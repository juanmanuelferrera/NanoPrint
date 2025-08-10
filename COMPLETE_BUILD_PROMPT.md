# Complete NanoPrint Build Prompt

## Project Overview
Build a standalone task management application that wraps PDF pages around any arbitrary inner shape and constrained by any outer shape. The output should be suitable for nano laser printers (NanoRosetta technology) with configurable DPI and memory management for large documents.

## Core Requirements

### Primary Functionality
- **PDF Page Wrapping**: Wrap any number of PDF pages around arbitrary SVG shapes
- **Dual Shape Support**: Inner shape (keep-out area) and outer shape (constraint boundary)
- **Layout Algorithm**: Signed Distance Field (SDF) and level-set "orbits" for robust placement
- **Output Formats**: High-resolution TIFF (1-bit bilevel) and composite PDF proofs
- **Memory Management**: Handle large documents (2000+ pages) without memory overflow
- **DPI Optimization**: Calculate optimal page sizes to fill available area efficiently

### Technical Specifications
- **Target Platforms**: Windows 64-bit (.exe), macOS (.app), Linux (AppImage)
- **Standalone**: No external dependencies, works "out of the box"
- **GUI Interface**: Tkinter-based graphical user interface
- **CLI Interface**: Command-line interface for automation
- **Large Document Support**: Optimized for 2000+ page text documents at 200 DPI

## File Structure

```
mr_ha/
├── nanorosetta/
│   ├── __init__.py              # Package initialization with version
│   ├── units.py                 # Unit conversion utilities (mm to points/pixels)
│   ├── geometry.py              # SVG parsing and boolean operations
│   ├── layout.py                # Page placement algorithm with SDF
│   ├── render.py                # PDF/TIFF rendering and export
│   ├── cli.py                   # Command-line interface
│   └── gui.py                   # Tkinter GUI interface
├── nanoprint.py                 # Main launcher (CLI/GUI dispatcher)
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Project metadata
├── README.md                   # Documentation
├── examples/                   # Sample files
│   ├── sample.pdf              # Placeholder PDF
│   ├── outer_rect.svg          # Rectangular outer shape
│   └── inner_circle.svg        # Circular inner shape
├── packaging/                  # Build specifications
│   └── specs/
│       ├── nanorosetta_macos_app.spec
│       └── nanorosetta_windows_onefile.spec
├── .github/workflows/          # CI/CD automation
│   ├── windows-build.yml       # Windows EXE build
│   └── linux-appimage.yml      # Linux AppImage build
└── test scripts
    ├── test_dpi_optimization.sh
    └── test_large_document.sh
```

## Dependencies (requirements.txt)

```txt
pymupdf>=1.23.8
Pillow>=10.2.0
numpy==1.26.4
shapely==2.0.1
svgpathtools>=1.6.1
scipy>=1.11.0
svgwrite>=1.4.3
```

**Critical**: Use exact versions for numpy and shapely to prevent Windows EXE crashes.

## Core Implementation

### 1. Geometry Module (nanorosetta/geometry.py)

```python
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from svgpathtools import svg2paths2

def parse_svg_path(svg_path: str) -> MultiPolygon:
    """Parse SVG file and convert to Shapely MultiPolygon."""
    paths, attributes, svg_attributes = svg2paths2(svg_path)
    
    polygons = []
    for path in paths:
        coords = []
        for segment in path:
            if hasattr(segment, 'start'):
                coords.append((segment.start.real, segment.start.imag))
            if hasattr(segment, 'end'):
                coords.append((segment.end.real, segment.end.imag))
        
        if len(coords) >= 3:
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            polygon = Polygon(coords)
            if polygon.is_valid:
                polygons.append(polygon)
    
    if not polygons:
        raise ValueError(f"No valid polygons found in {svg_path}")
    
    return MultiPolygon(polygons)

def boolean_allowed_region(outer: MultiPolygon, inners: List[MultiPolygon]) -> MultiPolygon:
    """Create allowed region by subtracting inner shapes from outer shape."""
    # Validation checks for shape relationships
    # Returns MultiPolygon of allowed placement area
```

### 2. Layout Module (nanorosetta/layout.py)

