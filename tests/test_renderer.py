"""Tests for gcode_viewer.renderer — scene building and recoloring."""

from __future__ import annotations

import numpy as np
import pyvista as pv
import pytest

from gcode_viewer.renderer import (
    LayerActors,
    _collect_distinct_values,
    _compute_ranges,
    _feature_type_legend,
    _segments_to_polydata,
    add_legend,
    build_scene,
    recolor_layers,
)
from gcode_viewer.types import (
    ColorMode,
    ExtrusionType,
    LayerData,
    Segment,
    ToolpathData,
)


# ---------------------------------------------------------------------------
# LayerActors
# ---------------------------------------------------------------------------

def test_layer_actors_init():
    la = LayerActors()
    assert la.extrusion_actor is None
    assert la.travel_actor is None
    assert la.extrusion_pd is None
    assert la.travel_pd is None
    assert la.extrusion_segs == []
    assert la.travel_segs == []


# ---------------------------------------------------------------------------
# _segments_to_polydata
# ---------------------------------------------------------------------------

def test_segments_to_polydata_type(sample_segments, sample_ranges):
    ext_segs = [s for s in sample_segments if not s.is_travel]
    pd = _segments_to_polydata(ext_segs, ColorMode.FEATURE_TYPE, sample_ranges)
    assert isinstance(pd, pv.PolyData)


def test_segments_to_polydata_points(sample_segments, sample_ranges):
    ext_segs = [s for s in sample_segments if not s.is_travel]
    n = len(ext_segs)
    pd = _segments_to_polydata(ext_segs, ColorMode.FEATURE_TYPE, sample_ranges)
    assert pd.n_points == n * 2


def test_segments_to_polydata_lines(sample_segments, sample_ranges):
    ext_segs = [s for s in sample_segments if not s.is_travel]
    n = len(ext_segs)
    pd = _segments_to_polydata(ext_segs, ColorMode.FEATURE_TYPE, sample_ranges)
    assert pd.n_lines == n


def test_segments_to_polydata_has_colors(sample_segments, sample_ranges):
    ext_segs = [s for s in sample_segments if not s.is_travel]
    pd = _segments_to_polydata(ext_segs, ColorMode.FEATURE_TYPE, sample_ranges)
    assert "colors" in pd.cell_data
    assert pd.cell_data["colors"].shape == (len(ext_segs), 3)
    assert pd.cell_data["colors"].dtype == np.uint8


def test_segments_to_polydata_coordinates(segment_factory, sample_ranges):
    seg = segment_factory(x0=5.0, y0=10.0, z0=0.3, x1=15.0, y1=20.0, z1=0.3)
    pd = _segments_to_polydata([seg], ColorMode.FEATURE_TYPE, sample_ranges)
    pts = pd.points
    np.testing.assert_allclose(pts[0], [5.0, 10.0, 0.3], atol=1e-5)
    np.testing.assert_allclose(pts[1], [15.0, 20.0, 0.3], atol=1e-5)


# ---------------------------------------------------------------------------
# _compute_ranges
# ---------------------------------------------------------------------------

def test_compute_ranges_normal(sample_toolpath):
    ranges = _compute_ranges(sample_toolpath)
    assert "z" in ranges and "f" in ranges and "fan" in ranges
    assert "temp" in ranges and "flow" in ranges
    f_min, f_max = ranges["f"]
    assert f_min < f_max


def test_compute_ranges_travel_only():
    """All-travel toolpath should produce degenerate default ranges."""
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.TRAVEL,
        layer_index=0, is_travel=True, feedrate=9000,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    ranges = _compute_ranges(tp)
    # Defaults when no non-travel segments
    assert ranges["f"] == (0.0, 1.0)
    assert ranges["fan"] == (0.0, 255.0)
    assert ranges["temp"] == (0.0, 300.0)
    assert ranges["flow"] == (0.0, 1.0)


