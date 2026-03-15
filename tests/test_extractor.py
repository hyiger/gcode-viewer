"""Tests for gcode_viewer.extractor — G-code parsing and extraction."""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import gcode_lib as gl
import pytest

from gcode_viewer.extractor import (
    _FILAMENT_AREA,
    _get_s_or_r_param,
    _get_s_param,
    _is_positive_extrusion,
    _parse_type_comment,
    extract_toolpath,
)
from gcode_viewer.types import ExtrusionType


# ---------------------------------------------------------------------------
# _parse_type_comment
# ---------------------------------------------------------------------------

_TYPE_CASES = [
    ("; TYPE:External perimeter", ExtrusionType.EXTERNAL_PERIMETER),
    ("; TYPE:Perimeter", ExtrusionType.PERIMETER),
    ("; TYPE:Overhang perimeter", ExtrusionType.EXTERNAL_PERIMETER),
    ("; TYPE:Infill", ExtrusionType.INFILL),
    ("; TYPE:Solid infill", ExtrusionType.SOLID_INFILL),
    ("; TYPE:Top solid infill", ExtrusionType.TOP_SOLID_INFILL),
    ("; TYPE:Bridge infill", ExtrusionType.BRIDGE_INFILL),
    ("; TYPE:Support material", ExtrusionType.SUPPORT_MATERIAL),
    ("; TYPE:Support material interface", ExtrusionType.SUPPORT_MATERIAL),
    ("; TYPE:Skirt/Brim", ExtrusionType.SKIRT_BRIM),
    ("; TYPE:Skirt", ExtrusionType.SKIRT_BRIM),
    ("; TYPE:Custom", ExtrusionType.CUSTOM),
    ("; TYPE:Gap fill", ExtrusionType.GAP_FILL),
    ("; TYPE:Ironing", ExtrusionType.IRONING),
    ("; TYPE:Wipe tower", ExtrusionType.WIPE),
]


@pytest.mark.parametrize("comment, expected", _TYPE_CASES)
def test_parse_type_comment_valid(comment, expected):
    assert _parse_type_comment(comment) is expected


def test_parse_type_comment_unknown():
    assert _parse_type_comment("; TYPE:SomethingNew") is ExtrusionType.UNKNOWN


def test_parse_type_comment_not_a_type():
    assert _parse_type_comment("; some random comment") is None


def test_parse_type_comment_empty():
    assert _parse_type_comment("") is None


def test_parse_type_comment_whitespace():
    assert _parse_type_comment("  ; TYPE:Infill  ") is ExtrusionType.INFILL


# ---------------------------------------------------------------------------
# _get_s_param
# ---------------------------------------------------------------------------

def test_get_s_param_present():
    line = gl.parse_line("M106 S128")
    assert _get_s_param(line) == pytest.approx(128.0)


def test_get_s_param_lowercase():
    line = gl.parse_line("M106 s200")
    assert _get_s_param(line) == pytest.approx(200.0)


def test_get_s_param_absent():
    line = gl.parse_line("M106")
    assert _get_s_param(line) is None


def test_get_s_param_float():
    line = gl.parse_line("M106 S127.5")
    assert _get_s_param(line) == pytest.approx(127.5)


# ---------------------------------------------------------------------------
# _get_s_or_r_param
# ---------------------------------------------------------------------------

def test_get_s_or_r_param_s_present():
    line = gl.parse_line("M104 S210")
    assert _get_s_or_r_param(line) == pytest.approx(210.0)


def test_get_s_or_r_param_r_fallback():
    line = gl.parse_line("M109 R200")
    assert _get_s_or_r_param(line) == pytest.approx(200.0)


def test_get_s_or_r_param_neither():
    line = gl.parse_line("M109")
    assert _get_s_or_r_param(line) is None


def test_get_s_or_r_param_both():
    line = gl.parse_line("M109 S210 R200")
    # S takes priority
    assert _get_s_or_r_param(line) == pytest.approx(210.0)


# ---------------------------------------------------------------------------
# _is_positive_extrusion
# ---------------------------------------------------------------------------

def test_is_positive_extrusion_no_e():
    line = gl.parse_line("G1 X10 Y20")
    state = gl.ModalState()
    assert _is_positive_extrusion(line, state) is False


def test_is_positive_extrusion_abs_positive():
    line = gl.parse_line("G1 X10 E5.0")
    state = gl.ModalState()
    state.e = 3.0
    state.abs_e = True
    assert _is_positive_extrusion(line, state) is True


def test_is_positive_extrusion_abs_negative():
    line = gl.parse_line("G1 X10 E2.0")
    state = gl.ModalState()
    state.e = 3.0
    state.abs_e = True
    assert _is_positive_extrusion(line, state) is False


def test_is_positive_extrusion_rel_positive():
    line = gl.parse_line("G1 X10 E0.5")
    state = gl.ModalState()
    state.abs_e = False
    assert _is_positive_extrusion(line, state) is True


def test_is_positive_extrusion_rel_negative():
    line = gl.parse_line("G1 X10 E-1.0")
    state = gl.ModalState()
    state.abs_e = False
    assert _is_positive_extrusion(line, state) is False


def test_is_positive_extrusion_rel_zero():
    line = gl.parse_line("G1 X10 E0.0")
    state = gl.ModalState()
    state.abs_e = False
    assert _is_positive_extrusion(line, state) is False


# ---------------------------------------------------------------------------
# extract_toolpath (mocked gcode-lib)
# ---------------------------------------------------------------------------

def _mock_gcode_file(lines):
    gf = MagicMock()
    gf.lines = lines
    return gf


