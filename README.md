# Any‑Shape Wafer Layout (NanoRosetta‑style) – CLI MVP

CLI tool that places large numbers of PDF pages “around” any inner shape and constrained to any outer shape. Inputs are PDF pages and SVG paths (inner keep‑outs and outer boundary). Exports a vector PDF proof and optional 1‑bit TIFF suitable for laser workflows.

Spec references: NanoRosetta’s process and wafer geometry described at [nanorosetta.com/technology](https://nanorosetta.com/technology/).

## Install

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Example: wrap around a center circle (inner keep‑out) and constrain to a rectangle (outer boundary):

```bash
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --output ./out/proof.pdf \
  --export-tiff ./out/master.tiff \
  --tiff-dpi 2400
```

Key options:
- `--outer-shape PATH` SVG path for the outer constraint (supports arbitrary shapes)
- `--inner-shape PATH` SVG path(s) for inner keep‑out; repeatable
- `--orientation tangent|upright` page orientation relative to local flow
- `--gap-mm 0.5` minimum gap between pages
- `--scale-min 0.1 --scale-max 1.0` per‑page scale bounds
- `--tiff-dpi 600|1200|2400` output DPI for raster master

See all options:

```bash
python -m nanorosetta.cli compose --help
```

## How it works (MVP)
- Parses SVG outer/inner shapes as polygons.
- Computes the allowed region: outer minus inner(s) via polygon boolean ops.
- Generates a field of streamlines (offset/level sets) and places pages along paths with arc‑length spacing; avoids collisions; orients tangent or upright.
- Renders a high‑DPI raster for TIFF; writes a PDF proof.

## Roadmap
- Pure vector PDF assembly (pages as XObjects with clipping) instead of raster proof
- Conformal mapping option for ultra‑uniform spacing
- Interactive desktop UI (Tauri) and JSON sidecar with placements
