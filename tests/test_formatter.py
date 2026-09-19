import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from formatter import format_basis_display, format_price_clean, format_price_display


def test_clean_strips_trailing_zeros():
    assert format_price_clean(29511.70) == "29511.7"
    assert format_price_clean(29300.20) == "29300.2"


def test_clean_strips_full_decimal_when_whole_number():
    assert format_price_clean(29726.00) == "29726"


def test_clean_avoids_binary_float_artifacts():
    # 29606 - 305.80 in raw floating point can produce trailing noise digits;
    # formatting must clean that up to a sensible 1-decimal value.
    value = 29606 - 305.80
    assert format_price_clean(value) == "29300.2"


def test_clean_rounds_to_two_decimal_places():
    assert format_price_clean(29517.015) in ("29517.02", "29517.01")


def test_display_format_has_comma_and_two_decimals():
    assert format_price_display(29836) == "29,836.00"
    assert format_price_display(29530.20) == "29,530.20"


def test_basis_display_format():
    assert format_basis_display(305.80) == "305.80"
    assert format_basis_display(305.8) == "305.80"
