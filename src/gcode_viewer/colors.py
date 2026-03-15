"""Color definitions and gradient colormaps for visualization modes."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from gcode_viewer.types import ColorMode, ExtrusionType, Segment

# RGB tuples (0.0–1.0), PrusaSlicer-inspired palette
EXTRUSION_COLORS: Dict[ExtrusionType, Tuple[float, float, float]] = {
    ExtrusionType.EXTERNAL_PERIMETER: (1.00, 0.49, 0.22),  # orange
    ExtrusionType.PERIMETER:          (1.00, 0.90, 0.30),  # yellow
    ExtrusionType.INFILL:             (0.70, 0.22, 0.22),  # dark red
    ExtrusionType.SOLID_INFILL:       (0.82, 0.34, 0.34),  # medium red
    ExtrusionType.TOP_SOLID_INFILL:   (1.00, 0.40, 0.40),  # light red
    ExtrusionType.BRIDGE_INFILL:      (0.30, 0.50, 0.73),  # steel blue
    ExtrusionType.SUPPORT_MATERIAL:   (0.00, 1.00, 0.00),  # green
    ExtrusionType.SKIRT_BRIM:         (0.00, 0.53, 0.43),  # teal
    ExtrusionType.CUSTOM:             (0.65, 0.05, 0.90),  # purple
    ExtrusionType.GAP_FILL:           (1.00, 1.00, 1.00),  # white
    ExtrusionType.IRONING:            (1.00, 0.75, 0.80),  # pink
    ExtrusionType.TRAVEL:             (0.00, 0.60, 1.00),  # light blue
    ExtrusionType.WIPE:               (0.50, 0.50, 0.00),  # olive
    ExtrusionType.UNKNOWN:            (0.60, 0.60, 0.60),  # gray
}

TRAVEL_OPACITY = 0.15
BED_COLOR = (0.85, 0.85, 0.85)
BED_GRID_COLOR = (0.70, 0.70, 0.70)
BACKGROUND_COLOR = (0.12, 0.12, 0.14)

# Human-readable labels for the legend
EXTRUSION_LABELS: Dict[ExtrusionType, str] = {
    ExtrusionType.EXTERNAL_PERIMETER: "External perimeter",
    ExtrusionType.PERIMETER:          "Perimeter",
    ExtrusionType.INFILL:             "Infill",
    ExtrusionType.SOLID_INFILL:       "Solid infill",
    ExtrusionType.TOP_SOLID_INFILL:   "Top solid infill",
    ExtrusionType.BRIDGE_INFILL:      "Bridge infill",
    ExtrusionType.SUPPORT_MATERIAL:   "Support material",
    ExtrusionType.SKIRT_BRIM:         "Skirt/Brim",
    ExtrusionType.CUSTOM:             "Custom",
    ExtrusionType.GAP_FILL:           "Gap fill",
    ExtrusionType.IRONING:            "Ironing",
    ExtrusionType.TRAVEL:             "Travel",
    ExtrusionType.WIPE:               "Wipe",
    ExtrusionType.UNKNOWN:            "Unknown",
}

# Color mode display names
COLOR_MODE_LABELS: Dict[ColorMode, str] = {
    ColorMode.FEATURE_TYPE: "Feature type",
    ColorMode.HEIGHT: "Height (mm)",
    ColorMode.SPEED: "Speed (mm/s)",
    ColorMode.FAN_SPEED: "Fan speed (%)",
    ColorMode.TEMPERATURE: "Temperature (\u00b0C)",
    ColorMode.VOLUMETRIC_FLOW: "Flow rate (mm\u00b3/s)",
}

# ---------------------------------------------------------------------------
# Gradient colormaps — cool-to-warm style matching PrusaSlicer
# ---------------------------------------------------------------------------

# Height gradient: blue (low) → cyan → green → yellow → red (high)
_HEIGHT_STOPS = [
    (0.00, (0.00, 0.10, 0.90)),  # dark blue
    (0.25, (0.00, 0.70, 0.90)),  # cyan
    (0.50, (0.00, 0.85, 0.20)),  # green
    (0.75, (1.00, 0.85, 0.00)),  # yellow
    (1.00, (1.00, 0.15, 0.00)),  # red
]

# Speed gradient: blue (slow) → green → yellow → red (fast)
_SPEED_STOPS = [
    (0.00, (0.00, 0.20, 0.80)),  # blue (slow)
    (0.33, (0.00, 0.80, 0.30)),  # green
    (0.66, (1.00, 0.85, 0.00)),  # yellow
    (1.00, (1.00, 0.10, 0.00)),  # red (fast)
]

# Fan speed gradient: grey (off) → light blue → deep blue (full)
_FAN_STOPS = [
    (0.00, (0.40, 0.40, 0.40)),  # grey (off)
    (0.33, (0.30, 0.65, 0.90)),  # light blue
    (0.66, (0.10, 0.40, 0.90)),  # blue
    (1.00, (0.00, 0.15, 0.70)),  # deep blue (max)
]

# Temperature gradient: blue (cool) → green → yellow → red (hot)
_TEMP_STOPS = [
    (0.00, (0.10, 0.20, 0.80)),  # blue (cool)
    (0.33, (0.20, 0.80, 0.40)),  # green
    (0.66, (1.00, 0.85, 0.00)),  # yellow
    (1.00, (1.00, 0.10, 0.00)),  # red (hot)
]

# Volumetric flow gradient: teal (low) → green → amber → red (high)
_FLOW_STOPS = [
    (0.00, (0.00, 0.50, 0.35)),  # teal (low)
    (0.33, (0.30, 0.80, 0.10)),  # green
    (0.66, (1.00, 0.75, 0.00)),  # amber
    (1.00, (1.00, 0.00, 0.20)),  # red (high)
]

# Map color mode → gradient stops
_GRADIENT_STOPS: Dict[ColorMode, list] = {
    ColorMode.HEIGHT: _HEIGHT_STOPS,
    ColorMode.SPEED: _SPEED_STOPS,
    ColorMode.FAN_SPEED: _FAN_STOPS,
    ColorMode.TEMPERATURE: _TEMP_STOPS,
    ColorMode.VOLUMETRIC_FLOW: _FLOW_STOPS,
}

# Map color mode → unit string for legend
_GRADIENT_UNITS: Dict[ColorMode, str] = {
    ColorMode.HEIGHT: "mm",
    ColorMode.SPEED: "mm/s",
    ColorMode.FAN_SPEED: "%",
    ColorMode.TEMPERATURE: "\u00b0C",
    ColorMode.VOLUMETRIC_FLOW: "mm\u00b3/s",
}


def _lerp_color(
    t: float,
    stops: List[Tuple[float, Tuple[float, float, float]]],
) -> Tuple[float, float, float]:
    """Linearly interpolate between color stops at position t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return (
                c0[0] + f * (c1[0] - c0[0]),
                c0[1] + f * (c1[1] - c0[1]),
                c0[2] + f * (c1[2] - c0[2]),
            )
    return stops[-1][1]  # pragma: no cover


