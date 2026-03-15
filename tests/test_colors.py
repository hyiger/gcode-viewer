"""Tests for gcode_viewer.colors — palettes, gradients, legends."""

from __future__ import annotations

import numpy as np
import pytest

from gcode_viewer.colors import (
    COLOR_MODE_LABELS,
    EXTRUSION_COLORS,
    EXTRUSION_LABELS,
    _gradient_color,
    _lerp_color,
    build_gradient_legend_labels,
    color_for_feature,
    compute_segment_colors,
)
from gcode_viewer.types import ColorMode, ExtrusionType, Segment

# Re-use private constants for testing
from gcode_viewer.colors import _HEIGHT_STOPS, _SPEED_STOPS


# ---------------------------------------------------------------------------
# _lerp_color
# ---------------------------------------------------------------------------

def test_lerp_color_at_zero():
    rgb = _lerp_color(0.0, _HEIGHT_STOPS)
    assert rgb == _HEIGHT_STOPS[0][1]


def test_lerp_color_at_one():
    rgb = _lerp_color(1.0, _HEIGHT_STOPS)
    expected = _HEIGHT_STOPS[-1][1]
    for i in range(3):
        assert abs(rgb[i] - expected[i]) < 1e-9


def test_lerp_color_clamp_below():
    rgb = _lerp_color(-1.0, _HEIGHT_STOPS)
    for i in range(3):
        assert abs(rgb[i] - _HEIGHT_STOPS[0][1][i]) < 1e-9


def test_lerp_color_clamp_above():
    rgb = _lerp_color(2.0, _HEIGHT_STOPS)
    expected = _HEIGHT_STOPS[-1][1]
    for i in range(3):
        assert abs(rgb[i] - expected[i]) < 1e-9


def test_lerp_color_exact_stop():
    # t=0.25 is exactly the second stop of _HEIGHT_STOPS
    rgb = _lerp_color(0.25, _HEIGHT_STOPS)
    assert rgb == _HEIGHT_STOPS[1][1]


def test_lerp_color_interpolation():
    # Between first two stops (0.0 and 0.25) at t=0.125
    rgb = _lerp_color(0.125, _HEIGHT_STOPS)
    c0 = _HEIGHT_STOPS[0][1]
    c1 = _HEIGHT_STOPS[1][1]
    for i in range(3):
        expected = c0[i] + 0.5 * (c1[i] - c0[i])
        assert abs(rgb[i] - expected) < 1e-9


def test_lerp_color_equal_stops():
    stops = [(0.5, (1.0, 0.0, 0.0)), (0.5, (0.0, 1.0, 0.0))]
    # t=0.5 should hit the first stop; f = 0 (division guard)
    rgb = _lerp_color(0.5, stops)
    assert rgb == (1.0, 0.0, 0.0)


# ---------------------------------------------------------------------------
# color_for_feature
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("etype", list(ExtrusionType))
def test_color_for_feature_all_types(etype, segment_factory):
    seg = segment_factory(extrusion_type=etype)
    rgb = color_for_feature(seg)
    assert len(rgb) == 3
    assert all(0.0 <= c <= 1.0 for c in rgb)


# ---------------------------------------------------------------------------
# _gradient_color
# ---------------------------------------------------------------------------

def test_gradient_color_zero_range():
    rgb = _gradient_color(5.0, 5.0, 0.0, _HEIGHT_STOPS)
    # val_range=0 → t=0.5
    expected = _lerp_color(0.5, _HEIGHT_STOPS)
    assert rgb == expected


def test_gradient_color_normal():
    rgb = _gradient_color(10.0, 0.0, 20.0, _SPEED_STOPS)
    expected = _lerp_color(0.5, _SPEED_STOPS)
    assert rgb == expected


# ---------------------------------------------------------------------------
# compute_segment_colors
# ---------------------------------------------------------------------------

