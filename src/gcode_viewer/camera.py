"""Camera preset calculations for 3D toolpath viewing."""

from __future__ import annotations

import math
from typing import Callable, Dict, Tuple

from gcode_viewer.types import ToolpathData

# (camera_position, focal_point, view_up)
CameraPos = Tuple[
    Tuple[float, float, float],
    Tuple[float, float, float],
    Tuple[float, float, float],
]


def _focus_point(tp: ToolpathData) -> Tuple[float, float, float]:
    """Center of the print bounding box."""
    cx = (tp.x_min + tp.x_max) / 2
    cy = (tp.y_min + tp.y_max) / 2
    cz = (tp.z_min + tp.z_max) / 2
    return (cx, cy, cz)


def _camera_distance(tp: ToolpathData) -> float:
    """Distance ensuring the print fills the viewport comfortably."""
    dx = tp.x_max - tp.x_min
    dy = tp.y_max - tp.y_min
    dz = tp.z_max - tp.z_min
    # Use bed dimensions if larger than print bounds
    dx = max(dx, tp.bed_x)
    dy = max(dy, tp.bed_y)
    diagonal = math.sqrt(dx**2 + dy**2 + dz**2)
    return diagonal * 1.5


def camera_top_down(tp: ToolpathData) -> CameraPos:
    """Looking straight down from above."""
    fx, fy, fz = _focus_point(tp)
    d = _camera_distance(tp)
    return ((fx, fy, fz + d), (fx, fy, fz), (0, 1, 0))


def camera_front(tp: ToolpathData) -> CameraPos:
    """Looking from the front (-Y direction)."""
    fx, fy, fz = _focus_point(tp)
    d = _camera_distance(tp)
    return ((fx, fy - d, fz), (fx, fy, fz), (0, 0, 1))


def camera_side(tp: ToolpathData) -> CameraPos:
    """Looking from the right side (+X direction)."""
    fx, fy, fz = _focus_point(tp)
    d = _camera_distance(tp)
    return ((fx + d, fy, fz), (fx, fy, fz), (0, 0, 1))


def camera_isometric(tp: ToolpathData) -> CameraPos:
    """True isometric: 45deg azimuth, 35.264deg elevation."""
    fx, fy, fz = _focus_point(tp)
    d = _camera_distance(tp)
    elev = math.radians(35.264)
    azim = math.radians(45)
    cam_x = fx + d * math.cos(elev) * math.sin(azim)
    cam_y = fy - d * math.cos(elev) * math.cos(azim)
    cam_z = fz + d * math.sin(elev)
    return ((cam_x, cam_y, cam_z), (fx, fy, fz), (0, 0, 1))


def camera_custom(
    tp: ToolpathData, azimuth_deg: float, elevation_deg: float,
) -> CameraPos:
    """Arbitrary spherical camera position."""
    fx, fy, fz = _focus_point(tp)
    d = _camera_distance(tp)
    elev = math.radians(elevation_deg)
    azim = math.radians(azimuth_deg)
    cam_x = fx + d * math.cos(elev) * math.sin(azim)
    cam_y = fy - d * math.cos(elev) * math.cos(azim)
    cam_z = fz + d * math.sin(elev)
    return ((cam_x, cam_y, cam_z), (fx, fy, fz), (0, 0, 1))


CAMERA_PRESETS: Dict[str, Callable[[ToolpathData], CameraPos]] = {
    "top": camera_top_down,
    "front": camera_front,
    "side": camera_side,
    "isometric": camera_isometric,
}