def _make_lines(*raw_strs):
    return [gl.parse_line(s) for s in raw_strs]


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_basic(mock_gl):
    lines = _make_lines(
        "; TYPE:Perimeter",
        "G1 X10 Y20 E0.5 F1800",
        "G1 X20 Y20 E0.5 F1800",
    )
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}

    bounds = MagicMock()
    bounds.valid = True
    bounds.x_min, bounds.x_max = 0.0, 100.0
    bounds.y_min, bounds.y_max = 0.0, 100.0
    bounds.z_min, bounds.z_max = 0.0, 10.0
    stats = MagicMock()
    stats.bounds = bounds
    mock_gl.compute_stats.return_value = stats
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()

    def advance(state, line):
        gl.advance_state(state, line)
    mock_gl.advance_state.side_effect = advance

    tp = extract_toolpath("test.gcode")
    assert tp.bed_x == 250
    assert tp.bed_y == 220
    assert tp.total_layers == 1
    assert tp.total_segments == 2


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_no_volume(mock_gl):
    lines = _make_lines("G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = None

    bounds = MagicMock()
    bounds.valid = True
    bounds.x_min, bounds.x_max = 0.0, 50.0
    bounds.y_min, bounds.y_max = 0.0, 50.0
    bounds.z_min, bounds.z_max = 0.0, 5.0
    stats = MagicMock()
    stats.bounds = bounds
    mock_gl.compute_stats.return_value = stats
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    assert tp.bed_x == 250.0  # _DEFAULT_BED_X
    assert tp.bed_y == 210.0  # _DEFAULT_BED_Y


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_invalid_bounds(mock_gl):
    lines = _make_lines("G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}

    bounds = MagicMock()
    bounds.valid = False
    stats = MagicMock()
    stats.bounds = bounds
    mock_gl.compute_stats.return_value = stats
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    assert tp.x_min == 0.0
    assert tp.x_max == 250  # bed_x
    assert tp.y_max == 220  # bed_y


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_m106_with_s(mock_gl):
    lines = _make_lines("M106 S128", "G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    seg = tp.layers[0].segments[0]
    assert seg.fan_speed == pytest.approx(128.0)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_m106_without_s(mock_gl):
    lines = _make_lines("M106", "G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    seg = tp.layers[0].segments[0]
    assert seg.fan_speed == pytest.approx(255.0)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_m107(mock_gl):
    lines = _make_lines("M106 S128", "M107", "G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    seg = tp.layers[0].segments[0]
    assert seg.fan_speed == pytest.approx(0.0)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_m104_temperature(mock_gl):
    lines = _make_lines("M104 S215", "G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    assert tp.layers[0].segments[0].temperature == pytest.approx(215.0)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_m109_r(mock_gl):
    lines = _make_lines("M109 R200", "G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    assert tp.layers[0].segments[0].temperature == pytest.approx(200.0)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_type_comment(mock_gl):
    lines = _make_lines("; TYPE:Infill", "G1 X10 Y10 E1 F1000")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    assert tp.layers[0].segments[0].extrusion_type is ExtrusionType.INFILL


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_travel_vs_extrusion(mock_gl):
    lines = _make_lines(
        "G1 X10 Y10 E1 F1000",   # extrusion
        "G0 X20 Y20 F9000",       # travel
    )
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    segs = tp.layers[0].segments
    assert segs[0].is_travel is False
    assert segs[1].is_travel is True


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_volumetric_flow(mock_gl):
    # G1 X10 Y0 E1.0 F600 → distance=10mm, e_delta=1.0, f=600mm/min
    lines = _make_lines("G1 X10 Y0 E1.0 F600")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    seg = tp.layers[0].segments[0]
    # vol_flow = e_delta * FILAMENT_AREA * f / (dist * 60)
    expected = 1.0 * _FILAMENT_AREA * 600.0 / (10.0 * 60.0)
    assert seg.volumetric_flow == pytest.approx(expected, rel=1e-3)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_empty_layers(mock_gl):
    # No move lines
    lines = _make_lines("; just a comment", "M104 S200")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    assert tp.total_segments == 0


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_relative_xy(mock_gl):
    """Cover the relative XY branch (G91)."""
    lines = _make_lines("G91", "G1 X10 Y20 E0.5 F1800")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    seg = tp.layers[0].segments[0]
    # Starting from (0,0,0), relative move X10 Y20 → endpoint (10, 20, 0)
    assert seg.x1 == pytest.approx(10.0)
    assert seg.y1 == pytest.approx(20.0)


@patch("gcode_viewer.extractor.gl")
def test_extract_toolpath_relative_e_volumetric_flow(mock_gl):
    """Cover the relative E branch for volumetric flow (M83)."""
    lines = _make_lines("M83", "G1 X10 Y0 E1.0 F600")
    mock_gl.load.return_value = _mock_gcode_file(lines)
    mock_gl.linearize_arcs.return_value = lines
    mock_gl.detect_print_volume.return_value = {"bed_x": 250, "bed_y": 220, "max_z": 200}
    bounds = MagicMock(valid=True, x_min=0, x_max=100, y_min=0, y_max=100, z_min=0, z_max=10)
    mock_gl.compute_stats.return_value = MagicMock(bounds=bounds)
    mock_gl.iter_layers.return_value = [(0.2, lines)]
    mock_gl.ModalState.return_value = gl.ModalState()
    mock_gl.advance_state.side_effect = lambda s, l: gl.advance_state(s, l)

    tp = extract_toolpath("test.gcode")
    seg = tp.layers[0].segments[0]
    # Relative E: e_delta = line.words["E"] = 1.0
    expected = 1.0 * _FILAMENT_AREA * 600.0 / (10.0 * 60.0)
    assert seg.volumetric_flow == pytest.approx(expected, rel=1e-3)
