# -*- coding: utf-8 -*-
"""
Metric and US customary units for measurements.

Values are always stored in metric: kilograms, centimetres, millilitres and
degrees Celsius. Conversion happens at the edges - when a form is filled in and
when a value is displayed - so the database stays consistent regardless of which
unit system is in use, and the API keeps a single well defined unit per field.

The unit system is a site-wide setting rather than a per-user one, so that a
value entered by one parent reads the same to the other.
"""

from django.template.defaultfilters import floatformat
from django.utils.translation import gettext_lazy as _

METRIC = "metric"
US = "us"

UNIT_SYSTEM_CHOICES = [
    (METRIC, _("Metric (kg, cm, ml, °C)")),
    (US, _("US customary (lb, in, fl oz, °F)")),
]

# Measurement kinds.
WEIGHT = "weight"
LENGTH = "length"
VOLUME = "volume"
TEMPERATURE = "temperature"

# Abbreviation and metric-to-US factor for each kind. Temperature is affine
# rather than a simple ratio, so it is handled separately below.
_UNITS = {
    WEIGHT: {
        METRIC: {"abbreviation": _("kg"), "precision": 3},
        US: {"abbreviation": _("lb"), "precision": 2, "factor": 2.2046226218},
    },
    LENGTH: {
        METRIC: {"abbreviation": _("cm"), "precision": 1},
        US: {"abbreviation": _("in"), "precision": 2, "factor": 0.3937007874},
    },
    VOLUME: {
        METRIC: {"abbreviation": _("ml"), "precision": 1},
        US: {"abbreviation": _("fl oz"), "precision": 2, "factor": 0.0338140227},
    },
    TEMPERATURE: {
        METRIC: {"abbreviation": _("°C"), "precision": 1},
        US: {"abbreviation": _("°F"), "precision": 1},
    },
}


def unit_system():
    """
    The unit system currently configured for the site.

    :return: "metric" or "us".
    """
    # Imported here because core.models imports babybuddy.site_settings, which
    # would make this a circular import at module level.
    from core.models import Child

    value = Child.settings.unit_system
    return US if value == US else METRIC


def _config(kind, system=None):
    return _UNITS[kind][system or unit_system()]


def abbreviation(kind, system=None):
    """
    The unit abbreviation for a measurement kind, e.g. "kg" or "lb".
    """
    return _config(kind, system)["abbreviation"]


def precision(kind, system=None):
    """
    How many decimal places are meaningful for a measurement kind.
    """
    return _config(kind, system)["precision"]


def to_display(kind, value, system=None):
    """
    Convert a stored (metric) value into the configured display unit.

    :return: a float, or None when value is None.
    """
    if value is None:
        return None
    system = system or unit_system()
    if system == METRIC:
        return float(value)
    if kind == TEMPERATURE:
        return float(value) * 9 / 5 + 32
    return float(value) * _UNITS[kind][US]["factor"]


def to_storage(kind, value, system=None):
    """
    Convert a value entered in the display unit back to metric for storage.

    :return: a float, or None when value is None.
    """
    if value is None:
        return None
    system = system or unit_system()
    if system == METRIC:
        return float(value)
    if kind == TEMPERATURE:
        return (float(value) - 32) * 5 / 9
    return float(value) / _UNITS[kind][US]["factor"]


def format_value(kind, value, system=None, with_unit=True):
    """
    Convert and format a stored value for display.

    :return: a string such as "3.6 kg", or an empty string when value is None.
    """
    if value is None:
        return ""
    system = system or unit_system()
    converted = to_display(kind, value, system)
    number = floatformat(converted, -_significant_decimals(converted, kind, system))
    if not with_unit:
        return number
    return "{} {}".format(number, abbreviation(kind, system))


def _significant_decimals(value, kind, system):
    """
    The fewest decimal places that represent a value without losing detail,
    capped at the precision meaningful for the measurement kind.

    This keeps "60 ml" from rendering as "60.0 ml" while still allowing
    "3.625 kg". Formatting itself is left to floatformat so the decimal
    separator follows the active locale.
    """
    limit = precision(kind, system)
    rounded = round(value, limit)
    for decimals in range(limit + 1):
        if round(rounded, decimals) == rounded:
            return decimals
    return limit


def convert_list(kind, values, system=None):
    """
    Convert an iterable of stored values into the display unit.

    Used for chart series, where the values have to be numbers rather than
    formatted strings.
    """
    system = system or unit_system()
    return [to_display(kind, value, system) for value in values]


def axis_label(label, kind, system=None):
    """
    Add the unit abbreviation to a chart axis title, e.g. "Weight (kg)".
    """
    return "{} ({})".format(label, abbreviation(kind, system))
