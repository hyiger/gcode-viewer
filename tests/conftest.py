"""Shared fixtures for gcode-viewer tests."""

from __future__ import annotations

import os
from typing import Any, Dict, List

import pyvista as pv
import pytest

from gcode_viewer.types import (
    ColorMode,
    ExtrusionType,
    LayerData,
    Segment,
    ToolpathData,
)


# ---------------------------------------------------------------------------
# Segment helpers
# ---------------------------------------------------------------------------

def _make_segment(**kwargs: Any) -> Segment:
    """Create a Segment with sensible defaults; override via kwargs."""
    defaults = dict(
        x0=100.0, y0=100.0, z0=0.2,
        x1=110.0, y1=100.0, z1=0.2,
        extrusion_type=ExtrusionType.PERIMETER,
        layer_index=0,
        is_travel=False,
        feedrate=3000.0,
        fan_speed=128.0,
        temperature=210.0,
        volumetric_flow=5.0,
    )
    defaults.update(kwargs)
    return Segment(**defaults)


@pytest.fixture
def segment_factory():
    """Factory fixture — call with overrides to create a Segment."""
    return _make_segment


@pytest.fixture
def travel_segment() -> Segment:
    return _make_segment(
        is_travel=True,
        extrusion_type=ExtrusionType.TRAVEL,
        volumetric_flow=0.0,
        fan_speed=0.0,
        temperature=0.0,
        feedrate=9000.0,
    )


@pytest.fixture
def sample_segments(travel_segment) -> List[Segment]:
    """A mix of 10 segments: 7 extrusion + 3 travel."""
    segs = [
        _make_segment(extrusion_type=ExtrusionType.PERIMETER, feedrate=1800, fan_speed=0, temperature=210, volumetric_flow=3.0, z0=0.2, z1=0.2),
        _make_segment(extrusion_type=ExtrusionType.PERIMETER, feedrate=1800, fan_speed=0, temperature=210, volumetric_flow=3.2, x0=110, x1=120, z0=0.2, z1=0.2),
        _make_segment(extrusion_type=ExtrusionType.EXTERNAL_PERIMETER, feedrate=1200, fan_speed=128, temperature=215, volumetric_flow=2.5, x0=120, x1=130, z0=0.2, z1=0.2),
        _make_segment(extrusion_type=ExtrusionType.INFILL, feedrate=6000, fan_speed=255, temperature=220, volumetric_flow=12.0, x0=130, x1=140, z0=0.2, z1=0.2),
        _make_segment(extrusion_type=ExtrusionType.SOLID_INFILL, feedrate=4000, fan_speed=200, temperature=220, volumetric_flow=8.0, x0=140, x1=150, z0=0.2, z1=0.2),
        _make_segment(extrusion_type=ExtrusionType.TOP_SOLID_INFILL, feedrate=3000, fan_speed=255, temperature=210, volumetric_flow=5.0, x0=150, x1=160, z0=0.2, z1=0.2),
        _make_segment(extrusion_type=ExtrusionType.BRIDGE_INFILL, feedrate=2400, fan_speed=255, temperature=215, volumetric_flow=4.0, x0=160, x1=170, z0=0.2, z1=0.2),
        # 3 travel segments
        _make_segment(is_travel=True, extrusion_type=ExtrusionType.TRAVEL, feedrate=9000, fan_speed=0, temperature=0, volumetric_flow=0.0, x0=170, x1=100),
        _make_segment(is_travel=True, extrusion_type=ExtrusionType.TRAVEL, feedrate=9000, fan_speed=0, temperature=0, volumetric_flow=0.0, x0=100, x1=110),
        _make_segment(is_travel=True, extrusion_type=ExtrusionType.TRAVEL, feedrate=9000, fan_speed=0, temperature=0, volumetric_flow=0.0, x0=110, x1=120),
    ]
    return segs


@pytest.fixture
def sample_layer(sample_segments) -> LayerData:
    return LayerData(z_height=0.2, layer_index=0, segments=sample_segments)


def _make_layer(z: float, idx: int, n_ext: int = 5, n_trav: int = 2) -> LayerData:
    """Build a LayerData with *n_ext* extrusion + *n_trav* travel segments."""
    segs: List[Segment] = []
    for i in range(n_ext):
        segs.append(_make_segment(
            x0=100.0 + i * 10, x1=110.0 + i * 10,
            z0=z, z1=z,
            layer_index=idx,
            feedrate=1800.0 + i * 600,
            fan_speed=50.0 * i,
            temperature=200.0 + i * 5,
            volumetric_flow=2.0 + i * 2,
        ))
    for i in range(n_trav):
        segs.append(_make_segment(
            x0=150.0 + i * 10, x1=160.0 + i * 10,
            z0=z, z1=z,
            layer_index=idx,
            is_travel=True,
            extrusion_type=ExtrusionType.TRAVEL,
            feedrate=9000.0,
            fan_speed=0.0,
            temperature=0.0,
            volumetric_flow=0.0,
        ))
    return LayerData(z_height=z, layer_index=idx, segments=segs)


@pytest.fixture
def sample_toolpath() -> ToolpathData:
    """ToolpathData with 3 layers at z=0.2, 0.4, 0.6."""
    layers = [
        _make_layer(0.2, 0),
        _make_layer(0.4, 1),
        _make_layer(0.6, 2),
    ]
    return ToolpathData(
        layers=layers,
        bed_x=250.0,
        bed_y=220.0,
        max_z=50.0,
        total_layers=3,
        total_segments=sum(len(l.segments) for l in layers),
        x_min=80.0, x_max=170.0,
        y_min=60.0, y_max=160.0,
        z_min=0.2, z_max=0.6,
    )


@pytest.fixture
def sample_ranges() -> Dict[str, tuple]:
    return {
        "z": (0.2, 0.6),
        "f": (1200.0, 6000.0),
        "fan": (0.0, 255.0),
        "temp": (200.0, 250.0),
        "flow": (2.0, 12.0),
    }


# ---------------------------------------------------------------------------
# PyVista
# ---------------------------------------------------------------------------

@pytest.fixture
def offscreen_plotter():
    pl = pv.Plotter(off_screen=True, window_size=[800, 600])
    yield pl
    pl.close()


# ---------------------------------------------------------------------------
# Integration
# ---------------------------------------------------------------------------

_BENCHY_PATH = "/Users/rlewis/Desktop/3DBenchy_0.6n_0.2mm_PC_COREONE_1h6m.gcode"


@pytest.fixture
def benchy_path():
    if not os.path.isfile(_BENCHY_PATH):
        pytest.skip("Benchy gcode file not found")
    return _BENCHY_PATH
