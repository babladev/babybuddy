# -*- coding: utf-8 -*-
from django import template

from babybuddy import units

register = template.Library()


@register.filter
def as_weight(value):
    """
    Format a stored weight in the configured unit system, e.g. "3.6 kg".
    """
    return units.format_value(units.WEIGHT, value)


@register.filter
def as_length(value):
    """
    Format a stored length (height, head circumference) e.g. "50 cm".
    """
    return units.format_value(units.LENGTH, value)


@register.filter
def as_volume(value):
    """
    Format a stored volume (feeding or pumping amount) e.g. "60 ml".
    """
    return units.format_value(units.VOLUME, value)


@register.filter
def as_temperature(value):
    """
    Format a stored temperature, e.g. "37 °C".
    """
    return units.format_value(units.TEMPERATURE, value)


@register.simple_tag
def unit_label(kind):
    """
    The unit abbreviation for a measurement kind, for use in table headers.

    :param kind: one of "weight", "length", "volume" or "temperature".
    """
    return units.abbreviation(kind)
