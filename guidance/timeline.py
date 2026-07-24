# -*- coding: utf-8 -*-
"""
Positioning guidance content on a child's or pregnancy's timeline.

The content library is sparse on purpose: daily entries cover the newborn
weeks and monthly entries take over afterwards. This module maps a date to the
periods that content actually exists for, so a gap in the library never leaves
a page empty.
"""

from dataclasses import dataclass, field

from dateutil.relativedelta import relativedelta

from django.utils import timezone

from guidance.models import GuidanceEntry, Kind, Scale


def age_in_days(birth_date, today=None):
    """
    Days since birth. The day of birth is day 0. Negative before birth.
    """
    today = today or timezone.localdate()
    return (today - birth_date).days


def month_of_life(birth_date, today=None):
    """
    Which month of life a date falls in, counting from 1.

    Month 1 covers birth up to (but not including) the first month birthday,
    month 2 the second month, and so on.
    """
    today = today or timezone.localdate()
    if today < birth_date:
        return 0
    delta = relativedelta(today, birth_date)
    return delta.years * 12 + delta.months + 1


def available_periods(scale):
    """
    Periods that active content exists for, in ascending order.
    """
    return sorted(
        GuidanceEntry.objects.filter(scale=scale, is_active=True)
        .values_list("period", flat=True)
        .distinct()
    )


def resolve_period(scale, target, periods=None):
    """
    Find the period whose content applies to ``target``.

    Counting up (day, month) the applicable period is the latest one already
    reached. Counting down to a due date (prenatal) it is the next checkpoint
    that has been reached, which is the smallest period at or above the number
    of days remaining.

    :return: an int period, or None when no content applies yet.
    """
    if periods is None:
        periods = available_periods(scale)
    if not periods:
        return None

    if scale == Scale.PRENATAL:
        reached = [period for period in periods if period >= target]
        return min(reached) if reached else None

    reached = [period for period in periods if period <= target]
    return max(reached) if reached else None


@dataclass
class GuidanceGroup:
    """
    The entries for one period, split by kind and annotated with progress.
    """

    scale: str
    period: int
    label: str = ""
    actions: list = field(default_factory=list)
    watch_for: list = field(default_factory=list)
    recaps: list = field(default_factory=list)
    completed_entry_ids: set = field(default_factory=set)

    @property
    def entries(self):
        return self.actions + self.watch_for + self.recaps

    @property
    def is_empty(self):
        return not self.entries

    @property
    def action_total(self):
        return len(self.actions)

    @property
    def action_completed(self):
        return len(
            [action for action in self.actions if action.id in self.completed_entry_ids]
        )

    @property
    def is_complete(self):
        return self.action_total > 0 and self.action_completed == self.action_total


def _group(scale, period, entries, completed_entry_ids, label=""):
    group = GuidanceGroup(
        scale=scale,
        period=period,
        label=label,
        completed_entry_ids=completed_entry_ids,
    )
    for entry in entries:
        if entry.kind == Kind.ACTION:
            group.actions.append(entry)
        elif entry.kind == Kind.WATCH:
            group.watch_for.append(entry)
        else:
            group.recaps.append(entry)
    return group


def _completed_ids(child=None, pregnancy=None):
    from guidance.models import GuidanceCompletion

    queryset = GuidanceCompletion.objects.all()
    if child is not None:
        queryset = queryset.filter(child=child)
    else:
        queryset = queryset.filter(pregnancy=pregnancy)
    return set(queryset.values_list("entry_id", flat=True))


def entries_for_period(scale, period):
    if period is None:
        return []
    return list(
        GuidanceEntry.objects.filter(scale=scale, period=period, is_active=True)
    )


def group_for_period(scale, period, child=None, pregnancy=None, label=""):
    """
    Build a single group of guidance for an explicit period.
    """
    return _group(
        scale,
        period,
        entries_for_period(scale, period),
        _completed_ids(child=child, pregnancy=pregnancy),
        label=label,
    )


def child_guidance(child, today=None):
    """
    Current guidance for a child: the applicable day group and month group.

    :return: dict with ``age_days``, ``month``, ``day_group`` and
        ``month_group``. Groups may be None when no content applies.
    """
    today = today or timezone.localdate()
    days = age_in_days(child.birth_date, today)
    month = month_of_life(child.birth_date, today)
    completed = _completed_ids(child=child)

    day_period = resolve_period(Scale.DAY, days) if days >= 0 else None
    month_period = resolve_period(Scale.MONTH, month) if month >= 1 else None

    return {
        "child": child,
        "age_days": days,
        "month": month,
        "day_group": (
            _group(
                Scale.DAY,
                day_period,
                entries_for_period(Scale.DAY, day_period),
                completed,
            )
            if day_period is not None
            else None
        ),
        "month_group": (
            _group(
                Scale.MONTH,
                month_period,
                entries_for_period(Scale.MONTH, month_period),
                completed,
            )
            if month_period is not None
            else None
        ),
    }


def pregnancy_guidance(pregnancy, today=None):
    """
    Current prenatal guidance for a pregnancy.

    :return: dict with ``days_until_due`` and ``group`` (may be None when the
        due date is still further out than the earliest content).
    """
    today = today or timezone.localdate()
    days_remaining = pregnancy.days_until_due(today)
    period = resolve_period(Scale.PRENATAL, days_remaining)
    completed = _completed_ids(pregnancy=pregnancy)

    return {
        "pregnancy": pregnancy,
        "days_until_due": days_remaining,
        "group": (
            _group(
                Scale.PRENATAL,
                period,
                entries_for_period(Scale.PRENATAL, period),
                completed,
            )
            if period is not None
            else None
        ),
    }