def color_for_feature(seg: Segment) -> Tuple[float, float, float]:
    """Return RGB for a segment based on feature type."""
    return EXTRUSION_COLORS.get(seg.extrusion_type, (0.6, 0.6, 0.6))


def _gradient_color(
    value: float, val_min: float, val_range: float,
    stops: list,
) -> Tuple[float, float, float]:
    """Return RGB by mapping value into [0,1] over the gradient stops."""
    t = (value - val_min) / val_range if val_range > 0 else 0.5
    return _lerp_color(t, stops)


def compute_segment_colors(
    segments: List[Segment],
    mode: ColorMode,
    ranges: Dict[str, Tuple[float, float]],
) -> np.ndarray:
    """Compute an Nx3 uint8 color array for segments in the given mode.

    *ranges* maps range keys to (min, max) tuples:
        'z', 'f', 'fan', 'temp', 'flow'
    """
    n = len(segments)
    colors = np.empty((n, 3), dtype=np.uint8)

    if mode == ColorMode.FEATURE_TYPE:
        for i, seg in enumerate(segments):
            rgb = color_for_feature(seg)
            colors[i] = [int(c * 255) for c in rgb]
        return colors

    # Gradient modes: pick the right value accessor, range, and stops
    z_min, z_max = ranges.get("z", (0.0, 1.0))
    f_min, f_max = ranges.get("f", (0.0, 1.0))
    fan_min, fan_max = ranges.get("fan", (0.0, 255.0))
    temp_min, temp_max = ranges.get("temp", (0.0, 300.0))
    flow_min, flow_max = ranges.get("flow", (0.0, 1.0))

    stops = _GRADIENT_STOPS.get(mode, _HEIGHT_STOPS)

    for i, seg in enumerate(segments):
        if mode == ColorMode.HEIGHT:
            val = (seg.z0 + seg.z1) * 0.5
            vmin, vrange = z_min, z_max - z_min
        elif mode == ColorMode.SPEED:
            val, vmin, vrange = seg.feedrate, f_min, f_max - f_min
        elif mode == ColorMode.FAN_SPEED:
            val, vmin, vrange = seg.fan_speed, fan_min, fan_max - fan_min
        elif mode == ColorMode.TEMPERATURE:
            val, vmin, vrange = seg.temperature, temp_min, temp_max - temp_min
        elif mode == ColorMode.VOLUMETRIC_FLOW:
            val, vmin, vrange = seg.volumetric_flow, flow_min, flow_max - flow_min
        else:  # pragma: no cover
            colors[i] = [153, 153, 153]
            continue
        rgb = _gradient_color(val, vmin, vrange, stops)
        colors[i] = [int(c * 255) for c in rgb]

    return colors


def build_gradient_legend_labels(
    mode: ColorMode,
    val_min: float,
    val_max: float,
    steps: int = 8,
    distinct_values: Optional[List[float]] = None,
) -> List[Tuple[str, List[int]]]:
    """Build legend labels for gradient color modes.

    If *distinct_values* is provided and has <= *steps* entries, each
    distinct value gets its own legend row instead of interpolating.
    """
    stops = _GRADIENT_STOPS.get(mode, _HEIGHT_STOPS)
    unit = _GRADIENT_UNITS.get(mode, "")
    val_range = val_max - val_min

    # Constant value — single entry
    if abs(val_range) < 1e-6:
        rgb = _lerp_color(0.5, stops)
        color = [int(c * 255) for c in rgb]
        return [(f"{val_min:.1f} {unit}", color)]

    # Use actual distinct values when there are few enough
    if distinct_values is not None and len(distinct_values) <= steps:
        labels = []
        for val in sorted(distinct_values):
            t = (val - val_min) / val_range
            text = f"{val:.1f} {unit}"
            rgb = _lerp_color(t, stops)
            color = [int(c * 255) for c in rgb]
            labels.append((text, color))
        return labels

    # Interpolate evenly, deduplicating display strings
    labels = []
    seen: set = set()
    for i in range(steps):
        t = i / max(steps - 1, 1)
        val = val_min + t * val_range
        text = f"{val:.1f} {unit}"
        if text in seen:
            continue
        seen.add(text)
        rgb = _lerp_color(t, stops)
        color = [int(c * 255) for c in rgb]
        labels.append((text, color))

    return labels
