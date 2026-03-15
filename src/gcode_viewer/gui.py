"""Interactive GUI for gcode-viewer using PyVista's native plotter."""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import pyvista as pv

from gcode_viewer.camera import CAMERA_PRESETS
from gcode_viewer.colors import BACKGROUND_COLOR
from gcode_viewer.extractor import extract_toolpath
from gcode_viewer.renderer import LayerActors, add_legend, build_scene, recolor_layers
from gcode_viewer.types import ColorMode, ToolpathData


# Ordered list of color modes for cycling
_COLOR_MODES = [
    ColorMode.FEATURE_TYPE,
    ColorMode.HEIGHT,
    ColorMode.SPEED,
    ColorMode.FAN_SPEED,
    ColorMode.TEMPERATURE,
    ColorMode.VOLUMETRIC_FLOW,
]


class GCodeViewer:
    """Interactive G-code viewer using PyVista's built-in plotter."""

    def __init__(
        self,
        toolpath: ToolpathData,
        filename: str = "",
    ) -> None:
        self._toolpath = toolpath
        self._filename = filename
        self._show_travel = False
        self._current_max_layer = toolpath.total_layers - 1
        self._layer_actors: Dict[int, LayerActors] = {}
        self._color_mode = ColorMode.FEATURE_TYPE
        self._color_mode_idx = 0
        self._ranges: Dict[str, Tuple[float, float]] = {}

        # Create plotter
        self._plotter = pv.Plotter(
            title=f"G-Code Viewer \u2014 {os.path.basename(filename)}" if filename else "G-Code Viewer",
            window_size=[1400, 900],
        )
        self._plotter.set_background(BACKGROUND_COLOR)

        # Build the scene
        self._layer_actors, self._ranges = build_scene(
            self._plotter,
            toolpath,
            layer_range=(0, self._current_max_layer),
            show_travel=False,
            show_bed=True,
            color_mode=self._color_mode,
        )

        # Layer slider
        self._plotter.add_slider_widget(
            self._on_layer_slider,
            rng=[0, toolpath.total_layers - 1],
            value=toolpath.total_layers - 1,
            title="Layer",
            pointa=(0.02, 0.07),
            pointb=(0.55, 0.07),
            style="modern",
            fmt="%.0f",
        )

        # Travel checkbox
        self._plotter.add_checkbox_button_widget(
            self._on_travel_toggle,
            value=False,
            position=(10, 10),
            size=30,
            color_on="lightblue",
            color_off="grey",
        )
        self._plotter.add_text(
            "Travel",
            position=(45, 10),
            font_size=10,
            color="white",
        )

        # Help text
        self._plotter.add_text(
            "Keys: 1=Iso 2=Top 3=Front 4=Side  T=Travel  V=View mode  S=Screenshot",
            position="upper_right",
            font_size=9,
            color="white",
            name="help_text",
        )

        # Status text
        name = os.path.basename(filename) if filename else "untitled"
        self._plotter.add_text(
            f"{name}  |  {toolpath.total_layers} layers  |  "
            f"{toolpath.total_segments:,} segments  |  "
            f"bed {toolpath.bed_x:.0f}x{toolpath.bed_y:.0f} mm",
            position=(10, 80),
            font_size=9,
            color="white",
            name="status_text",
        )

        # Set initial camera
        self._set_camera("isometric")

    def _setup_key_events(self) -> None:
        """Install key event handler via VTK observer (higher priority)."""
        interactor = self._plotter.iren.interactor
        interactor.AddObserver("KeyPressEvent", self._on_key_press, 10.0)

    def _on_key_press(self, interactor, event) -> None:
        """Handle key presses at VTK level."""
        key = interactor.GetKeySym()
        handled = True

        if key == "1":
            self._set_camera("isometric")
        elif key == "2":
            self._set_camera("top")
        elif key == "3":
            self._set_camera("front")
        elif key == "4":
            self._set_camera("side")
        elif key in ("t", "T"):
            self._toggle_travel()
        elif key in ("v", "V"):
            self._cycle_color_mode()
        elif key in ("s", "S"):
            self._save_screenshot()
        else:
            handled = False

        if handled:
            interactor.SetKeyCode("\0")
            interactor.SetKeySym("")

    def _on_layer_slider(self, value: float) -> None:
        target = int(round(value))
        if target == self._current_max_layer:
            return

        show_travel = self._show_travel
        prev = self._current_max_layer

        if target > prev:
            for idx in range(prev + 1, target + 1):
                la = self._layer_actors.get(idx)
                if la:
                    if la.extrusion_actor:
                        la.extrusion_actor.SetVisibility(True)
                    if la.travel_actor:
                        la.travel_actor.SetVisibility(show_travel)
        else:
            for idx in range(target + 1, prev + 1):
                la = self._layer_actors.get(idx)
                if la:
                    if la.extrusion_actor:
                        la.extrusion_actor.SetVisibility(False)
                    if la.travel_actor:
                        la.travel_actor.SetVisibility(False)

        self._current_max_layer = target
        self._plotter.render()

    def _on_travel_toggle(self, state: bool) -> None:
        self._show_travel = state
        for idx, la in self._layer_actors.items():
            if la.travel_actor:
                visible = state and idx <= self._current_max_layer
                la.travel_actor.SetVisibility(visible)
        self._plotter.render()

    def _set_camera(self, name: str) -> None:
        if name in CAMERA_PRESETS:
            cam = CAMERA_PRESETS[name](self._toolpath)
            self._plotter.camera_position = cam
            self._plotter.render()

    def _toggle_travel(self) -> None:
        self._show_travel = not self._show_travel
        self._on_travel_toggle(self._show_travel)

    def _cycle_color_mode(self) -> None:
        """Cycle to the next color mode."""
        self._color_mode_idx = (self._color_mode_idx + 1) % len(_COLOR_MODES)
        self._color_mode = _COLOR_MODES[self._color_mode_idx]

        # Recolor all layers
        recolor_layers(self._layer_actors, self._color_mode, self._ranges)

        # Update legend (also updates view mode label)
        add_legend(self._plotter, self._toolpath, self._color_mode, self._ranges)

        self._plotter.render()

    def _save_screenshot(self) -> None:
        base = os.path.splitext(os.path.basename(self._filename))[0] or "gcode"
        path = f"{base}_screenshot.png"
        self._plotter.screenshot(path)
        print(f"Screenshot saved: {path}")

    def show(self) -> None:
        """Show the interactive window (blocks until closed)."""
        self._setup_key_events()
        self._plotter.show()


def run_app(toolpath: ToolpathData, filename: str = "") -> None:
    """Launch the interactive GUI."""
    viewer = GCodeViewer(toolpath, filename)
    viewer.show()
