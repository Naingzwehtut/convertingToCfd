"""
formatter.py

All display/decimal formatting lives here so parser.py and converter.py
stay focused on parsing and math.

Two distinct formatting needs:
  * "clean" formatting for converted price fields inside the Gamma
    Engine block (e.g. 29511.7, 29300.2, 29726) — minimal decimals,
    no thousands separators, no trailing zeros.
  * "display" formatting for the human-readable summary block
    (e.g. 29,836.00) — fixed 2 decimals, thousands separators.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

# Converted prices are rounded to this many decimal places before
# trailing-zero stripping. Two is enough for NQ/US100 tick sizes
# (0.25 / 0.01) while avoiding binary-float artifacts like
# 29300.199999999997.
CLEAN_DECIMAL_PLACES = 2


def format_price_clean(value: float) -> str:
    """
    Format a converted price for the output block: round to 2 decimal
    places, then strip unnecessary trailing zeros (and a trailing
    decimal point if nothing follows it).

    29511.70 -> "29511.7"
    29300.20 -> "29300.2"
    29726.00 -> "29726"
    """
    quantized = Decimal(str(value)).quantize(
        Decimal("1." + "0" * CLEAN_DECIMAL_PLACES), rounding=ROUND_HALF_UP
    )
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def format_price_display(value: float) -> str:
    """
    Format a price for the summary header: fixed 2 decimals with a
    thousands separator, e.g. 29836 -> "29,836.00".
    """
    quantized = Decimal(str(value)).quantize(
        Decimal("1.00"), rounding=ROUND_HALF_UP
    )
    return f"{quantized:,.2f}"


def format_basis_display(value: float) -> str:
    """Format the basis for the summary header, e.g. 305.80."""
    quantized = Decimal(str(value)).quantize(
        Decimal("1.00"), rounding=ROUND_HALF_UP
    )
    return f"{quantized:,.2f}"
