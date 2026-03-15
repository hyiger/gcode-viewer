"""Extract toolpath segments from G-code files using gcode-lib."""

from __future__ import annotations

import math
import re
from typing import List

import gcode_lib as gl

from gcode_viewer.types import ExtrusionType, LayerData, Segment, ToolpathData

_TYPE_RE = re.compile(r";\s*TYPE:(.+)")
_S_RE = re.compile(r"[Ss]\s*(-?[\d.]+)")
_R_RE = re.compile(r"[Rr]\s*(-?[\d.]+)")

_TYPE_MAP = {
    "External perimeter": ExtrusionType.EXTERNAL_PERIMETER,
    "Perimeter":          ExtrusionType.PERIMETER,
    "Overhang perimeter": ExtrusionType.EXTERNAL_PERIMETER,
    "Infill":             ExtrusionType.INFILL,
    "Solid infill":       ExtrusionType.SOLID_INFILL,
    "Top solid infill":   ExtrusionType.TOP_SOLID_INFILL,
    "Bridge infill":      ExtrusionType.BRIDGE_INFILL,
    "Support material":   ExtrusionType.SUPPORT_MATERIAL,
    "Support material interface": ExtrusionType.SUPPORT_MATERIAL,
    "Skirt/Brim":         ExtrusionType.SKIRT_BRIM,
    "Skirt":              ExtrusionType.SKIRT_BRIM,
    "Custom":             ExtrusionType.CUSTOM,
    "Gap fill":           ExtrusionType.GAP_FILL,
    "Ironing":            ExtrusionType.IRONING,
    "Wipe tower":         ExtrusionType.WIPE,
}

# Default bed dimensions (MK4) if auto-detection fails
_DEFAULT_BED_X = 250.0
_DEFAULT_BED_Y = 210.0
_DEFAULT_MAX_Z = 220.0

# Filament cross-section area for volumetric flow calculation
_FILAMENT_DIAMETER = 1.75  # mm
_FILAMENT_AREA = math.pi * (_FILAMENT_DIAMETER / 2) ** 2  # ~2.405 mm²


def _parse_type_comment(comment: str) -> ExtrusionType | None:
    """Parse a PrusaSlicer TYPE comment, returning the extrusion type or None."""
    m = _TYPE_RE.match(comment.strip())
    if m:
        return _TYPE_MAP.get(m.group(1).strip(), ExtrusionType.UNKNOWN)
    return None


def _get_s_param(line: gl.GCodeLine) -> float | None:
    """Extract S parameter from a line (gcode-lib doesn't parse S into words)."""
    m = _S_RE.search(line.raw)
    return float(m.group(1)) if m else None


def _get_s_or_r_param(line: gl.GCodeLine) -> float | None:
    """Extract S or R (temperature) parameter from M104/M109 lines."""
    s = _get_s_param(line)
    if s is not None:
        return s
    m = _R_RE.search(line.raw)
    return float(m.group(1)) if m else None


def _is_positive_extrusion(line: gl.GCodeLine, state: gl.ModalState) -> bool:
    """Check if a move line has positive extrusion (deposits material)."""
    if "E" not in line.words:
        return False
    e_val = line.words["E"]
    if state.abs_e:
        return e_val > state.e
    return e_val > 0.0