def _segs_for_modes():
    """A few segments with varied attributes for testing color modes."""
    def seg(z=0.2, f=3000, fan=128, temp=210, flow=5.0):
        return Segment(
            x0=100, y0=100, z0=z, x1=110, y1=100, z1=z,
            extrusion_type=ExtrusionType.PERIMETER,
            layer_index=0, is_travel=False,
            feedrate=f, fan_speed=fan, temperature=temp, volumetric_flow=flow,
        )
    return [seg(), seg(z=0.4, f=6000, fan=255, temp=250, flow=12.0)]


_RANGES = {"z": (0.2, 0.6), "f": (1200, 6000), "fan": (0, 255), "temp": (200, 250), "flow": (2, 12)}


@pytest.mark.parametrize("mode", list(ColorMode))
def test_compute_segment_colors_all_modes(mode):
    segs = _segs_for_modes()
    colors = compute_segment_colors(segs, mode, _RANGES)
    assert colors.shape == (2, 3)
    assert colors.dtype == np.uint8


def test_compute_segment_colors_empty():
    colors = compute_segment_colors([], ColorMode.FEATURE_TYPE, _RANGES)
    assert colors.shape == (0, 3)


def test_compute_segment_colors_feature_matches():
    segs = _segs_for_modes()
    colors = compute_segment_colors(segs, ColorMode.FEATURE_TYPE, _RANGES)
    expected_rgb = EXTRUSION_COLORS[ExtrusionType.PERIMETER]
    expected = [int(c * 255) for c in expected_rgb]
    np.testing.assert_array_equal(colors[0], expected)


# ---------------------------------------------------------------------------
# build_gradient_legend_labels
# ---------------------------------------------------------------------------

def test_legend_labels_constant_value():
    labels = build_gradient_legend_labels(ColorMode.HEIGHT, 5.0, 5.0)
    assert len(labels) == 1
    assert "5.0" in labels[0][0]


def test_legend_labels_distinct_values_few():
    labels = build_gradient_legend_labels(
        ColorMode.FAN_SPEED, 0.0, 100.0,
        distinct_values=[0.0, 50.0, 100.0],
    )
    assert len(labels) == 3
    assert "0.0" in labels[0][0]
    assert "100.0" in labels[2][0]


def test_legend_labels_distinct_values_too_many():
    many = [float(i) for i in range(20)]
    labels = build_gradient_legend_labels(
        ColorMode.HEIGHT, 0.0, 19.0,
        distinct_values=many,
    )
    # Falls through to interpolation (8 steps)
    assert len(labels) <= 8


def test_legend_labels_interpolation():
    labels = build_gradient_legend_labels(ColorMode.SPEED, 0.0, 100.0)
    assert 2 <= len(labels) <= 8


def test_legend_labels_dedup():
    # Narrow range: 0.0–0.5 with 8 steps → many duplicate display strings
    labels = build_gradient_legend_labels(ColorMode.HEIGHT, 0.0, 0.5)
    texts = [l[0] for l in labels]
    assert len(texts) == len(set(texts))  # no duplicates


@pytest.mark.parametrize("mode,unit", [
    (ColorMode.HEIGHT, "mm"),
    (ColorMode.SPEED, "mm/s"),
    (ColorMode.FAN_SPEED, "%"),
    (ColorMode.TEMPERATURE, "\u00b0C"),
    (ColorMode.VOLUMETRIC_FLOW, "mm\u00b3/s"),
])
def test_legend_labels_units(mode, unit):
    labels = build_gradient_legend_labels(mode, 0.0, 100.0)
    assert all(unit in text for text, _ in labels)


# ---------------------------------------------------------------------------
# Dict completeness
# ---------------------------------------------------------------------------

def test_extrusion_colors_complete():
    for et in ExtrusionType:
        assert et in EXTRUSION_COLORS, f"{et} missing from EXTRUSION_COLORS"


def test_extrusion_labels_complete():
    for et in ExtrusionType:
        assert et in EXTRUSION_LABELS, f"{et} missing from EXTRUSION_LABELS"


def test_color_mode_labels_complete():
    for cm in ColorMode:
        assert cm in COLOR_MODE_LABELS, f"{cm} missing from COLOR_MODE_LABELS"
