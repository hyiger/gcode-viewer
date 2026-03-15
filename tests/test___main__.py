"""Tests for gcode_viewer.__main__ module."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch


def test_main_module_calls_main():
    with patch("gcode_viewer.cli.main") as mock_main:
        # Remove cached module so reload executes the module body
        sys.modules.pop("gcode_viewer.__main__", None)
        import gcode_viewer.__main__  # noqa: F401
    mock_main.assert_called_once()


def test_main_module_runs_via_subprocess():
    """Verify python -m gcode_viewer invokes the CLI."""
    result = subprocess.run(
        [sys.executable, "-m", "gcode_viewer"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 2