def test_compute_ranges_zero_feedrate_skipped():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False, feedrate=0.0,
        fan_speed=100, temperature=210, volumetric_flow=5.0,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    ranges = _compute_ranges(tp)
    assert ranges["f"] == (0.0, 1.0)  # default because feedrate=0 skipped


def test_compute_ranges_zero_temp_skipped():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False, feedrate=1000,
        temperature=0.0, fan_speed=100, volumetric_flow=5.0,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    ranges = _compute_ranges(tp)
    assert ranges["temp"] == (0.0, 300.0)  # default


def test_compute_ranges_degenerate_empty():
    tp = ToolpathData(
        layers=[], bed_x=250, bed_y=220, max_z=50,
        total_layers=0, total_segments=0,
    )
    ranges = _compute_ranges(tp)
    assert ranges["f"] == (0.0, 1.0)


# ---------------------------------------------------------------------------
# build_scene
# ---------------------------------------------------------------------------

def test_build_scene_returns_correct_types(sample_toolpath, offscreen_plotter):
    actors, ranges = build_scene(offscreen_plotter, sample_toolpath)
    assert isinstance(actors, dict)
    assert isinstance(ranges, dict)


def test_build_scene_layer_actors_populated(sample_toolpath, offscreen_plotter):
    actors, _ = build_scene(offscreen_plotter, sample_toolpath)
    assert len(actors) > 0


def test_build_scene_without_bed(sample_toolpath, offscreen_plotter):
    actors, _ = build_scene(offscreen_plotter, sample_toolpath, show_bed=False)
    assert len(actors) > 0


def test_build_scene_with_travel(sample_toolpath, offscreen_plotter):
    actors, _ = build_scene(offscreen_plotter, sample_toolpath, show_travel=True)
    # At least one layer should have a travel actor
    has_travel = any(la.travel_actor is not None for la in actors.values())
    assert has_travel


def test_build_scene_layer_range_limited(sample_toolpath, offscreen_plotter):
    actors, _ = build_scene(offscreen_plotter, sample_toolpath, layer_range=(0, 0))
    # Layer 0 should exist; layers beyond 0 should have actors hidden
    for idx, la in actors.items():
        if idx > 0 and la.extrusion_actor:
            assert not la.extrusion_actor.GetVisibility()


