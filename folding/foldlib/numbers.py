"""The folding maths and the number formatting shown in the counters.

    layers(n)    = 2^n
    thickness(n) = sheet thickness x 2^n
"""

import math


def layers(n):
    return 2 ** n


def thickness_m(thickness_mm, n):
    """Stack thickness in metres after n folds."""
    return thickness_mm / 1000.0 * (2 ** n)


def format_int(value):
    """4398046511104 -> '4,398,046,511,104'."""
    return f"{int(value):,}"


def format_sig(value, sig=3):
    """Three significant figures, trailing zeros stripped.

    Values of 1000 and above are shown as full integers with commas, so the
    finale reads '439,805 km' rather than '440,000 km'.
    """
    if value >= 1000:
        return f"{round(value):,}"
    if value <= 0:
        return "0"
    decimals = max(sig - 1 - math.floor(math.log10(value)), 0)
    text = f"{round(value, decimals):.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


# Unit ladder: (unit, metres per unit, switch to the next unit at this value).
_UNITS = [
    ("mm", 0.001, 100.0),   # up to 99.9 mm
    ("cm", 0.01, 100.0),    # 10 cm .. 99.9 cm
    ("m", 1.0, 1000.0),     # 1 m .. 999 m
    ("km", 1000.0, None),   # 1 km and up
]


def format_length(metres):
    """Auto units mm -> cm -> m -> km, e.g. 0.0128 -> '12.8 mm', 1.6384 -> '1.64 m'."""
    for unit, scale, upper in _UNITS:
        text = format_sig(metres / scale)
        # Promote when the value (after rounding) reaches the next unit.
        if upper is not None and float(text.replace(",", "")) >= upper:
            continue
        return f"{text} {unit}"
    return f"{format_sig(metres / 1000.0)} km"  # not reached; km has no upper bound


def split_value_unit(text):
    """'12.8 mm' -> ('12.8', 'mm')."""
    value, _, unit = text.partition(" ")
    return value, unit
