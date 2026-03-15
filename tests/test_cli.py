"""Tests for gcode_viewer.cli — argument parsing and entry point."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gcode_viewer.cli import build_parser, export_png, main


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

def test_build_parser_returns_parser():
    import argparse
    assert isinstance(build_parser(), argparse.ArgumentParser)


def test_build_parser_required_file():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["test.gcode"])
    assert args.file == "test.gcode"
    assert args.export is None
    assert args.camera == "isometric"
    assert args.layer is None
    assert args.resolution == "1920x1080"
    assert args.show_travel is False
    assert args.no_bed is False
    assert args.color_mode == "feature"


def test_build_parser_all_options():
    parser = build_parser()
    args = parser.parse_args([
        "test.gcode",
        "--export", "out.png",
        "--camera", "front",
        "--camera-azimuth", "45",
        "--camera-elevation", "30",
        "--layer", "10",
        "--resolution", "800x600",
        "--show-travel",
        "--no-bed",
        "--color-mode", "height",
    ])
    assert args.export == "out.png"
    assert args.camera == "front"
    assert args.camera_azimuth == 45.0
    assert args.camera_elevation == 30.0
    assert args.layer == 10
    assert args.resolution == "800x600"
    assert args.show_travel is True
    assert args.no_bed is True
    assert args.color_mode == "height"


@pytest.mark.parametrize("cam", ["top", "front", "side", "isometric"])
def test_build_parser_camera_choices(cam):
    parser = build_parser()
    args = parser.parse_args(["test.gcode", "--camera", cam])
    assert args.camera == cam


@pytest.mark.parametrize("mode", ["feature", "height", "speed", "fan", "temperature", "flow"])
def test_build_parser_color_mode_choices(mode):
    parser = build_parser()
    args = parser.parse_args(["test.gcode", "--color-mode", mode])
    assert args.color_mode == mode


def test_build_parser_invalid_camera():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["test.gcode", "--camera", "bogus"])


# ---------------------------------------------------------------------------
# export_png — use real off-screen rendering with sample toolpath
# ---------------------------------------------------------------------------

def _make_args(**kwargs):
    defaults = dict(
        export="out.png", camera="isometric",
        camera_azimuth=None, camera_elevation=None,
        layer=None, resolution="800x600",
        show_travel=False, no_bed=False,
        color_mode="feature",
    )
    defaults.update(kwargs)
    args = MagicMock()
    for k, v in defaults.items():
        setattr(args, k, v)
    return args


def test_export_png_preset_camera(sample_toolpath, tmp_path):
    out = str(tmp_path / "out.png")
    args = _make_args(export=out, camera="front")
    export_png(sample_toolpath, args)
    assert (tmp_path / "out.png").exists()


def test_export_png_custom_camera(sample_toolpath, tmp_path):
    out = str(tmp_path / "out.png")
    args = _make_args(export=out, camera_azimuth=45.0, camera_elevation=30.0)
    export_png(sample_toolpath, args)
    assert (tmp_path / "out.png").exists()


def test_export_png_with_layer_limit(sample_toolpath, tmp_path):
    out = str(tmp_path / "out.png")
    args = _make_args(export=out, layer=1)
    export_png(sample_toolpath, args)
    assert (tmp_path / "out.png").exists()


def test_export_png_no_bed(sample_toolpath, tmp_path):
    out = str(tmp_path / "out.png")
    args = _make_args(export=out, no_bed=True)
    export_png(sample_toolpath, args)
    assert (tmp_path / "out.png").exists()


def test_export_png_show_travel(sample_toolpath, tmp_path):
    out = str(tmp_path / "out.png")
    args = _make_args(export=out, show_travel=True)
    export_png(sample_toolpath, args)
    assert (tmp_path / "out.png").exists()


@pytest.mark.parametrize("mode_str", ["feature", "height", "speed", "fan", "temperature", "flow"])
def test_export_png_color_modes(mode_str, sample_toolpath, tmp_path):
    out = str(tmp_path / f"{mode_str}.png")
    args = _make_args(export=out, color_mode=mode_str)
    export_png(sample_toolpath, args)
    assert (tmp_path / f"{mode_str}.png").exists()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def test_main_export_mode(sample_toolpath, tmp_path):
    out = str(tmp_path / "main_out.png")
    with patch("gcode_viewer.extractor.extract_toolpath", return_value=sample_toolpath), \
         patch("sys.argv", ["gcode-viewer", "test.gcode", "--export", out, "--resolution", "400x300"]):
        main()
    assert (tmp_path / "main_out.png").exists()


def test_main_gui_mode(sample_toolpath):
    with patch("gcode_viewer.extractor.extract_toolpath", return_value=sample_toolpath), \
         patch("gcode_viewer.gui.run_app") as mock_run_app, \
         patch("sys.argv", ["gcode-viewer", "test.gcode"]):
        main()
    mock_run_app.assert_called_once_with(sample_toolpath, "test.gcode")