```python
from dataclasses import dataclass
from typing import List, Literal
import math

Orientation = Literal["tangent", "upright"]

class PageSpec:
    def __init__(self, width_mm: float, height_mm: float):
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.aspect_ratio = width_mm / height_mm

class Placement:
    def __init__(self, page_index: int, x_mm: float, y_mm: float, 
                 scale: float, rotation_deg: float):
        self.page_index = page_index
        self.x_mm = x_mm
        self.y_mm = y_mm
        self.scale = scale
        self.rotation_deg = rotation_deg

def calculate_safe_page_dimensions(
    page_count: int,
    target_dpi: int,
    max_canvas_pixels: int = 100_000_000,
    min_page_height_mm: float = 1.0,
    max_page_height_mm: float = 50.0,
) -> float:
    """Calculate safe page dimensions for large document counts."""
    # Memory management for 2000+ page documents
    estimated_canvas_side_pixels = math.sqrt(max_canvas_pixels)
    canvas_side_mm = estimated_canvas_side_pixels / (target_dpi / 25.4)
    avg_aspect_ratio = 1.4
    
    estimated_pages_per_row = math.sqrt(page_count * avg_aspect_ratio)
    estimated_rows = page_count / estimated_pages_per_row
    
    if estimated_pages_per_row > 0 and estimated_rows > 0:
        page_height_mm = min(
            canvas_side_mm / estimated_rows,
            canvas_side_mm / (estimated_pages_per_row * avg_aspect_ratio)
        )
    else:
        page_height_mm = math.sqrt(canvas_side_mm * canvas_side_mm / page_count / avg_aspect_ratio)
    
    return max(min_page_height_mm, min(max_page_height_mm, page_height_mm))

def calculate_optimal_page_size(
    allowed_region_mm: MultiPolygon,
    pages: List[PageSpec],
    dpi: int,
    gap_mm: float = 0.5,
    min_page_height_mm: float = 1.0,
    max_page_height_mm: float = 50.0,
    max_canvas_pixels: int = 100_000_000,
) -> float:
    """Calculate optimal page height to efficiently fill the available area."""
    if not pages or allowed_region_mm.is_empty:
        return min_page_height_mm
    
    # For large page counts, use safe calculation
    if len(pages) > 500:
        return calculate_safe_page_dimensions(
            len(pages), dpi, max_canvas_pixels, min_page_height_mm, max_page_height_mm
        )
    
    # Calculate optimal size for smaller documents
    total_area_mm2 = allowed_region_mm.area
    total_aspect_ratio = sum(p.aspect_ratio for p in pages)
    avg_aspect_ratio = total_aspect_ratio / len(pages)
    
    estimated_pages_per_row = math.sqrt(len(pages) * avg_aspect_ratio)
    estimated_rows = len(pages) / estimated_pages_per_row
    
    if estimated_pages_per_row > 0 and estimated_rows > 0:
        optimal_height = math.sqrt(total_area_mm2 / (estimated_rows * estimated_pages_per_row * avg_aspect_ratio))
    else:
        optimal_height = math.sqrt(total_area_mm2 / len(pages))
    
    return max(min_page_height_mm, min(max_page_height_mm, optimal_height))

def plan_layout_any_shape(
    pages: List[PageSpec],
    allowed_region_mm: MultiPolygon,
    nominal_height_mm: float,
    gap_mm: float = 0.5,
    orientation: Orientation = "tangent",
    scale_min: float = 0.1,
    scale_max: float = 1.0,
    streamline_step_mm: float = 2.0,
    max_streamlines: int = 200,
    optimize_for_dpi: int = None,
    max_canvas_pixels: int = 100_000_000,
) -> List[Placement]:
    """Generate page placements using SDF and streamline algorithm."""
    # Implementation of SDF-based layout algorithm
    # Returns list of Placement objects with optimal positions
```

### 3. Render Module (nanorosetta/render.py)