def test_build_scene_empty_layer_skipped(offscreen_plotter):
    tp = ToolpathData(
        layers=[LayerData(z_height=0.2, layer_index=0, segments=[])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=0,
    )
    actors, _ = build_scene(offscreen_plotter, tp)
    assert 0 not in actors  # empty layer skipped


def test_build_scene_custom_line_width(sample_toolpath, offscreen_plotter):
    actors, _ = build_scene(offscreen_plotter, sample_toolpath, line_width=4.0)
    assert len(actors) > 0


@pytest.mark.parametrize("mode", list(ColorMode))
def test_build_scene_all_color_modes(mode, sample_toolpath, offscreen_plotter):
    actors, _ = build_scene(offscreen_plotter, sample_toolpath, color_mode=mode)
    assert len(actors) > 0


# ---------------------------------------------------------------------------
# recolor_layers
# ---------------------------------------------------------------------------

def test_recolor_layers_changes_colors(sample_toolpath, offscreen_plotter):
    actors, ranges = build_scene(offscreen_plotter, sample_toolpath, color_mode=ColorMode.FEATURE_TYPE)
    la = next(iter(actors.values()))
    if la.extrusion_pd is not None:
        old = la.extrusion_pd.cell_data["colors"].copy()
        recolor_layers(actors, ColorMode.HEIGHT, ranges)
        new = la.extrusion_pd.cell_data["colors"]
        assert not np.array_equal(old, new)


def test_recolor_layers_with_travel(sample_toolpath, offscreen_plotter):
    actors, ranges = build_scene(offscreen_plotter, sample_toolpath, show_travel=True)
    # Should not crash when recoloring travel
    recolor_layers(actors, ColorMode.SPEED, ranges)


def test_recolor_layers_none_pd(sample_ranges):
    la = LayerActors()
    la.extrusion_pd = None
    la.travel_pd = None
    # Should not crash
    recolor_layers({0: la}, ColorMode.HEIGHT, sample_ranges)


# ---------------------------------------------------------------------------
# _collect_distinct_values
# ---------------------------------------------------------------------------

def test_collect_distinct_values_speed(sample_toolpath):
    vals = _collect_distinct_values(sample_toolpath, ColorMode.SPEED)
    assert len(vals) > 0
    assert vals == sorted(vals)


def test_collect_distinct_values_fan_speed(sample_toolpath):
    vals = _collect_distinct_values(sample_toolpath, ColorMode.FAN_SPEED)
    assert len(vals) > 0


def test_collect_distinct_values_temperature(sample_toolpath):
    vals = _collect_distinct_values(sample_toolpath, ColorMode.TEMPERATURE)
    assert len(vals) > 0


def test_collect_distinct_values_flow(sample_toolpath):
    vals = _collect_distinct_values(sample_toolpath, ColorMode.VOLUMETRIC_FLOW)
    assert len(vals) > 0


def test_collect_distinct_values_height(sample_toolpath):
    vals = _collect_distinct_values(sample_toolpath, ColorMode.HEIGHT)
    assert len(vals) > 0


def test_collect_distinct_values_skips_travel():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.TRAVEL,
        layer_index=0, is_travel=True, feedrate=9000,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    assert _collect_distinct_values(tp, ColorMode.SPEED) == []


def test_collect_distinct_values_skips_zero_temp():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False, temperature=0.0,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    assert _collect_distinct_values(tp, ColorMode.TEMPERATURE) == []


def test_collect_distinct_values_skips_zero_flow():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False, volumetric_flow=0.0,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    assert _collect_distinct_values(tp, ColorMode.VOLUMETRIC_FLOW) == []


# ---------------------------------------------------------------------------
# add_legend
# ---------------------------------------------------------------------------

def test_add_legend_feature_type(sample_toolpath, offscreen_plotter):
    ranges = _compute_ranges(sample_toolpath)
    add_legend(offscreen_plotter, sample_toolpath, ColorMode.FEATURE_TYPE, ranges)
    # Should not crash; legend added


@pytest.mark.parametrize("mode", [
    ColorMode.HEIGHT, ColorMode.SPEED, ColorMode.FAN_SPEED,
    ColorMode.TEMPERATURE, ColorMode.VOLUMETRIC_FLOW,
])
def test_add_legend_gradient_modes(mode, sample_toolpath, offscreen_plotter):
    ranges = _compute_ranges(sample_toolpath)
    add_legend(offscreen_plotter, sample_toolpath, mode, ranges)


# ---------------------------------------------------------------------------
# _feature_type_legend
# ---------------------------------------------------------------------------

def test_feature_type_legend_counts(sample_toolpath):
    labels = _feature_type_legend(sample_toolpath)
    assert len(labels) > 0
    # Percentages should sum to ~100%
    pcts = []
    for text, _ in labels:
        pct_str = text.split()[-1].rstrip("%")
        pcts.append(float(pct_str))
    assert abs(sum(pcts) - 100.0) < 0.5


def test_feature_type_legend_absent_types():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=10, y1=10, z1=0,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False,
    )
    tp = ToolpathData(
        layers=[LayerData(z_height=0.0, layer_index=0, segments=[seg])],
        bed_x=250, bed_y=220, max_z=50,
        total_layers=1, total_segments=1,
    )
    labels = _feature_type_legend(tp)
    # Only PERIMETER should appear
    assert len(labels) == 1
    assert "Perimeter" in labels[0][0]


def test_feature_type_legend_empty():
    tp = ToolpathData(
        layers=[], bed_x=250, bed_y=220, max_z=50,
        total_layers=0, total_segments=0,
    )
    labels = _feature_type_legend(tp)
    assert labels == []
