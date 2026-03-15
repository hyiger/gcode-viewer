"""CLI entry point for gcode-viewer."""

from __future__ import annotations

import argparse
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gcode-viewer",
        description="Visualize G-code toolpaths in 3D",
    )
    parser.add_argument("file", help="Path to .gcode or .bgcode file")

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--gui", action="store_true", default=True,
        help="Launch interactive GUI (default)",
    )
    mode.add_argument(
        "--export", "-e", metavar="OUTPUT.png",
        help="Export static PNG image and exit",
    )

    parser.add_argument(
        "--camera", "-c", default="isometric",
        choices=["top", "front", "side", "isometric"],
        help="Camera angle preset (default: isometric)",
    )
    parser.add_argument(
        "--camera-azimuth", type=float, default=None,
        help="Custom camera azimuth in degrees",
    )
    parser.add_argument(
        "--camera-elevation", type=float, default=None,
        help="Custom camera elevation in degrees",
    )
    parser.add_argument(
        "--layer", "-l", type=int, default=None,
        help="Maximum layer to show (default: all)",
    )
    parser.add_argument(
        "--resolution", "-r", default="1920x1080",
        help="Export resolution WxH (default: 1920x1080)",
    )
    parser.add_argument(
        "--show-travel", action="store_true",
        help="Show travel moves",
    )
    parser.add_argument(
        "--no-bed", action="store_true",
        help="Hide print bed",
    )
    parser.add_argument(
        "--color-mode", default="feature",
        choices=["feature", "height", "speed", "fan", "temperature", "flow"],
        help="Color mode for visualization (default: feature)",
    )

    return parser


def export_png(toolpath, args) -> None:
    """Render to off-screen plotter and save PNG."""
    import pyvista as pv

    from gcode_viewer.camera import CAMERA_PRESETS, camera_custom
    from gcode_viewer.renderer import build_scene
    from gcode_viewer.types import ColorMode

    color_mode_map = {
        "feature": ColorMode.FEATURE_TYPE,
        "height": ColorMode.HEIGHT,
        "speed": ColorMode.SPEED,
        "fan": ColorMode.FAN_SPEED,
        "temperature": ColorMode.TEMPERATURE,
        "flow": ColorMode.VOLUMETRIC_FLOW,
    }
    color_mode = color_mode_map[args.color_mode]

    w, h = map(int, args.resolution.split("x"))
    plotter = pv.Plotter(off_screen=True, window_size=[w, h])

    max_layer = args.layer if args.layer is not None else toolpath.total_layers - 1
    build_scene(
        plotter,
        toolpath,
        layer_range=(0, max_layer),
        show_travel=args.show_travel,
        show_bed=not args.no_bed,
        color_mode=color_mode,
    )

    if args.camera_azimuth is not None and args.camera_elevation is not None:
        cam = camera_custom(toolpath, args.camera_azimuth, args.camera_elevation)
    else:
        cam = CAMERA_PRESETS[args.camera](toolpath)
    plotter.camera_position = cam

    plotter.screenshot(args.export)
    plotter.close()
    print(f"Saved: {args.export}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    from gcode_viewer.extractor import extract_toolpath

    print(f"Loading {args.file}...")
    toolpath = extract_toolpath(args.file)
    print(
        f"  {toolpath.total_layers} layers, "
        f"{toolpath.total_segments} segments, "
        f"bed {toolpath.bed_x}x{toolpath.bed_y} mm"
    )

    if args.export:
        export_png(toolpath, args)
    else:
        from gcode_viewer.gui import run_app
        run_app(toolpath, args.file)
