"""Tests for gcode_viewer.bed — bed geometry generation."""

from __future__ import annotations

import numpy as np
import pyvista as pv
import pytest

from gcode_viewer.bed import add_origin_axes, build_bed_border, build_bed_grid, build_bed_plane


# ---------------------------------------------------------------------------
# build_bed_plane
# ---------------------------------------------------------------------------

def test_bed_plane_returns_polydata():
    mesh = build_bed_plane(250, 220)
    assert isinstance(mesh, pv.PolyData)


def test_bed_plane_dimensions():
    mesh = build_bed_plane(250, 220)
    xmin, xmax, ymin, ymax, zmin, zmax = mesh.bounds
    assert abs(xmax - xmin - 250) < 1.0
    assert abs(ymax - ymin - 220) < 1.0
    assert abs(zmin) < 0.01 and abs(zmax) < 0.01


# ---------------------------------------------------------------------------
# build_bed_grid
# ---------------------------------------------------------------------------

def test_bed_grid_returns_polydata():
    mesh = build_bed_grid(100, 100, spacing=10)
    assert isinstance(mesh, pv.PolyData)
    assert mesh.n_lines > 0


def test_bed_grid_line_count():
    # 100/10 + 1 = 11 lines in each direction → 22 total
    mesh = build_bed_grid(100, 100, spacing=10)
    assert mesh.n_lines == 22


def test_bed_grid_custom_spacing():
    mesh = build_bed_grid(100, 100, spacing=25)
    # 0,25,50,75,100 → 5 per direction → 10 total
    assert mesh.n_lines == 10


def test_bed_grid_bounds():
    mesh = build_bed_grid(200, 150, spacing=10)
    xmin, xmax, ymin, ymax, _, _ = mesh.bounds
    assert xmin >= -0.01 and xmax <= 200.01
    assert ymin >= -0.01 and ymax <= 150.01


# ---------------------------------------------------------------------------
# build_bed_border
# ---------------------------------------------------------------------------

def test_bed_border_points():
    mesh = build_bed_border(250, 220)
    assert mesh.n_points == 4


def test_bed_border_lines():
    mesh = build_bed_border(250, 220)
    assert mesh.n_lines == 4


# ---------------------------------------------------------------------------
# add_origin_axes
# ---------------------------------------------------------------------------

def test_add_origin_axes(offscreen_plotter):
    before = len(offscreen_plotter.actors)
    add_origin_axes(offscreen_plotter)
    after = len(offscreen_plotter.actors)
    assert after > before


def test_add_origin_axes_custom_length(offscreen_plotter):
    add_origin_axes(offscreen_plotter, length=50.0)
    assert len(offscreen_plotter.actors) > 0
