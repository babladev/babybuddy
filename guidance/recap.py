# -*- coding: utf-8 -*-
"""
Monthly recaps built from data already logged in Baby Buddy.

The guidance library says what is typical for a given month; this module says
what actually happened, so the two can be read side by side.
"""

import datetime

from dateutil.relativedelta import relativedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from core import models


def month_range(birth_date, month):
    """
    The date range covered by a month of life.

    :param month: month of life, counting from 1.
    :return: (start date, end date) where end is exclusive.
    """
    start = birth_date + relativedelta(months=month - 1)
    end = birth_date + relativedelta(months=month)
    return start, end


def _as_datetime_range(start, end):
    """
    Convert a date range into an aware datetime range for time-based models.
    """
    current_timezone = timezone.get_current_timezone()
    start_dt = timezone.make_aware(
        datetime.datetime.combine(start, datetime.time.min), current_timezone
    )
    end_dt = timezone.make_aware(
        datetime.datetime.combine(end, datetime.time.min), current_timezone
    )
    return start_dt, end_dt


def _duration_total(queryset, field="duration"):
    return queryset.aggregate(total=Sum(field))["total"] or datetime.timedelta()


def month_recap(child, month, today=None):
    """
    Summarise a child's logged data for one month of life.

    :return: dict of totals, plus ``days_elapsed`` and ``is_partial`` so a month
        still in progress can be labelled as such.
    """
    today = today or timezone.localdate()
    start, end = month_range(child.birth_date, month)
    effective_end = min(end, today + datetime.timedelta(days=1))
    days_elapsed = max((effective_end - start).days, 0)

    start_dt, end_dt = _as_datetime_range(start, effective_end)

    feedings = models.Feeding.objects.filter(
        child=child, start__gte=start_dt, start__lt=end_dt
    )
    changes = models.DiaperChange.objects.filter(
        child=child, time__gte=start_dt, time__lt=end_dt
    )
    sleeps = models.Sleep.objects.filter(
        child=child, start__gte=start_dt, start__lt=end_dt
    )
    tummy_times = models.TummyTime.objects.filter(
        child=child, start__gte=start_dt, start__lt=end_dt
    )
    weights = models.Weight.objects.filter(
        child=child, date__gte=start, date__lt=effective_end
    ).order_by("date")

    change_counts = changes.aggregate(
        wet=Count("id", filter=Q(wet=True)),
        solid=Count("id", filter=Q(solid=True)),
    )

    sleep_total = _duration_total(sleeps)
    first_weight = weights.first()
    last_weight = weights.last()

    return {
        "child": child,
        "month": month,
        "start": start,
        "end": end,
        "days_elapsed": days_elapsed,
        "is_partial": today < end - datetime.timedelta(days=1),
        "has_data": bool(
            feedings.exists()
            or changes.exists()
            or sleeps.exists()
            or tummy_times.exists()
            or weights.exists()
        ),
        "feeding_count": feedings.count(),
        "feeding_amount": feedings.aggregate(total=Sum("amount"))["total"],
        "change_count": changes.count(),
        "change_wet_count": change_counts["wet"],
        "change_solid_count": change_counts["solid"],
        "sleep_total": sleep_total,
        "sleep_daily_average": (
            sleep_total / days_elapsed if days_elapsed else datetime.timedelta()
        ),
        "tummy_time_total": _duration_total(tummy_times),
        "note_count": models.Note.objects.filter(
            child=child, time__gte=start_dt, time__lt=end_dt
        ).count(),
        "weight_start": first_weight,
        "weight_end": last_weight,
        "weight_change": (
            round(last_weight.weight - first_weight.weight, 3)
            if first_weight and last_weight and first_weight.id != last_weight.id
            else None
        ),
    }
