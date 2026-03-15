# CLAUDE.md

## Build & Run

```bash
uv sync                              # install dependencies
uv run gcode-viewer file.gcode       # interactive GUI
uv run gcode-viewer file.gcode -e out.png  # CLI export
```

## Test

```bash
uv run pytest -m "not integration"   # unit tests (~2s)
uv run pytest -m integration         # integration tests (~12min, needs benchy file)
uv run pytest --cov=gcode_viewer --cov-report=term-missing  # full suite with coverage
```

Integration tests require: `/Users/rlewis/Desktop/3DBenchy_0.6n_0.2mm_PC_COREONE_1h6m.gcode`

## Architecture

src layout with hatchling build. Data pipeline:

```
extractor.py (gcode-lib → Segments) → renderer.py (PyVista PolyData) → gui.py / cli.py
```

- One PyVista actor per layer for fast visibility toggling (no rebuild on slider change)
- Color mode changes update cell_data in-place via `recolor_layers()`
- `cli.py` uses local imports inside `export_png()` and `main()` — mock at source module, not at `gcode_viewer.cli`

## Key Files

| File | Purpose |
|------|---------|
| `types.py` | `ExtrusionType` (14), `ColorMode` (6), `Segment`, `LayerData`, `ToolpathData` dataclasses |
| `extractor.py` | G-code parsing via gcode-lib, TYPE comment parsing, volumetric flow calculation |
| `colors.py` | Color palettes, gradient stops, `compute_segment_colors()`, legend label generation |
| `camera.py` | 4 camera presets + custom azimuth/elevation, `CAMERA_PRESETS` dict |
| `bed.py` | Bed plane, grid, border, origin axes (PyVista PolyData) |
| `renderer.py` | `build_scene()`, `recolor_layers()`, `add_legend()`, `_compute_ranges()` |
| `gui.py` | `GCodeViewer` class, keyboard shortcuts (1-4 cameras, T travel, V color, S screenshot) |
| `cli.py` | `build_parser()`, `export_png()`, `main()` entry point |

## Conventions

- Python >= 3.10, virtual env via `uv` (Python 3.14)
- `from __future__ import annotations` in all files
- Dataclasses with `slots=True` for Segment
- gcode-lib installed editable from `/Users/rlewis/github/gcode-lib`
- Test fixtures in `conftest.py`, parametrize over enums
- `@pytest.mark.integration` for tests requiring real gcode files
- Unreachable defensive branches marked `# pragma: no cover`

## Known Behaviors

- `gl.iter_layers()` splits on every Z change including Z-hops — layer count is inflated (e.g., 245-layer Benchy → 4522 layers)
- Purge/start gcode produces segments with negative Y coordinates
- COREONE bed is 250x220mm, auto-detected via `gl.detect_print_volume()`
- Filament diameter hardcoded at 1.75mm for volumetric flow calculation
- Default bed fallback: 250x210mm (MK4)