```python
import fitz
from PIL import Image
import numpy as np

def compose_raster_any_shape(
    placements: List[Placement],
    doc_registry: List[fitz.Document],
    dpi: int,
    canvas_width_mm: float,
    canvas_height_mm: float,
    origin_center: bool = True,
    background: int = 255,
) -> Image.Image:
    """Render placements to high-resolution TIFF."""
    canvas_w_px = mm_to_px(canvas_width_mm, dpi)
    canvas_h_px = mm_to_px(canvas_height_mm, dpi)
    
    # Check for dimension overflow (PIL typically has limits around 2^31-1 pixels)
    max_dimension = 2**30  # Conservative limit
    if canvas_w_px > max_dimension or canvas_h_px > max_dimension:
        raise ValueError(f"code=5: image dimensions might overflow (width={canvas_w_px}, height={canvas_h_px} pixels). Try reducing DPI or canvas size.")
    
    base = Image.new("L", (canvas_w_px, canvas_h_px), color=background)
    
    # Render each placement
    for placement in placements:
        # Implementation of page rendering with transforms
        pass
    
    return base

def compute_dpi_for_target_mb(width_mm: float, height_mm: float, target_mb: float, bits_per_pixel: int = 1) -> int:
    """Calculate DPI needed to achieve target file size."""
    # Formula: DPI = sqrt((target_mb * 8 * 1024 * 1024) / (width_mm * height_mm * bits_per_pixel * (25.4^2)))
    numerator = target_mb * 8 * 1024 * 1024
    denominator = width_mm * height_mm * bits_per_pixel * (25.4 ** 2)
    dpi = math.sqrt(numerator / denominator)
    
    # Limit DPI to prevent dimension overflow
    max_dpi = 10000  # Conservative limit to prevent overflow
    dpi = min(dpi, max_dpi)
    
    return int(max(1, round(dpi)))
```

### 4. CLI Module (nanorosetta/cli.py)

```python
import argparse
from pathlib import Path

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NanoPrint - PDF Layout Tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    c = subparsers.add_parser("compose", help="Compose PDF pages into layout")
    
    # Input/output
    c.add_argument("--input", type=Path, required=True, help="Input PDF file")
    c.add_argument("--output", type=Path, help="Output PDF file")
    c.add_argument("--export-tiff", type=Path, help="Export as TIFF file")
    
    # Shapes
    c.add_argument("--outer-shape", type=Path, required=True, help="Outer constraint SVG")
    c.add_argument("--inner-shape", type=Path, action="append", help="Inner keep-out SVG(s)")
    
    # Layout parameters
    c.add_argument("--nominal-height-mm", type=float, default=10.0)
    c.add_argument("--gap-mm", type=float, default=0.5)
    c.add_argument("--orientation", choices=["tangent", "upright"], default="tangent")
    c.add_argument("--scale-min", type=float, default=0.1)
    c.add_argument("--scale-max", type=float, default=1.0)
    c.add_argument("--streamline-step-mm", type=float, default=2.0)
    c.add_argument("--max-streamlines", type=int, default=200)
    c.add_argument("--optimize-for-dpi", type=int, help="Calculate optimal page size to fill area at this DPI")
    c.add_argument("--max-canvas-pixels", type=int, default=100_000_000, help="Maximum canvas pixels for memory management")
    
    # Canvas controls
    c.add_argument("--canvas-margin-mm", type=float, default=5.0)
    c.add_argument("--canvas-bin-mm", type=float, help="Round canvas dimensions to multiples of this value")
    
    # Output controls
    c.add_argument("--tiff-dpi", type=int, default=1200)
    c.add_argument("--target-mb", type=float, help="Target TIFF file size in MB")
    c.add_argument("--tiff-mode", choices=["bilevel", "gray"], default="bilevel")
    c.add_argument("--tiff-compression", choices=["lzw", "deflate", "none"], default="lzw")
    
    return parser
```

### 5. GUI Module (nanorosetta/gui.py)

```python
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

class NanoPrintGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        
        self.title("NanoPrint - PDF Layout Tool")
        self.geometry("600x800")
        
        # Variables
        self.input_file_var = tk.StringVar()
        self.output_file_var = tk.StringVar()
        self.tiff_file_var = tk.StringVar()
        self.outer_shape_var = tk.StringVar()
        self.inner_shape_var = tk.StringVar()
        self.nominal_height_var = tk.DoubleVar(value=10.0)
        self.gap_var = tk.DoubleVar(value=0.5)
        self.orientation_var = tk.StringVar(value="tangent")
        self.tiff_dpi_var = tk.IntVar(value=1200)
        self.optimize_dpi_var = tk.IntVar(value=0)
        self.max_canvas_pixels_var = tk.IntVar(value=100_000_000)
        
        self._build_widgets()
    
    def _build_widgets(self) -> None:
        # Implementation of Tkinter GUI with all controls
        # File selection, parameter inputs, and run button
        pass
    
    def _run(self) -> None:
        # Execute the layout process using CLI functions
        # Show progress and handle errors
        pass
```

### 6. Main Launcher (nanoprint.py)

