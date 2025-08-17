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

- Select Input PDFs, Outer SVG, and optional Inner SVGs (inner shapes are optional)
- Use "Optimize for DPI" (e.g., 200 for large text docs)
- Use "Max Canvas Pixels" (e.g., 50,000,000 for big jobs)
- Clear buttons let you replace selections without restarting
- Click Run to generate outputs (PDF proof and/or TIFF)

**Recent Improvements:**
- **TIFF DPI Metadata Fix**: TIFF files now correctly use actual rendering DPI instead of hardcoded 200 DPI
- **Optimized Packing Algorithms**: Advanced shape-aware packing for maximum space utilization
- **Inner Shape Intelligence**: Analyzes inner shape constraints for optimal placement strategies
- **Pixel-First Layout**: Direct pixel calculations for consistent quality without DPI dependencies
- **Adaptive Sizing**: Automatically adjusts page sizes to achieve target space utilization
- **Smart Canvas Sizing**: Automatically fits canvas to content instead of using raw SVG coordinates
- **Grid Layout**: Pages arranged left-to-right, top-to-bottom in clean rows (not curved streamlines)
- **Single Page Optimization**: Conservative sizing for 1-page layouts prevents memory overflow
- **Enhanced Logging**: Comprehensive debug information for troubleshooting layout decisions

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

### Advanced Packing & Layout (New)

#### Optimized Packing for Maximum Space Utilization
```bash
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --use-optimized-packing \
  --packing-flexibility 0.15 \
  --export-tiff ./out/master.tiff
```

#### Adaptive Sizing with Target Fill Ratio
```bash
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --adaptive-sizing \
  --target-fill-ratio 0.90 \
  --export-tiff ./out/master.tiff
```

#### Pixel-First Layout for Consistent Quality
```bash
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --pixel-first \
  --standard-page-width-px 1700 \
  --standard-page-height-px 2200 \
  --export-tiff ./out/master.tiff
```

#### Inner Shape Positioning (9 Options)
```bash
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --inner-position top-left \
  --use-optimized-packing \
  --export-tiff ./out/master.tiff
```

**Available inner positions:** center, top-left, top-center, top-right, middle-left, middle-right, bottom-left, bottom-center, bottom-right

**Inner Shape Positioning Logic:**
- **Default**: Inner shapes are placed at their original SVG coordinates (typically center)
- **With --inner-position**: Inner shapes are automatically repositioned relative to the outer shape bounds
- **After scaling**: Inner shapes maintain their relative position even when SVG shapes are auto-scaled
- **Multiple inner shapes**: Each inner shape can have the same relative positioning applied
- **Coordinates**: Positioning uses the outer shape's bounding box as reference, not the original SVG coordinate system

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

For documents with many pages (e.g., 1,034+ pages), use optimized packing:

```bash
python -m nanorosetta.cli compose \
  --input ./large_document.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --use-optimized-packing \
  --adaptive-sizing \
  --target-fill-ratio 0.85 \
  --max-canvas-pixels 200000000 \
  --export-tiff ./out/large_output.tiff
```

**Large Document Strategies:**
- `--use-optimized-packing` for maximum space efficiency
- `--adaptive-sizing` automatically adjusts page sizes for best fit
- `--max-canvas-pixels 200000000` (200M pixels) for very large layouts
- `--pixel-first` for consistent quality at scale
- **Intelligent shape analysis** adapts packing strategy to SVG geometry
- **Inner shape awareness** optimizes placement around constraints

**Flow for DPI Optimization:**
1. **User specifies target DPI** (e.g., 200 DPI for final output quality)
2. **Calculate pixel area needed** = page_count × page_area_at_target_dpi + gaps
3. **Measure current SVG area** (outer shape minus inner shapes)
4. **Auto-scale SVG shapes** by factor = √(needed_area / current_area)
5. **Place pages optimally** in the scaled SVG area at target DPI
6. **Prevents dimension overflow** by ensuring realistic canvas sizes

### Overflow Prevention & Debugging (New)

- Automatic DPI reduction if computed pixel dimensions are too large
- Conservative limits (~2^28 pixels/dimension) to avoid Pillow overflow
- **Comprehensive logging** - Creates `nanorosetta_debug.log` with detailed execution info
- Clear suggestions if saving fails (lower DPI, use Target MB, reduce canvas)
- **Enhanced error handling** with specific guidance for dimension overflow issues

**Debug Log Features:**
- Timestamped execution tracking
- Canvas dimension calculations and pixel counts
- DPI adjustments and safety validations
- Layout planning progress and placement counts
- Full error context with stack traces

### Key Options

#### Traditional Layout
- `--outer-shape PATH` SVG path for the outer constraint (supports arbitrary shapes)
- `--inner-shape PATH` SVG path(s) for inner keep‑out; repeatable
- `--inner-position POSITION` Position inner shape: center (default), top-left, top-center, top-right, middle-left, middle-right, bottom-left, bottom-center, bottom-right
- `--optimize-for-dpi DPI` **Auto-scale SVG shapes** to fit all pages at target DPI (recommended for dimension overflow)
- `--max-canvas-pixels PIXELS` Maximum canvas pixels for memory management
- `--orientation tangent|upright` page orientation relative to local flow
- `--gap-mm 0.5` minimum gap between pages
- `--scale-min 0.1 --scale-max 1.0` per‑page scale bounds
- `--tiff-dpi 600|1200|2400` output DPI for raster master

