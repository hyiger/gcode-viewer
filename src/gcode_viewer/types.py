"""Data types for gcode-viewer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


class ExtrusionType(Enum):
    """Extrusion type parsed from PrusaSlicer TYPE comments."""

    EXTERNAL_PERIMETER = auto()
    PERIMETER = auto()
    INFILL = auto()
    SOLID_INFILL = auto()
    TOP_SOLID_INFILL = auto()
    BRIDGE_INFILL = auto()
    SUPPORT_MATERIAL = auto()
    SKIRT_BRIM = auto()
    CUSTOM = auto()
    GAP_FILL = auto()
    IRONING = auto()
    TRAVEL = auto()
    WIPE = auto()
    UNKNOWN = auto()


class ColorMode(Enum):
    """Available visualization color modes."""

    FEATURE_TYPE = auto()
    HEIGHT = auto()
    SPEED = auto()
    FAN_SPEED = auto()
    TEMPERATURE = auto()
    VOLUMETRIC_FLOW = auto()


@dataclass(slots=True)
class Segment:
    """A single toolpath line segment."""

    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float
    extrusion_type: ExtrusionType
    layer_index: int
    is_travel: bool
    feedrate: float = 0.0        # mm/min
    fan_speed: float = 0.0       # 0–255 PWM value
    temperature: float = 0.0     # °C hotend target
    volumetric_flow: float = 0.0 # mm³/s


@dataclass
class LayerData:
    """All segments belonging to a single layer."""

    z_height: float
    layer_index: int
    segments: List[Segment] = field(default_factory=list)


@dataclass
class ToolpathData:
    """Complete extracted toolpath ready for rendering."""

    layers: List[LayerData]
    bed_x: float
    bed_y: float
    max_z: float
    total_layers: int
    total_segments: int
    # Bounding box of the print (from gcode_lib.Bounds)
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    z_min: float = 0.0
    z_max: float = 0.0
