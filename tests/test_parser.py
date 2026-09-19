import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from parser import parse_block, parse_line


def test_r_line_is_never_converted_field_positions():
    line = parse_line("R, Positive, Slow Grind Upward, 426.82, Compressed")
    assert line.is_valid
    assert line.price_indices == ()


def test_b_line_price_position():
    line = parse_line("B, 29817.5")
    assert line.is_valid
    assert line.price_indices == (0,)
    assert line.fields[0] == "29817.5"


def test_e_line_two_price_positions():
    line = parse_line("E, 29626, 29865.5")
    assert line.is_valid
    assert line.price_indices == (0, 1)


def test_u_line_only_first_two_fields_are_prices():
    line = parse_line(
        "U, 29865.5, 29822.82, , 35, 92, "
        "[in-cluster 12w \u00b7 vacuum beyond \u00b7 ridge 6.53x]"
    )
    assert line.is_valid
    assert line.price_indices == (0, 1)
    # Non-price fields preserved exactly
    assert line.fields[2] == ""
    assert line.fields[3] == "35"
    assert line.fields[4] == "92"
    assert "12w" in line.fields[5]
    assert "6.53x" in line.fields[5]


def test_d_line_only_first_two_fields_are_prices():
    line = parse_line(
        "D, 29777, 29819.68, , 15, 58, [in-cluster 18w \u00b7 vacuum beyond], "
        "[entry AT local support]"
    )
    assert line.is_valid
    assert line.price_indices == (0, 1)
    assert line.fields[3] == "15"
    assert line.fields[4] == "58"


def test_lc_metadata_preserved():
    line = parse_line(
        "LC, 30032, Local Resistance \u2014 Call Wall \u00b7 holds 53% "
        "\u2014 sellers' last gate"
    )
    assert line.is_valid
    assert line.price_indices == (0,)
    assert "holds 53%" in line.fields[1]
    assert "sellers' last gate" in line.fields[1]


def test_gc_metadata_preserved():
    line = parse_line(
        "GC, 30005, Gamma Cluster \u2014 12-wall band by total gamma \u00b7 holds 53%"
    )
    assert line.is_valid
    assert "holds 53%" in line.fields[1]


def test_lf_metadata_preserved():
    line = parse_line(
        "LF, 29777, Local Support \u2014 Put Wall \u00b7 VP-conf \u00b7 holds 58% "
        "\u2014 buyers' last gate"
    )
    assert line.is_valid
    assert "VP-conf" in line.fields[1]
    assert "holds 58%" in line.fields[1]


def test_gf_metadata_preserved():
    line = parse_line(
        "GF, 29706.75, Gamma Floor \u2014 18-wall band by total gamma \u00b7 holds 51%"
    )
    assert line.is_valid
    assert "holds 51%" in line.fields[1]


def test_fs_two_price_positions():
    line = parse_line("FS, 29852, 29908.18, , 83, 92, Long-Gate Rejection Fade")
    assert line.is_valid
    assert line.price_indices == (0, 1)


def test_fl_two_price_positions():
    line = parse_line("FL, 29802, 29734.32, , 83, 73, Short-Gate Reclaim Fade")
    assert line.is_valid
    assert line.price_indices == (0, 1)


def test_unknown_label_is_flagged_and_not_modified():
    line = parse_line("XX, 12345")
    assert not line.is_valid
    assert line.error is not None


def test_malformed_line_missing_price_field():
    line = parse_line("B,")
    assert not line.is_valid


def test_invalid_numeric_price():
    line = parse_line("B, not-a-number")
    assert not line.is_valid


def test_blank_line_is_blank():
    line = parse_line("")
    assert line.is_blank


def test_parse_block_skips_truly_empty_lines():
    text = "B, 29817.5\n\nZ, 29606"
    lines = parse_block(text)
    assert len(lines) == 2
