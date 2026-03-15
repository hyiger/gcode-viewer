"""Tests for gcode_viewer.camera — camera preset calculations."""

from __future__ import annotations

import math

import pytest

from gcode_viewer.camera import (
    CAMERA_PRESETS,
    _camera_distance,
    _focus_point,
    camera_custom,
    camera_front,
    camera_isometric,
    camera_side,
    camera_top_down,
)
from gcode_viewer.types import ToolpathData


@pytest.fixture
def tp():
    return ToolpathData(
        layers=[], bed_x=250, bed_y=220, max_z=50,
        total_layers=0, total_segments=0,
        x_min=80, x_max=170, y_min=60, y_max=160, z_min=0.2, z_max=48.0,
    )


# ---------------------------------------------------------------------------
# _focus_point
# ---------------------------------------------------------------------------

def test_focus_point(tp):
    fx, fy, fz = _focus_point(tp)
    assert fx == pytest.approx((80 + 170) / 2)
    assert fy == pytest.approx((60 + 160) / 2)
    assert fz == pytest.approx((0.2 + 48.0) / 2)


# ---------------------------------------------------------------------------
# _camera_distance
# ---------------------------------------------------------------------------

def test_camera_distance_positive(tp):
    d = _camera_distance(tp)
    assert d > 0


def test_camera_distance_uses_bed_when_larger(tp):
    # Bed 250x220 is larger than print bounds 90x100
    d = _camera_distance(tp)
    dx = max(170 - 80, 250)
    dy = max(160 - 60, 220)
    dz = 48.0 - 0.2
    expected = math.sqrt(dx**2 + dy**2 + dz**2) * 1.5
    assert d == pytest.approx(expected)


def test_camera_distance_uses_print_when_larger():
    tp = ToolpathData(
        layers=[], bed_x=50, bed_y=50, max_z=50,
        total_layers=0, total_segments=0,
        x_min=0, x_max=200, y_min=0, y_max=200, z_min=0, z_max=50,
    )
    d = _camera_distance(tp)
    # Print bounds 200x200 > bed 50x50
    diag = math.sqrt(200**2 + 200**2 + 50**2) * 1.5
    assert d == pytest.approx(diag)


# ---------------------------------------------------------------------------
# Camera presets
# ---------------------------------------------------------------------------

def test_camera_top_down(tp):
    pos, focus, up = camera_top_down(tp)
    fx, fy, fz = _focus_point(tp)
    assert pos[0] == pytest.approx(fx)
    assert pos[1] == pytest.approx(fy)
    assert pos[2] > fz  # camera above
    assert up == (0, 1, 0)


def test_camera_front(tp):
    pos, focus, up = camera_front(tp)
    fy = _focus_point(tp)[1]
    assert pos[1] < fy  # camera in front (-Y)
    assert up == (0, 0, 1)


def test_camera_side(tp):
    pos, focus, up = camera_side(tp)
    fx = _focus_point(tp)[0]
    assert pos[0] > fx  # camera to the right (+X)
    assert up == (0, 0, 1)


def test_camera_isometric(tp):
    pos, focus, up = camera_isometric(tp)
    fx, fy, fz = _focus_point(tp)
    # Camera should be offset in all 3 axes from focus
    assert pos[0] > fx  # +X offset
    assert pos[1] < fy  # -Y offset (front-right)
    assert pos[2] > fz  # above


def test_camera_custom(tp):
    pos, focus, up = camera_custom(tp, 90.0, 45.0)
    fx, fy, fz = _focus_point(tp)
    d = _camera_distance(tp)
    elev = math.radians(45)
    azim = math.radians(90)
    expected_x = fx + d * math.cos(elev) * math.sin(azim)
    expected_y = fy - d * math.cos(elev) * math.cos(azim)
    expected_z = fz + d * math.sin(elev)
    assert pos[0] == pytest.approx(expected_x)
    assert pos[1] == pytest.approx(expected_y)
    assert pos[2] == pytest.approx(expected_z)


def test_camera_custom_zero_angles(tp):
    pos, focus, up = camera_custom(tp, 0.0, 0.0)
    fy = _focus_point(tp)[1]
    # azim=0, elev=0 → camera along -Y axis
    assert pos[1] < fy


# ---------------------------------------------------------------------------
# CAMERA_PRESETS dict
# ---------------------------------------------------------------------------

def test_camera_presets_keys():
    assert set(CAMERA_PRESETS.keys()) == {"top", "front", "side", "isometric"}


@pytest.mark.parametrize("name", ["top", "front", "side", "isometric"])
def test_camera_presets_return_valid(name, tp):
    result = CAMERA_PRESETS[name](tp)
    assert len(result) == 3
    for part in result:
        assert len(part) == 3
