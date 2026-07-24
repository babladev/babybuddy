# -*- coding: utf-8 -*-
from django import template
from django.utils import timezone

from guidance import timeline

register = template.Library()


@register.inclusion_tag("cards/guidance.html", takes_context=True)
def card_guidance(context, child):
    """
    Today's guidance for a child, for the child dashboard.

    :param child: an instance of the Child model.
    :returns: the applicable day and month guidance groups.
    """
    today = timezone.localdate()
    guidance = timeline.child_guidance(child, today)

    group = guidance["day_group"] or guidance["month_group"]
    empty = group is None or group.is_empty

    return {
        "type": "guidance",
        "child": child,
        "group": group,
        "age_days": guidance["age_days"],
        "month": guidance["month"],
        "empty": empty,
        "hide_empty": context["request"].user.settings.dashboard_hide_empty,
        "perms": context.get("perms"),
        "request": context["request"],
    }