#### Advanced Packing Options
- `--use-optimized-packing` Enable shape-aware packing algorithms for better space utilization
- `--adaptive-sizing` Automatically adjust page sizes to achieve target fill ratio
- `--packing-flexibility 0.1` Allow page size variation for better packing (0.0-1.0)
- `--target-fill-ratio 0.85` Target space utilization ratio for adaptive sizing

#### Pixel-First Layout
- `--pixel-first` Use pixel-first layout approach (calculates exact canvas size needed)
- `--standard-page-width-px 1700` Standard page width in pixels
- `--standard-page-height-px 2200` Standard page height in pixels
- `--gap-px 50` Gap between pages in pixels

See all options:

```bash
python -m nanorosetta.cli compose --help
```

## Troubleshooting

### Error Code 5: Image Dimensions Overflow (RESOLVED)

**Status: Fixed in latest version**
- ✅ Automatic canvas sizing prevents oversized outputs
- ✅ PDF proof downsampling eliminates PyMuPDF overflow
- ✅ Single page conservative sizing avoids memory issues
- ✅ Content-based canvas fits actual page layout
- ✅ TIFF DPI metadata now correctly matches rendering DPI

**If you still encounter issues:**
```bash
# Use --optimize-for-dpi to auto-scale SVG shapes
python -m nanorosetta.cli compose \
  --input your.pdf \
  --outer-shape outer.svg \
  --optimize-for-dpi 200 \
  --export-tiff output.tiff
```

**Alternative Solutions:**
- Reduce DPI: `--tiff-dpi 600` (instead of 1200)
- Target file size: `--target-mb 50` (auto-calculates safe DPI)
- Reduce canvas: `--canvas-margin-mm 2.0` (instead of 5.0)

**Debug Information:**
- Check `nanorosetta_debug.log` for detailed execution info
- Shows canvas dimensions, pixel counts, and where execution fails

## Latest Features & Fixes

### TIFF DPI Metadata Fix (Latest)
- **Correct DPI Metadata**: TIFF files now save with actual rendering DPI instead of hardcoded 200 DPI
- **Proper Display Scaling**: Image viewers now display TIFF files at correct physical sizes
- **CLI & GUI Fixed**: Both command-line and graphical interfaces properly pass DPI to TIFF save functions
- **Resolution Accuracy**: TIFF metadata now accurately reflects the rendering resolution used

### Advanced Packing Engine (New)
- **Shape-Aware Packing**: Analyzes SVG geometry (rectangular, square, elongated, complex) and adapts packing strategy accordingly
- **Inner Shape Intelligence**: Detects central, offset, or distributed inner shapes and optimizes placement strategies
- **Adaptive Sizing**: Automatically adjusts page sizes to achieve target space utilization (default 85%)
- **Size Flexibility**: Allows controlled page size variation (default 10%) for better packing efficiency
- **Collision Detection**: Prevents page overlap while maintaining minimum gaps
- **Utilization Metrics**: Reports space efficiency and placement success rates

### Inner Shape Positioning System (New)
- **9 Position Options**: Place inner shapes at center (default), corners, or edges relative to outer shape
- **Automatic Repositioning**: Inner shapes maintain relative position even after SVG scaling
- **Constraint Analysis**: System analyzes inner shape size and position to optimize packing approach
- **Multi-Shape Support**: Handle multiple inner shapes with different positioning strategies

### Pixel-First Layout (New)
- **Direct Pixel Calculations**: Calculate exact canvas size needed without DPI dependencies
- **Aspect Ratio Preservation**: Ensures square SVGs produce square canvases by adjusting grid ratios
- **Accurate DPI Metadata**: TIFF files now use actual rendering DPI for correct physical dimensions
- **Large Layout Support**: Handles 1000+ pages efficiently with optimized pixel calculations

### Smart Layout Engine
- **Rectangular Grid Layout**: Pages arrange in clean left-to-right, top-to-bottom rows
- **Content-Based Canvas**: Canvas automatically sizes to fit actual page layout
- **SVG Coordinate Scaling**: Intelligent handling of different SVG coordinate systems
- **Packing Analysis**: Real-time efficiency metrics show how well pages fill available space

### Memory & Performance
- **PDF Sampling**: 200 DPI sampling with high-quality scaling prevents memory overflow
- **Automatic DPI Reduction**: Built-in safeguards against excessive pixel dimensions
- **PyMuPDF Protection**: PDF proof downsampling eliminates image insertion limits
- **Single Page Optimization**: Conservative sizing for small layouts

### User Experience
- **Comprehensive Logging**: Full debug trace of layout decisions and render pipeline
- **Error Detection**: Special handling for dimension overflow with helpful suggestions
- **Flexible SVG Support**: Works with or without inner shapes, any coordinate scale
- **Grid Size Reporting**: Shows calculated rows/columns and spacing information
- Contains DPI calculations and safety validations

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
