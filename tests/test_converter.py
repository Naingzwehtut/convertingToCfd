import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from converter import calculate_basis, convert_block, convert_level
from parser import parse_block

SAMPLE_INPUT = """\
R, Positive, Slow Grind Upward, 426.82, Compressed
B, 29817.5
Z, 29606
M, 29602
H, 29572.5
E, 29626, 29865.5
I, 29798, 29844.75
LC, 30032, Local Resistance \u2014 Call Wall \u00b7 holds 53% \u2014 sellers' last gate
GC, 30005, Gamma Cluster \u2014 12-wall band by total gamma \u00b7 holds 53%
LF, 29777, Local Support \u2014 Put Wall \u00b7 VP-conf \u00b7 holds 58% \u2014 buyers' last gate
GF, 29706.75, Gamma Floor \u2014 18-wall band by total gamma \u00b7 holds 51%
U, 29865.5, 29822.82, , 35, 92, [in-cluster 12w \u00b7 vacuum beyond \u00b7 ridge 6.53x]
D, 29777, 29819.68, , 15, 58, [in-cluster 18w \u00b7 vacuum beyond], [entry AT local support]
FS, 29852, 29908.18, , 83, 92, Long-Gate Rejection Fade
FL, 29802, 29734.32, , 83, 73, Short-Gate Reclaim Fade
"""

NQ_PRICE = 29836.00
US100_PRICE = 29530.20


def test_basis_calculation():
    assert round(calculate_basis(29836, 29530.20), 2) == 305.8


def test_convert_level():
    assert round(convert_level(30032, 305.80), 2) == 29726.20


def _convert_sample():
    gamma_lines = parse_block(SAMPLE_INPUT)
    result = convert_block(gamma_lines, NQ_PRICE, US100_PRICE)
    return dict(
        zip(
            [line.split(",")[0].strip() if line.split(",")[0].strip() != "R" else "R"
             for line in result.converted_lines],
            result.converted_lines,
        )
    ), result


def test_b_conversion():
    outputs, _ = _convert_sample()
    assert outputs["B"] == "B, 29511.7"


def test_r_preservation_exact():
    outputs, _ = _convert_sample()
    assert outputs["R"] == "R, Positive, Slow Grind Upward, 426.82, Compressed"


def test_e_conversion():
    outputs, _ = _convert_sample()
    assert outputs["E"] == "E, 29320.2, 29559.7"


def test_u_conversion_only_first_two_fields_change():
    outputs, _ = _convert_sample()
    line = outputs["U"]
    assert line.startswith("U, 29559.7, 29517.02, , 35, 92,")
    assert "12w" in line
    assert "6.53x" in line


def test_d_conversion_only_first_two_fields_change():
    outputs, _ = _convert_sample()
    line = outputs["D"]
    assert line.startswith("D, 29471.2, 29513.88, , 15, 58,")
    assert "entry AT local support" in line


def test_lc_metadata_preservation():
    outputs, _ = _convert_sample()
    line = outputs["LC"]
    assert line.startswith("LC, 29726.2,")
    assert "holds 53%" in line
    assert "sellers' last gate" in line


def test_gc_metadata_preservation():
    outputs, _ = _convert_sample()
    line = outputs["GC"]
    assert line.startswith("GC, 29699.2,")
    assert "holds 53%" in line


def test_lf_metadata_preservation():
    outputs, _ = _convert_sample()
    line = outputs["LF"]
    assert line.startswith("LF, 29471.2,")
    assert "VP-conf" in line
    assert "holds 58%" in line


def test_gf_metadata_preservation():
    outputs, _ = _convert_sample()
    line = outputs["GF"]
    assert line.startswith("GF, 29400.95,")
    assert "holds 51%" in line


def test_fs_conversion():
    outputs, _ = _convert_sample()
    line = outputs["FS"]
    assert line.startswith("FS, 29546.2, 29602.38,")
    assert "Long-Gate Rejection Fade" in line


def test_fl_conversion():
    outputs, _ = _convert_sample()
    line = outputs["FL"]
    assert line.startswith("FL, 29496.2, 29428.52,")
    assert "Short-Gate Reclaim Fade" in line


def test_unknown_line_not_modified():
    gamma_lines = parse_block("XX, 12345, some text")
    result = convert_block(gamma_lines, NQ_PRICE, US100_PRICE)
    assert result.converted_lines[0] == "XX, 12345, some text"
    assert len(result.warnings) == 1


def test_decimal_formatting_no_trailing_zeros():
    outputs, _ = _convert_sample()
    assert "29296.2" in outputs["M"]
    assert "29266.7" in outputs["H"]


def test_negative_or_zero_basis_still_computes():
    gamma_lines = parse_block("B, 100")
    # us100 higher than nq -> negative basis
    result = convert_block(gamma_lines, 100.0, 150.0)
    assert result.basis == -50.0
    assert result.converted_lines[0] == "B, 150"


def test_zero_basis_computes_identity():
    gamma_lines = parse_block("B, 100")
    result = convert_block(gamma_lines, 100.0, 100.0)
    assert result.basis == 0.0
    assert result.converted_lines[0] == "B, 100"