```python
#!/usr/bin/env python3
"""NanoPrint - Main launcher for CLI and GUI modes."""

import sys
from nanorosetta.cli import main as cli_main
from nanorosetta.gui import NanoPrintGUI

def main():
    if len(sys.argv) > 1:
        # CLI mode
        cli_main()
    else:
        # GUI mode
        app = NanoPrintGUI()
        app.mainloop()

if __name__ == "__main__":
    main()
```

## Build Process

### 1. Windows EXE Build (GitHub Actions)

```yaml
# .github/workflows/windows-build.yml
name: Build Windows EXE

on:
  workflow_dispatch:
  push:
    branches: [main]

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python 3.11
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        architecture: 'x64'
    
    - name: Install dependencies
      run: |
        python -m pip install -U pip
        pip install -r requirements.txt
        pip install "numpy==1.26.4" "shapely==2.0.1" --upgrade
        pip install pyinstaller==6.6.0
    
    - name: Build GUI EXE
      run: |
        pyinstaller --windowed --onefile --name NanoPrint --collect-all numpy --collect-all shapely nanoprint.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: NanoPrint-windows-exe
        path: dist/NanoPrint.exe
```

### 2. Local Build Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install pyinstaller==6.6.0

# Build Windows EXE
pyinstaller --windowed --onefile --name NanoPrint --collect-all numpy --collect-all shapely nanoprint.py

# Build macOS App
pyinstaller --windowed --name NanoPrint nanoprint.py

# Build Linux AppImage
pyinstaller --windowed --onefile nanoprint.py
```

## Key Features Implementation

### 1. DPI Optimization
- Calculate optimal page sizes based on available area
- Minimize blank spaces by scaling pages appropriately
- Maintain original page aspect ratios
- Support for user-specified target DPI (e.g., 200 DPI for text)

### 2. Large Document Support
- Memory management for 2000+ page documents
- Automatic page scaling for large document counts
- Configurable canvas pixel limits
- Optimized for text documents at 200 DPI

### 3. Shape Flexibility
- Support for any SVG shapes (inner and outer)
- Boolean operations for complex layouts
- Validation of shape relationships
- Error handling for invalid geometries

### 4. Output Formats
- High-resolution TIFF (1-bit bilevel for laser printers)
- Composite PDF proofs (vector)
- Configurable compression and bit depth
- Target file size calculation

## Usage Examples

### CLI Usage
```bash
# Basic usage with DPI optimization
python -m nanorosetta.cli compose \
  --input ./document.pdf \
  --outer-shape ./outer_rect.svg \
  --inner-shape ./inner_circle.svg \
  --optimize-for-dpi 200 \
  --max-canvas-pixels 50000000 \
  --export-tiff ./output.tiff

# Large document (2000+ pages)
python -m nanorosetta.cli compose \
  --input ./large_document.pdf \
  --outer-shape ./outer_rect.svg \
  --inner-shape ./inner_circle.svg \
  --optimize-for-dpi 200 \
  --max-canvas-pixels 50000000 \
  --export-tiff ./large_output.tiff
```

### GUI Usage
1. Run `python nanoprint.py` (no arguments)
2. Select input PDF and SVG shapes
3. Set DPI optimization (e.g., 200 for large docs)
4. Set max canvas pixels (e.g., 50000000 for large docs)
5. Click "Run" to generate layout

## Testing

### Test Scripts
```bash
# Test DPI optimization
./test_dpi_optimization.sh

# Test large document handling
./test_large_document.sh
```

### Sample Files
- `examples/sample.pdf` - Placeholder PDF
- `examples/outer_rect.svg` - Rectangular outer shape
- `examples/inner_circle.svg` - Circular inner shape

## Critical Notes

1. **Dependency Versions**: Use exact numpy==1.26.4 and shapely==2.0.1 to prevent Windows EXE crashes
2. **Memory Management**: Large documents require max_canvas_pixels parameter
3. **DPI Limits**: Maximum 10,000 DPI to prevent dimension overflow
4. **Shape Validation**: Inner shapes must be smaller than outer shapes
5. **PyInstaller**: Use --collect-all for numpy and shapely to ensure proper bundling

## Expected Output

The final standalone EXE will:
- Work without Python installation
- Include GUI and CLI interfaces
- Handle 2000+ page documents efficiently
- Support any SVG shapes
- Generate high-resolution TIFF output
- Optimize page sizes for target DPI
- Prevent memory overflow with large documents

This complete prompt contains all necessary information to rebuild the exact NanoPrint standalone EXE from scratch.