def extract_toolpath(path: str) -> ToolpathData:
    """Load a G-code file and extract all toolpath segments by layer."""
    gf = gl.load(path)

    # Linearize arcs to G1 segments for simpler rendering
    lines = gl.linearize_arcs(gf.lines)

    # Detect bed dimensions
    volume = gl.detect_print_volume(lines)
    if volume:
        bed_x = volume["bed_x"]
        bed_y = volume["bed_y"]
        max_z = volume["max_z"]
    else:
        bed_x, bed_y, max_z = _DEFAULT_BED_X, _DEFAULT_BED_Y, _DEFAULT_MAX_Z

    # Compute stats for bounds
    stats = gl.compute_stats(lines)
    bounds = stats.bounds

    # Extract segments layer by layer
    layers: List[LayerData] = []
    total_segments = 0
    current_type = ExtrusionType.UNKNOWN

    for layer_idx, (z_height, layer_lines) in enumerate(gl.iter_layers(lines)):
        layer = LayerData(z_height=z_height, layer_index=layer_idx)
        state = gl.ModalState()

        # We need to track state from the beginning for correct positions.
        # iter_layers gives us lines per layer, but we need the state at the
        # start of each layer. We'll use advance_state manually.
        # For the first layer the initial state is (0,0,0). For subsequent
        # layers we carry state forward via the main loop below.

        layers.append(layer)

    # Re-do extraction with full state tracking across all layers
    layers.clear()
    state = gl.ModalState()
    current_type = ExtrusionType.UNKNOWN
    current_fan = 0.0    # M106 S value (0–255)
    current_temp = 0.0   # hotend target °C
    layer_idx = 0

    for z_height, layer_lines in gl.iter_layers(lines):
        layer = LayerData(z_height=z_height, layer_index=layer_idx)

        for line in layer_lines:
            # Check for TYPE comment
            if line.comment:
                parsed = _parse_type_comment(line.comment)
                if parsed is not None:
                    current_type = parsed

            # Track M-code state (S not in words — parse from raw)
            cmd = line.command or ""
            if cmd == "M106":
                s = _get_s_param(line)
                if s is not None:
                    current_fan = s
                else:
                    current_fan = 255.0  # M106 without S means full
            elif cmd == "M107":
                current_fan = 0.0
            elif cmd in ("M104", "M109"):
                t = _get_s_or_r_param(line)
                if t is not None:
                    current_temp = t

            # Only process moves (G0/G1)
            if line.is_move and ("X" in line.words or "Y" in line.words):
                # Compute endpoint
                if state.abs_xy:
                    x1 = line.words.get("X", state.x)
                    y1 = line.words.get("Y", state.y)
                    z1 = line.words.get("Z", state.z)
                else:
                    x1 = state.x + line.words.get("X", 0.0)
                    y1 = state.y + line.words.get("Y", 0.0)
                    z1 = state.z + line.words.get("Z", 0.0)

                # Classify move
                is_travel = not _is_positive_extrusion(line, state)
                seg_type = ExtrusionType.TRAVEL if is_travel else current_type

                # Feedrate: use F from this line, or carry forward from state
                f = line.words.get("F", state.f or 0.0)

                # Compute E delta for volumetric flow
                vol_flow = 0.0
                if not is_travel and "E" in line.words:
                    if state.abs_e:
                        e_delta = line.words["E"] - state.e
                    else:
                        e_delta = line.words["E"]
                    if e_delta > 0 and f > 0:
                        dx = x1 - state.x
                        dy = y1 - state.y
                        dz = z1 - state.z
                        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                        if dist > 0:
                            # volume / time = (e_delta * area) / (dist / (f/60))
                            vol_flow = e_delta * _FILAMENT_AREA * f / (dist * 60.0)

                seg = Segment(
                    x0=state.x, y0=state.y, z0=state.z,
                    x1=x1, y1=y1, z1=z1,
                    extrusion_type=seg_type,
                    layer_index=layer_idx,
                    is_travel=is_travel,
                    feedrate=f,
                    fan_speed=current_fan,
                    temperature=current_temp,
                    volumetric_flow=vol_flow,
                )
                layer.segments.append(seg)
                total_segments += 1

            gl.advance_state(state, line)

        layers.append(layer)
        layer_idx += 1

    return ToolpathData(
        layers=layers,
        bed_x=bed_x,
        bed_y=bed_y,
        max_z=max_z,
        total_layers=len(layers),
        total_segments=total_segments,
        x_min=bounds.x_min if bounds.valid else 0.0,
        x_max=bounds.x_max if bounds.valid else bed_x,
        y_min=bounds.y_min if bounds.valid else 0.0,
        y_max=bounds.y_max if bounds.valid else bed_y,
        z_min=bounds.z_min if bounds.valid else 0.0,
        z_max=bounds.z_max if bounds.valid else max_z,
    )
