"""Build PyVista geometry from toolpath segments and assemble scenes."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
import pyvista as pv

from gcode_viewer.bed import add_origin_axes, build_bed_border, build_bed_grid, build_bed_plane
from gcode_viewer.colors import (
    BACKGROUND_COLOR,
    BED_COLOR,
    BED_GRID_COLOR,
    COLOR_MODE_LABELS,
    EXTRUSION_COLORS,
    EXTRUSION_LABELS,
    TRAVEL_OPACITY,
    build_gradient_legend_labels,
    compute_segment_colors,
)
from gcode_viewer.types import ColorMode, ExtrusionType, Segment, ToolpathData

# Display order for feature-type legend
_LEGEND_ORDER = [
    ExtrusionType.PERIMETER,
    ExtrusionType.EXTERNAL_PERIMETER,
    ExtrusionType.INFILL,
    ExtrusionType.SOLID_INFILL,
    ExtrusionType.TOP_SOLID_INFILL,
    ExtrusionType.BRIDGE_INFILL,
    ExtrusionType.GAP_FILL,
    ExtrusionType.SKIRT_BRIM,
    ExtrusionType.SUPPORT_MATERIAL,
    ExtrusionType.IRONING,
    ExtrusionType.WIPE,
    ExtrusionType.CUSTOM,
    ExtrusionType.TRAVEL,
    ExtrusionType.UNKNOWN,
]


class LayerActors:
    """Per-layer rendering data: actors, polydata, and segment references."""

    __slots__ = (
        "extrusion_actor", "travel_actor",
        "extrusion_pd", "travel_pd",
        "extrusion_segs", "travel_segs",
    )

    def __init__(self) -> None:
        self.extrusion_actor: Optional[object] = None
        self.travel_actor: Optional[object] = None
        self.extrusion_pd: Optional[pv.PolyData] = None
        self.travel_pd: Optional[pv.PolyData] = None
        self.extrusion_segs: List[Segment] = []
        self.travel_segs: List[Segment] = []


def _segments_to_polydata(
    segments: List[Segment],
    mode: ColorMode,
    ranges: Dict[str, Tuple[float, float]],
) -> pv.PolyData:
    """Convert segments to PolyData with per-cell RGB colors."""
    n = len(segments)

    points = np.empty((n * 2, 3), dtype=np.float32)
    for i, seg in enumerate(segments):
        points[i * 2] = [seg.x0, seg.y0, seg.z0]
        points[i * 2 + 1] = [seg.x1, seg.y1, seg.z1]

    lines = np.empty((n, 3), dtype=np.int64)
    lines[:, 0] = 2
    lines[:, 1] = np.arange(0, n * 2, 2)
    lines[:, 2] = np.arange(1, n * 2, 2)

    poly = pv.PolyData(points, lines=lines.ravel())
    poly.cell_data["colors"] = compute_segment_colors(segments, mode, ranges)
    return poly


def _compute_ranges(toolpath: ToolpathData) -> Dict[str, Tuple[float, float]]:
    """Compute min/max ranges for all gradient color modes."""
    f_min = fan_min = temp_min = flow_min = float("inf")
    f_max = fan_max = temp_max = flow_max = float("-inf")

    for layer in toolpath.layers:
        for seg in layer.segments:
            if seg.is_travel:
                continue
            if seg.feedrate > 0:
                if seg.feedrate < f_min:
                    f_min = seg.feedrate
                if seg.feedrate > f_max:
                    f_max = seg.feedrate
            # Fan speed (include 0)
            if seg.fan_speed < fan_min:
                fan_min = seg.fan_speed
            if seg.fan_speed > fan_max:
                fan_max = seg.fan_speed
            # Temperature (skip 0 — before first M104)
            if seg.temperature > 0:
                if seg.temperature < temp_min:
                    temp_min = seg.temperature
                if seg.temperature > temp_max:
                    temp_max = seg.temperature
            # Volumetric flow (skip 0 — travel)
            if seg.volumetric_flow > 0:
                if seg.volumetric_flow < flow_min:
                    flow_min = seg.volumetric_flow
                if seg.volumetric_flow > flow_max:
                    flow_max = seg.volumetric_flow

    # Defaults for degenerate cases
    if f_min == float("inf"):
        f_min, f_max = 0.0, 1.0
    if fan_min == float("inf"):
        fan_min, fan_max = 0.0, 255.0
    if temp_min == float("inf"):
        temp_min, temp_max = 0.0, 300.0
    if flow_min == float("inf"):
        flow_min, flow_max = 0.0, 1.0

    return {
        "z": (toolpath.z_min, toolpath.z_max),
        "f": (f_min, f_max),
        "fan": (fan_min, fan_max),
        "temp": (temp_min, temp_max),
        "flow": (flow_min, flow_max),
    }


def build_scene(
    plotter: pv.Plotter,
    toolpath: ToolpathData,
    layer_range: Tuple[int, int] = (0, -1),
    show_travel: bool = False,
    show_bed: bool = True,
    line_width: float = 1.5,
    color_mode: ColorMode = ColorMode.FEATURE_TYPE,
) -> Tuple[Dict[int, LayerActors], Dict[str, Tuple[float, float]]]:
    """Add all geometry to a plotter.

    Returns (layer_actors_dict, ranges).
    """
    max_layer = layer_range[1]
    if max_layer < 0:
        max_layer = toolpath.total_layers - 1

    plotter.set_background(BACKGROUND_COLOR)

    # Bed
    if show_bed:
        bed_plane = build_bed_plane(toolpath.bed_x, toolpath.bed_y)
        plotter.add_mesh(
            bed_plane, color=BED_COLOR, opacity=0.3,
            show_edges=False, lighting=False,
        )
        bed_grid = build_bed_grid(toolpath.bed_x, toolpath.bed_y)
        plotter.add_mesh(
            bed_grid, color=BED_GRID_COLOR, line_width=0.5,
            lighting=False,
        )
        bed_border = build_bed_border(toolpath.bed_x, toolpath.bed_y)
        plotter.add_mesh(
            bed_border, color=BED_GRID_COLOR, line_width=1.5,
            lighting=False,
        )
        add_origin_axes(plotter)

    # Compute ranges for gradient modes
    ranges = _compute_ranges(toolpath)

    # Build per-layer actors
    layer_actors: Dict[int, LayerActors] = {}

    for layer in toolpath.layers:
        if not layer.segments:
            continue

        la = LayerActors()
        la.extrusion_segs = [s for s in layer.segments if not s.is_travel]
        la.travel_segs = [s for s in layer.segments if s.is_travel]
        visible = layer.layer_index <= max_layer

        if la.extrusion_segs:
            la.extrusion_pd = _segments_to_polydata(
                la.extrusion_segs, color_mode, ranges,
            )
            la.extrusion_actor = plotter.add_mesh(
                la.extrusion_pd, scalars="colors", rgb=True,
                line_width=line_width, lighting=False, show_scalar_bar=False,
            )
            la.extrusion_actor.SetVisibility(visible)

        if la.travel_segs:
            la.travel_pd = _segments_to_polydata(
                la.travel_segs, color_mode, ranges,
            )
            la.travel_actor = plotter.add_mesh(
                la.travel_pd, scalars="colors", rgb=True,
                line_width=0.5, opacity=TRAVEL_OPACITY,
                lighting=False, show_scalar_bar=False,
            )
            la.travel_actor.SetVisibility(visible and show_travel)

        layer_actors[layer.layer_index] = la

    # Legend
    add_legend(plotter, toolpath, color_mode, ranges)

    return layer_actors, ranges


def recolor_layers(
    layer_actors: Dict[int, LayerActors],
    mode: ColorMode,
    ranges: Dict[str, Tuple[float, float]],
) -> None:
    """Update cell colors on all existing PolyData for a new color mode."""
    for la in layer_actors.values():
        if la.extrusion_pd is not None and la.extrusion_segs:
            la.extrusion_pd.cell_data["colors"] = compute_segment_colors(
                la.extrusion_segs, mode, ranges,
            )
            la.extrusion_pd.Modified()
        if la.travel_pd is not None and la.travel_segs:
            la.travel_pd.cell_data["colors"] = compute_segment_colors(
                la.travel_segs, mode, ranges,
            )
            la.travel_pd.Modified()


def _collect_distinct_values(
    toolpath: ToolpathData,
    mode: ColorMode,
) -> List[float]:
    """Collect distinct display-ready values for a gradient mode."""
    raw: set = set()
    for layer in toolpath.layers:
        for seg in layer.segments:
            if seg.is_travel:
                continue
            if mode == ColorMode.SPEED:
                if seg.feedrate > 0:
                    raw.add(round(seg.feedrate / 60.0, 1))
            elif mode == ColorMode.FAN_SPEED:
                raw.add(round(seg.fan_speed / 255.0 * 100.0, 1))
            elif mode == ColorMode.TEMPERATURE:
                if seg.temperature > 0:
                    raw.add(round(seg.temperature, 1))
            elif mode == ColorMode.VOLUMETRIC_FLOW:
                if seg.volumetric_flow > 0:
                    raw.add(round(seg.volumetric_flow, 1))
            elif mode == ColorMode.HEIGHT:
                raw.add(round((seg.z0 + seg.z1) * 0.5, 1))
    return sorted(raw)


def add_legend(
    plotter: pv.Plotter,
    toolpath: ToolpathData,
    mode: ColorMode,
    ranges: Dict[str, Tuple[float, float]],
) -> None:
    """Add or replace the legend and mode label for the current color mode."""
    plotter.remove_legend()
    plotter.remove_actor("color_mode_text")

    if mode == ColorMode.FEATURE_TYPE:
        labels = _feature_type_legend(toolpath)
    elif mode == ColorMode.HEIGHT:
        z_min, z_max = ranges["z"]
        dv = _collect_distinct_values(toolpath, mode)
        labels = build_gradient_legend_labels(mode, z_min, z_max, distinct_values=dv)
    elif mode == ColorMode.SPEED:
        f_min, f_max = ranges["f"]
        dv = _collect_distinct_values(toolpath, mode)
        labels = build_gradient_legend_labels(mode, f_min / 60.0, f_max / 60.0, distinct_values=dv)
    elif mode == ColorMode.FAN_SPEED:
        fan_min, fan_max = ranges["fan"]
        dv = _collect_distinct_values(toolpath, mode)
        labels = build_gradient_legend_labels(
            mode, fan_min / 255.0 * 100.0, fan_max / 255.0 * 100.0, distinct_values=dv,
        )
    elif mode == ColorMode.TEMPERATURE:
        temp_min, temp_max = ranges["temp"]
        dv = _collect_distinct_values(toolpath, mode)
        labels = build_gradient_legend_labels(mode, temp_min, temp_max, distinct_values=dv)
    elif mode == ColorMode.VOLUMETRIC_FLOW:
        flow_min, flow_max = ranges["flow"]
        dv = _collect_distinct_values(toolpath, mode)
        labels = build_gradient_legend_labels(mode, flow_min, flow_max, distinct_values=dv)
    else:  # pragma: no cover
        return

    if not labels:
        return

    # View mode label above the legend (normalized viewport coords)
    mode_label = COLOR_MODE_LABELS[mode]
    text_actor = plotter.add_text(
        f"View: {mode_label}",
        position=(0, 0),
        font_size=11,
        color="white",
        name="color_mode_text",
    )
    text_actor.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
    text_actor.GetPositionCoordinate().SetValue(0.015, 0.97)

    # Legend sits just below the mode label
    legend_height = 0.04 * len(labels)
    plotter.add_legend(
        labels=labels,
        bcolor=(0.15, 0.15, 0.17),
        face="rectangle",
        loc="upper left",
        size=(0.20, legend_height),
    )
    # Shift legend down to leave room for the title
    legend = plotter.legend
    if legend is not None:
        pos = legend.GetPosition()
        legend.SetPosition(pos[0], pos[1] - 0.035)


def _feature_type_legend(
    toolpath: ToolpathData,
) -> List[Tuple[str, List[int]]]:
    """Build legend entries for feature-type mode."""
    counts: Counter = Counter()
    for layer in toolpath.layers:
        for seg in layer.segments:
            counts[seg.extrusion_type] += 1

    total = sum(counts.values()) or 1
    labels = []
    for etype in _LEGEND_ORDER:
        if etype not in counts:
            continue
        pct = 100.0 * counts[etype] / total
        name = EXTRUSION_LABELS.get(etype, etype.name)
        rgb = EXTRUSION_COLORS.get(etype, (0.6, 0.6, 0.6))
        color = [int(c * 255) for c in rgb]
        labels.append((f"{name}  {pct:.1f}%", color))
    return labels
