# Any‑Shape Wafer Layout (NanoRosetta‑style) – CLI + GUI

CLI/GUI tool that places large numbers of PDF pages "around" any inner shape and constrained to any outer shape. Inputs are PDF pages and SVG paths (inner keep‑outs and outer boundary). Exports a vector PDF proof and optional 1‑bit TIFF suitable for laser workflows.

Spec references: NanoRosetta's process and wafer geometry described at [nanorosetta.com/technology](https://nanorosetta.com/technology/).

## Install (for developers)

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## GUI Usage (New)

```bash
python nanoprint.py
```

- Select Input PDFs, Outer SVG, and optional Inner SVGs
- Use "Optimize for DPI" (e.g., 200 for large text docs)
- Use "Max Canvas Pixels" (e.g., 50,000,000 for big jobs)
- Clear buttons let you replace selections without restarting
- Click Run to generate outputs (PDF proof and/or TIFF)

## CLI Usage

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

### Diagnose SVGs (New)

Quickly see which shape elements your SVG contains (path/rect/circle/ellipse):

```bash
python -m nanorosetta.cli diagnose ./examples/outer_rect.svg
```

### DPI Optimization (Improved)

```bash
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 2400 \
  --export-tiff ./out/master.tiff
```

This will:
1. **Calculate page dimensions** based on the target DPI
2. **Calculate total area needed** = page_count × page_area + gaps
3. **Resize SVG shapes** to accommodate the required area
4. **Place pages optimally** within the resized SVG area difference
5. **Maintain original page aspect ratios**

### Large Document Support

For documents with many pages (e.g., 2,000 pages), use memory management:

```bash
python -m nanorosetta.cli compose \
  --input ./large_document.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 200 \
  --max-canvas-pixels 50000000 \
  --export-tiff ./out/large_output.tiff
```

**Memory Management:**
- `--max-canvas-pixels 50000000` (50M pixels) for large documents
- `--optimize-for-dpi 200` recommended for text-heavy documents
- **SVG shapes are automatically resized** to fit the calculated page area
- Prevents crashes on systems with limited RAM

**Flow for DPI Optimization:**
1. **User specifies DPI** (e.g., 200 DPI)
2. **Calculate page dimensions** based on that DPI
3. **Calculate total area needed** = page_count × page_area + gaps
4. **Resize SVG shapes** to accommodate the total area needed
5. **Fit everything** within the resized SVG area difference

### Overflow Prevention (New)

- Automatic DPI reduction if computed pixel dimensions are too large
- Conservative limits (~2^28 pixels/dimension) to avoid Pillow overflow
- Clear suggestions if saving fails (lower DPI, use Target MB, reduce canvas)

### Key Options
- `--outer-shape PATH` SVG path for the outer constraint (supports arbitrary shapes)
- `--inner-shape PATH` SVG path(s) for inner keep‑out; repeatable
- `--optimize-for-dpi DPI` Calculate optimal page sizes to fill area at this DPI
- `--max-canvas-pixels PIXELS` Maximum canvas pixels for memory management
- `--orientation tangent|upright` page orientation relative to local flow
- `--gap-mm 0.5` minimum gap between pages
- `--scale-min 0.1 --scale-max 1.0` per‑page scale bounds
- `--tiff-dpi 600|1200|2400` output DPI for raster master

See all options:

```bash
python -m nanorosetta.cli compose --help
```

## How it works (MVP)
- Parses SVG outer/inner shapes as polygons (supports path/rect/circle/ellipse)
- Computes the allowed region: outer minus inner(s) via polygon boolean ops
- Optionally calculates optimal page sizes to fill available area efficiently
- Generates a field of streamlines and places pages along paths with arc‑length spacing
- Renders a high‑DPI raster for TIFF; writes a PDF proof

## Standalone Builds
- Windows EXE, macOS App, and Linux AppImage are built via GitHub Actions
- Download artifacts from the Actions page or Releases (when enabled)

## Roadmap
- Pure vector PDF assembly (pages as XObjects with clipping)
- Conformal mapping option for ultra‑uniform spacing
