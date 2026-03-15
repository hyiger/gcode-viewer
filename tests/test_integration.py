"""Integration tests using real benchy gcode file."""

from __future__ import annotations

import numpy as np
import pyvista as pv
import pytest

from gcode_viewer.extractor import extract_toolpath
from gcode_viewer.renderer import _compute_ranges, build_scene, recolor_layers
from gcode_viewer.types import ColorMode, ExtrusionType


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def benchy_toolpath():
    path = "/Users/rlewis/Desktop/3DBenchy_0.6n_0.2mm_PC_COREONE_1h6m.gcode"
    import os
    if not os.path.isfile(path):
        pytest.skip("Benchy gcode file not found")
    return extract_toolpath(path)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def test_extract_layer_count(benchy_toolpath):
    assert benchy_toolpath.total_layers > 200


def test_extract_segment_count(benchy_toolpath):
    assert benchy_toolpath.total_segments > 10000


def test_extract_bed_dimensions(benchy_toolpath):
    assert benchy_toolpath.bed_x == 250.0
    assert benchy_toolpath.bed_y == 220.0


def test_extract_z_max(benchy_toolpath):
    assert benchy_toolpath.z_max > 30


def test_feature_types_present(benchy_toolpath):
    types_found = set()
    for layer in benchy_toolpath.layers:
        for seg in layer.segments:
            types_found.add(seg.extrusion_type)
    expected = {
        ExtrusionType.PERIMETER,
        ExtrusionType.EXTERNAL_PERIMETER,
        ExtrusionType.SOLID_INFILL,
        ExtrusionType.TRAVEL,
    }
    assert expected.issubset(types_found)


def test_segment_bounds(benchy_toolpath):
    for layer in benchy_toolpath.layers:
        for seg in layer.segments:
            assert -25 <= seg.x0 <= 260
            assert -25 <= seg.y0 <= 230
            assert seg.z0 >= 0
            assert -25 <= seg.x1 <= 260
            assert -25 <= seg.y1 <= 230
            assert seg.z1 >= 0


# ---------------------------------------------------------------------------
# Scene building
# ---------------------------------------------------------------------------

def test_build_scene_offscreen(benchy_toolpath):
    pl = pv.Plotter(off_screen=True, window_size=[800, 600])
    actors, ranges = build_scene(pl, benchy_toolpath)
    assert len(actors) > 0
    assert "z" in ranges
    pl.close()


def test_export_png(benchy_toolpath, tmp_path):
    pl = pv.Plotter(off_screen=True, window_size=[800, 600])
    build_scene(pl, benchy_toolpath)
    from gcode_viewer.camera import camera_isometric
    pl.camera_position = camera_isometric(benchy_toolpath)
    out = tmp_path / "benchy.png"
    pl.screenshot(str(out))
    pl.close()
    assert out.exists()
    assert out.stat().st_size > 1000


@pytest.mark.parametrize("mode", list(ColorMode))
def test_all_color_modes_export(mode, benchy_toolpath, tmp_path):
    pl = pv.Plotter(off_screen=True, window_size=[800, 600])
    build_scene(pl, benchy_toolpath, color_mode=mode)
    from gcode_viewer.camera import camera_isometric
    pl.camera_position = camera_isometric(benchy_toolpath)
    out = tmp_path / f"{mode.name}.png"
    pl.screenshot(str(out))
    pl.close()
    assert out.exists()
    assert out.stat().st_size > 1000


def test_compute_ranges_real(benchy_toolpath):
    ranges = _compute_ranges(benchy_toolpath)
    f_min, f_max = ranges["f"]
    assert f_min < f_max
    fan_min, fan_max = ranges["fan"]
    assert fan_min <= fan_max
    temp_min, temp_max = ranges["temp"]
    assert temp_min <= temp_max
    flow_min, flow_max = ranges["flow"]
    assert flow_min < flow_max


def test_recolor_real(benchy_toolpath):
    pl = pv.Plotter(off_screen=True, window_size=[800, 600])
    actors, ranges = build_scene(pl, benchy_toolpath, color_mode=ColorMode.FEATURE_TYPE)
    for mode in [ColorMode.HEIGHT, ColorMode.SPEED, ColorMode.FAN_SPEED,
                 ColorMode.TEMPERATURE, ColorMode.VOLUMETRIC_FLOW]:
        recolor_layers(actors, mode, ranges)
    pl.close()
