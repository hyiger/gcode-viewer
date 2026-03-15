"""Print bed geometry for visualization."""

from __future__ import annotations

import numpy as np
import pyvista as pv


def build_bed_plane(bed_x: float, bed_y: float) -> pv.PolyData:
    """Create a flat rectangular bed mesh at Z=0."""
    return pv.Plane(
        center=(bed_x / 2, bed_y / 2, 0),
        direction=(0, 0, 1),
        i_size=bed_x,
        j_size=bed_y,
    )


def build_bed_grid(bed_x: float, bed_y: float, spacing: float = 10.0) -> pv.PolyData:
    """Create grid lines on the bed surface at Z=0."""
    points = []
    lines_conn = []
    idx = 0

    # Y-parallel lines (constant X)
    x = 0.0
    while x <= bed_x + 1e-6:
        points.append([x, 0.0, 0.0])
        points.append([x, bed_y, 0.0])
        lines_conn.extend([2, idx, idx + 1])
        idx += 2
        x += spacing

    # X-parallel lines (constant Y)
    y = 0.0
    while y <= bed_y + 1e-6:
        points.append([0.0, y, 0.0])
        points.append([bed_x, y, 0.0])
        lines_conn.extend([2, idx, idx + 1])
        idx += 2
        y += spacing

    pts = np.array(points, dtype=np.float32)
    conn = np.array(lines_conn, dtype=np.int64)
    return pv.PolyData(pts, lines=conn)


def build_bed_border(bed_x: float, bed_y: float) -> pv.PolyData:
    """Create the outer border rectangle of the bed."""
    points = np.array([
        [0.0, 0.0, 0.0],
        [bed_x, 0.0, 0.0],
        [bed_x, bed_y, 0.0],
        [0.0, bed_y, 0.0],
    ], dtype=np.float32)
    lines_conn = np.array([
        2, 0, 1,
        2, 1, 2,
        2, 2, 3,
        2, 3, 0,
    ], dtype=np.int64)
    return pv.PolyData(points, lines=lines_conn)


def add_origin_axes(plotter: pv.Plotter, length: float = 30.0) -> None:
    """Add XY axis arrows at the bed origin (0, 0, 0)."""
    # X axis — red
    x_arrow = pv.Arrow(
        start=(0, 0, 0.1), direction=(1, 0, 0),
        tip_length=0.2, tip_radius=0.06, shaft_radius=0.02,
        scale=length,
    )
    plotter.add_mesh(x_arrow, color="red", lighting=False)
    plotter.add_point_labels(
        np.array([[length * 1.05, 0, 0.1]]),
        ["X"], font_size=14, text_color="red",
        shape=None, show_points=False,
    )

    # Y axis — green
    y_arrow = pv.Arrow(
        start=(0, 0, 0.1), direction=(0, 1, 0),
        tip_length=0.2, tip_radius=0.06, shaft_radius=0.02,
        scale=length,
    )
    plotter.add_mesh(y_arrow, color="green", lighting=False)
    plotter.add_point_labels(
        np.array([[0, length * 1.05, 0.1]]),
        ["Y"], font_size=14, text_color="green",
        shape=None, show_points=False,
    )
