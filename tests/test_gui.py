"""Tests for gcode_viewer.gui — interactive viewer (mocked plotter)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gcode_viewer.renderer import LayerActors
from gcode_viewer.types import ColorMode


# Patch pyvista.Plotter and build_scene to avoid real window creation
@pytest.fixture
def viewer(sample_toolpath):
    with patch("gcode_viewer.gui.pv.Plotter") as MockPlotter, \
         patch("gcode_viewer.gui.build_scene") as mock_build, \
         patch("gcode_viewer.gui.add_legend"):

        plotter = MockPlotter.return_value
        plotter.actors = {}
        plotter.legend = None

        # Build mock layer actors
        la0 = LayerActors()
        la0.extrusion_actor = MagicMock()
        la0.travel_actor = MagicMock()
        la1 = LayerActors()
        la1.extrusion_actor = MagicMock()
        la1.travel_actor = MagicMock()
        la2 = LayerActors()
        la2.extrusion_actor = MagicMock()
        la2.travel_actor = MagicMock()
        actors = {0: la0, 1: la1, 2: la2}
        ranges = {"z": (0.2, 0.6), "f": (1200, 6000), "fan": (0, 255), "temp": (200, 250), "flow": (2, 12)}
        mock_build.return_value = (actors, ranges)

        from gcode_viewer.gui import GCodeViewer
        v = GCodeViewer(sample_toolpath, "test.gcode")
        v._layer_actors = actors
        yield v


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------

def test_init_state(viewer):
    assert viewer._show_travel is False
    assert viewer._color_mode is ColorMode.FEATURE_TYPE
    assert viewer._color_mode_idx == 0


def test_init_no_filename(sample_toolpath):
    with patch("gcode_viewer.gui.pv.Plotter"), \
         patch("gcode_viewer.gui.build_scene") as mock_build, \
         patch("gcode_viewer.gui.add_legend"):
        mock_build.return_value = ({}, {})
        from gcode_viewer.gui import GCodeViewer
        v = GCodeViewer(sample_toolpath, "")
        assert v._filename == ""


# ---------------------------------------------------------------------------
# _on_layer_slider
# ---------------------------------------------------------------------------

def test_on_layer_slider_increase(viewer):
    viewer._current_max_layer = 0
    viewer._on_layer_slider(2.0)
    viewer._layer_actors[1].extrusion_actor.SetVisibility.assert_called_with(True)
    viewer._layer_actors[2].extrusion_actor.SetVisibility.assert_called_with(True)
    assert viewer._current_max_layer == 2


def test_on_layer_slider_decrease(viewer):
    viewer._current_max_layer = 2
    viewer._on_layer_slider(0.0)
    viewer._layer_actors[1].extrusion_actor.SetVisibility.assert_called_with(False)
    viewer._layer_actors[2].extrusion_actor.SetVisibility.assert_called_with(False)
    assert viewer._current_max_layer == 0


def test_on_layer_slider_no_change(viewer):
    viewer._current_max_layer = 1
    viewer._layer_actors[0].extrusion_actor.reset_mock()
    viewer._on_layer_slider(1.0)
    # No visibility changes
    viewer._layer_actors[0].extrusion_actor.SetVisibility.assert_not_called()


# ---------------------------------------------------------------------------
# _on_travel_toggle
# ---------------------------------------------------------------------------

def test_on_travel_toggle_on(viewer):
    viewer._current_max_layer = 2
    viewer._on_travel_toggle(True)
    assert viewer._show_travel is True
    viewer._layer_actors[0].travel_actor.SetVisibility.assert_called_with(True)


def test_on_travel_toggle_off(viewer):
    viewer._current_max_layer = 2
    viewer._on_travel_toggle(False)
    assert viewer._show_travel is False
    viewer._layer_actors[0].travel_actor.SetVisibility.assert_called_with(False)


# ---------------------------------------------------------------------------
# _set_camera
# ---------------------------------------------------------------------------

def test_set_camera_valid(viewer):
    viewer._set_camera("isometric")
    viewer._plotter.render.assert_called()


def test_set_camera_invalid(viewer):
    viewer._plotter.render.reset_mock()
    viewer._set_camera("nonexistent")
    viewer._plotter.render.assert_not_called()


# ---------------------------------------------------------------------------
# _toggle_travel
# ---------------------------------------------------------------------------

def test_toggle_travel(viewer):
    assert viewer._show_travel is False
    viewer._toggle_travel()
    assert viewer._show_travel is True


# ---------------------------------------------------------------------------
# _cycle_color_mode
# ---------------------------------------------------------------------------

def test_cycle_color_mode(viewer):
    with patch("gcode_viewer.gui.recolor_layers"), \
         patch("gcode_viewer.gui.add_legend"):
        viewer._cycle_color_mode()
        assert viewer._color_mode is ColorMode.HEIGHT
        assert viewer._color_mode_idx == 1


def test_cycle_color_mode_wraps(viewer):
    with patch("gcode_viewer.gui.recolor_layers"), \
         patch("gcode_viewer.gui.add_legend"):
        viewer._color_mode_idx = 5  # VOLUMETRIC_FLOW (last)
        viewer._cycle_color_mode()
        assert viewer._color_mode_idx == 0
        assert viewer._color_mode is ColorMode.FEATURE_TYPE


# ---------------------------------------------------------------------------
# _save_screenshot
# ---------------------------------------------------------------------------

def test_save_screenshot(viewer):
    viewer._save_screenshot()
    viewer._plotter.screenshot.assert_called_once_with("test_screenshot.png")


def test_save_screenshot_no_filename(viewer):
    viewer._filename = ""
    viewer._save_screenshot()
    viewer._plotter.screenshot.assert_called_with("gcode_screenshot.png")


# ---------------------------------------------------------------------------
# _on_key_press
# ---------------------------------------------------------------------------

def _fire_key(viewer, key):
    interactor = MagicMock()
    interactor.GetKeySym.return_value = key
    viewer._on_key_press(interactor, "KeyPressEvent")
    return interactor


def test_on_key_press_camera_1(viewer):
    _fire_key(viewer, "1")
    viewer._plotter.render.assert_called()


def test_on_key_press_camera_2(viewer):
    _fire_key(viewer, "2")
    viewer._plotter.render.assert_called()


def test_on_key_press_camera_3(viewer):
    _fire_key(viewer, "3")
    viewer._plotter.render.assert_called()


def test_on_key_press_camera_4(viewer):
    _fire_key(viewer, "4")
    viewer._plotter.render.assert_called()


def test_on_key_press_t(viewer):
    _fire_key(viewer, "t")
    assert viewer._show_travel is True


def test_on_key_press_v(viewer):
    with patch("gcode_viewer.gui.recolor_layers"), \
         patch("gcode_viewer.gui.add_legend"):
        _fire_key(viewer, "v")
        assert viewer._color_mode_idx == 1


def test_on_key_press_s(viewer):
    _fire_key(viewer, "s")
    viewer._plotter.screenshot.assert_called()


def test_on_key_press_unhandled(viewer):
    interactor = _fire_key(viewer, "q")
    # Not handled — SetKeyCode should NOT be called
    interactor.SetKeyCode.assert_not_called()


# ---------------------------------------------------------------------------
# show & run_app
# ---------------------------------------------------------------------------

def test_show(viewer):
    viewer._plotter.iren = MagicMock()
    viewer.show()
    viewer._plotter.show.assert_called_once()


def test_run_app(sample_toolpath):
    with patch("gcode_viewer.gui.GCodeViewer") as MockViewer:
        from gcode_viewer.gui import run_app
        run_app(sample_toolpath, "test.gcode")
        MockViewer.assert_called_once_with(sample_toolpath, "test.gcode")
        MockViewer.return_value.show.assert_called_once()
