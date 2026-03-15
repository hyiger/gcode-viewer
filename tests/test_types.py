"""Tests for gcode_viewer.types — enums and dataclasses."""

from __future__ import annotations

import pytest

from gcode_viewer.types import ColorMode, ExtrusionType, LayerData, Segment, ToolpathData


# ---------------------------------------------------------------------------
# ExtrusionType enum
# ---------------------------------------------------------------------------

_ALL_EXTRUSION_TYPES = [
    "EXTERNAL_PERIMETER", "PERIMETER", "INFILL", "SOLID_INFILL",
    "TOP_SOLID_INFILL", "BRIDGE_INFILL", "SUPPORT_MATERIAL", "SKIRT_BRIM",
    "CUSTOM", "GAP_FILL", "IRONING", "TRAVEL", "WIPE", "UNKNOWN",
]


@pytest.mark.parametrize("name", _ALL_EXTRUSION_TYPES)
def test_extrusion_type_members(name):
    assert hasattr(ExtrusionType, name)


def test_extrusion_type_count():
    assert len(ExtrusionType) == 14


# ---------------------------------------------------------------------------
# ColorMode enum
# ---------------------------------------------------------------------------

_ALL_COLOR_MODES = [
    "FEATURE_TYPE", "HEIGHT", "SPEED", "FAN_SPEED", "TEMPERATURE", "VOLUMETRIC_FLOW",
]


@pytest.mark.parametrize("name", _ALL_COLOR_MODES)
def test_color_mode_members(name):
    assert hasattr(ColorMode, name)


def test_color_mode_count():
    assert len(ColorMode) == 6


# ---------------------------------------------------------------------------
# Segment dataclass
# ---------------------------------------------------------------------------

def test_segment_creation():
    seg = Segment(
        x0=0, y0=0, z0=0.2, x1=10, y1=0, z1=0.2,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False,
    )
    assert seg.x0 == 0 and seg.x1 == 10
    assert seg.extrusion_type is ExtrusionType.PERIMETER


def test_segment_defaults():
    seg = Segment(
        x0=0, y0=0, z0=0.2, x1=10, y1=0, z1=0.2,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0, is_travel=False,
    )
    assert seg.feedrate == 0.0
    assert seg.fan_speed == 0.0
    assert seg.temperature == 0.0
    assert seg.volumetric_flow == 0.0


def test_segment_has_slots():
    seg = Segment(
        x0=0, y0=0, z0=0, x1=1, y1=1, z1=1,
        extrusion_type=ExtrusionType.UNKNOWN,
        layer_index=0, is_travel=False,
    )
    assert not hasattr(seg, "__dict__")


# ---------------------------------------------------------------------------
# LayerData dataclass
# ---------------------------------------------------------------------------

def test_layer_data_defaults():
    ld = LayerData(z_height=0.2, layer_index=0)
    assert ld.segments == []


def test_layer_data_with_segments(segment_factory):
    segs = [segment_factory(), segment_factory(x0=120)]
    ld = LayerData(z_height=0.2, layer_index=0, segments=segs)
    assert len(ld.segments) == 2


# ---------------------------------------------------------------------------
# ToolpathData dataclass
# ---------------------------------------------------------------------------

def test_toolpath_data_defaults():
    tp = ToolpathData(
        layers=[], bed_x=250, bed_y=220, max_z=50,
        total_layers=0, total_segments=0,
    )
    assert tp.x_min == 0.0 and tp.x_max == 0.0
    assert tp.y_min == 0.0 and tp.y_max == 0.0
    assert tp.z_min == 0.0 and tp.z_max == 0.0


def test_toolpath_data_full():
    tp = ToolpathData(
        layers=[], bed_x=250, bed_y=220, max_z=50,
        total_layers=3, total_segments=100,
        x_min=80, x_max=170, y_min=60, y_max=160,
        z_min=0.2, z_max=48.0,
    )
    assert tp.bed_x == 250 and tp.bed_y == 220
    assert tp.total_layers == 3
    assert tp.z_max == 48.0
