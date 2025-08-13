from __future__ import annotations

import argparse
import os
import math
import logging
import sys
from typing import List, Tuple

import fitz  # PyMuPDF
from shapely.geometry import MultiPolygon

from .geometry import boolean_allowed_region, parse_svg_path, parse_combined_svg, position_inner_shape_relative
from .pixel_layout import calculate_required_region_size_pixels, calculate_svg_scale_factor, calculate_pixel_layout
from .layout import PageSpec, plan_layout_any_shape, calculate_optimal_page_size
from .optimized_packing import optimized_packing_layout, hybrid_packing_layout, adaptive_size_packing
from .render import (
    compose_raster_any_shape,
    save_pdf_proof,
    save_tiff_1bit,
    save_tiff_gray,
    compute_dpi_for_target_mb,
    validate_canvas_dimensions,
)


def _setup_logging() -> None:
    """Setup logging to both file and console."""
    log_file = "nanorosetta_debug.log"
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler - detailed logs
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler - important messages only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info(f"Logging initialized. Debug log: {log_file}")


def _collect_pages(input_paths: List[str]) -> Tuple[List[fitz.Document], List[PageSpec]]:
    docs: List[fitz.Document] = []
    pages: List[PageSpec] = []
    for doc_idx, p in enumerate(input_paths):
        d = fitz.open(p)
        docs.append(d)
        for i in range(d.page_count):
            r = d.load_page(i).rect
            pages.append(PageSpec(doc_index=doc_idx, page_index=i, width_pt=r.width, height_pt=r.height))
    return docs, pages


def cli_diagnose(args: argparse.Namespace) -> int:
    """Diagnose an SVG file and show its contents."""
    from .geometry import diagnose_svg_file
    
    try:
        info = diagnose_svg_file(args.svg_file)
        print(info)
        
        # Also show automatic shape detection results
        print("\n" + "="*50)
        print("AUTOMATIC SHAPE DETECTION ANALYSIS")
        print("="*50)
        
        try:
            outer, inners = parse_combined_svg(args.svg_file)
            print(f"✅ Auto-detection successful:")
            print(f"   Outer shape: {outer.area:.2f} area, bounds {outer.bounds}")
            print(f"   Inner shapes: {len(inners)}")
            for i, inner in enumerate(inners):
                ratio = inner.area / outer.area
                print(f"   - Inner {i+1}: {inner.area:.2f} area ({ratio:.1%} of outer), bounds {inner.bounds}")
            
            if len(inners) == 0:
                print("   Note: No inner shapes detected (all shapes below 1% area threshold)")
                print("   Use --min-inner-area-ratio to adjust detection sensitivity")
        except Exception as detect_error:
            print(f"❌ Auto-detection failed: {detect_error}")
        
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cli_compose(args: argparse.Namespace) -> int:
    """Compose PDF pages around any inner shape constrained to any outer shape."""
    
    logging.info("Starting compose operation")
    logging.debug(f"Args: {vars(args)}")
    
    # Load PDF pages
    try:
        logging.info(f"Loading PDF pages from: {args.input}")
        docs, pages = _collect_pages(args.input)
        logging.info(f"Loaded {len(pages)} pages from {len(docs)} documents")
    except Exception as e:
        logging.error(f"Error opening input PDF(s): {e}")
        print(f"Error opening input PDF(s): {e}")
        return 5
    if not pages:
        logging.error("No pages found in input PDFs")
        print("No pages found in input PDFs")
        return 1
    
    # Load SVG shapes - support both combined and separate files
    try:
        if args.auto_detect_inner:
            # Use automatic shape detection from single SVG file
            logging.info(f"Auto-detecting shapes in: {args.outer_shape}")
            outer, inners = parse_combined_svg(args.outer_shape, args.min_inner_area_ratio)
            logging.info(f"Auto-detected: 1 outer shape, {len(inners)} inner shapes")
            
            # Apply relative positioning to auto-detected inner shapes
            if args.inner_position != "center" and inners:
                logging.info(f"Repositioning {len(inners)} auto-detected inner shapes to: {args.inner_position}")
                inners = [position_inner_shape_relative(inner, outer, args.inner_position) for inner in inners]
        else:
            # Traditional separate file approach
            logging.info(f"Parsing outer shape: {args.outer_shape}")
            outer = parse_svg_path(args.outer_shape)
            logging.debug(f"Outer shape bounds: {outer.bounds}")
            
            inners = []
            if args.inner_shape:
                logging.info(f"Parsing {len(args.inner_shape)} inner shape(s)")
                for inner_path in args.inner_shape:
                    inner = parse_svg_path(inner_path)
                    # Apply relative positioning
                    if args.inner_position != "center":
                        logging.info(f"Positioning inner shape at: {args.inner_position}")
                        inner = position_inner_shape_relative(inner, outer, args.inner_position)
                    inners.append(inner)
                    logging.debug(f"Inner shape bounds: {inner.bounds}")
    except Exception as e:
        logging.error(f"Error parsing SVG shapes: {e}")
        print(f"Error parsing SVG shapes: {e}")
        return 5
    
    # Choose layout approach: pixel-first or traditional
    if args.pixel_first:
        logging.info("Using pixel-first layout approach")
        
        # Detect SVG aspect ratio to determine target canvas aspect ratio
        outer_bounds = outer.bounds
        current_width_mm = outer_bounds[2] - outer_bounds[0]
        current_height_mm = outer_bounds[3] - outer_bounds[1]
        svg_aspect_ratio = current_width_mm / current_height_mm
        
        logging.info(f"SVG aspect ratio: {svg_aspect_ratio:.3f} (1.0 = square)")
        
        # Calculate exact pixel dimensions needed
        required_width_px, required_height_px = calculate_required_region_size_pixels(
            len(pages),
            args.standard_page_width_px, 
            args.standard_page_height_px,
            args.gap_px,
            target_aspect_ratio=svg_aspect_ratio
        )
        
        # Calculate SVG scale factor (reuse dimensions from above)
        
        scale_factor = calculate_svg_scale_factor(
            current_width_mm, current_height_mm,
            required_width_px, required_height_px
        )
        
        print(f"Pixel-first scaling: {scale_factor:.4f}x to create {required_width_px:,}×{required_height_px:,} pixel canvas")
        print(f"This will fit all {len(pages)} pages at {args.standard_page_width_px}×{args.standard_page_height_px} pixels each")
        
        # Apply scaling to SVG shapes
        from shapely.affinity import scale
        outer = scale(outer, scale_factor, scale_factor)
        inners = [scale(inner, scale_factor, scale_factor) for inner in inners]
        
        # Reapply relative positioning after scaling
        if args.inner_shape and args.inner_position != "center":
            logging.info(f"Reapplying inner positioning after pixel-first scaling: {args.inner_position}")
            inners = [position_inner_shape_relative(inner, outer, args.inner_position) for inner in inners]
        
        # Use pixel layout
        allowed_region = boolean_allowed_region(outer, inners)
        placements = calculate_pixel_layout(
            pages, 
            allowed_region.bounds,
            args.standard_page_width_px,
            args.standard_page_height_px, 
            args.gap_px
        )
        
    else:
        # Traditional approach or optimized packing
        if args.use_optimized_packing or args.adaptive_sizing:
            logging.info("Using optimized packing approach")
            
            # Calculate allowed region first
            allowed_region = boolean_allowed_region(outer, inners)
            
            if args.adaptive_sizing:
                # Use adaptive sizing to optimize page sizes
                logging.info(f"Using adaptive sizing with target fill ratio: {args.target_fill_ratio:.1%}")
                placements = adaptive_size_packing(
                    pages, allowed_region, args.target_fill_ratio, args.gap_mm
                )
            else:
                # Use optimized packing with specified parameters
                placements = optimized_packing_layout(
                    pages, allowed_region, args.nominal_height_mm, args.gap_mm,
                    size_flexibility=args.packing_flexibility,
                    prioritize_space_filling=True,
                    outer_shape=outer,
                    inner_shapes=inners
                )
        else:
            logging.info("Using traditional layout approach")
        
            # Calculate page dimensions based on DPI optimization if requested
            page_height_mm = args.nominal_height_mm
            logging.info(f"Initial page height: {page_height_mm}mm")
        
            if args.optimize_for_dpi is not None:
                logging.info(f"DPI optimization requested for target DPI: {args.optimize_for_dpi}")
                # For DPI optimization, we need to calculate the required SVG scale
                # based on the page dimensions and count
                
                # First, calculate what page height we need for the target DPI
                # This is a simplified calculation - we'll refine it
                target_dpi = args.optimize_for_dpi
                
                # Calculate total area needed for all pages
                total_page_area_mm2 = 0
                for page in pages:
                    # Estimate page width based on aspect ratio
                    page_width_mm = page.aspect_ratio * page_height_mm
                    page_area_mm2 = page_width_mm * page_height_mm
                    total_page_area_mm2 += page_area_mm2
                
                # Add gap area
                page_count = len(pages)
                estimated_pages_per_row = math.sqrt(page_count)
                estimated_rows = page_count / estimated_pages_per_row
                
                avg_page_width_mm = sum(p.aspect_ratio for p in pages) / len(pages) * page_height_mm
                gap_area_mm2 = (estimated_pages_per_row - 1) * estimated_rows * avg_page_width_mm * args.gap_mm
                gap_area_mm2 += (estimated_rows - 1) * estimated_pages_per_row * page_height_mm * args.gap_mm
                
                total_needed_area_mm2 = total_page_area_mm2 + gap_area_mm2
                
                # Calculate current SVG area difference
                logging.debug("Calculating boolean allowed region from shapes")
                allowed_region = boolean_allowed_region(outer, inners)
                current_svg_area_mm2 = allowed_region.area
                logging.info(f"Current SVG area: {current_svg_area_mm2:.2f} mm²")
                logging.info(f"Total needed area: {total_needed_area_mm2:.2f} mm²")
                
                # Calculate required scale factor for SVG shapes
                if current_svg_area_mm2 > 0:
                    # Add extra area buffer for large page counts to ensure all pages fit
                    if page_count > 1000:
                        area_buffer = 1.3  # 30% extra area for packing inefficiencies
                    elif page_count > 500:
                        area_buffer = 1.2  # 20% extra area
                    else:
                        area_buffer = 1.1  # 10% extra area
                    
                    required_scale = math.sqrt((total_needed_area_mm2 * area_buffer) / current_svg_area_mm2)
                    logging.info(f"Required scale factor: {required_scale:.4f} (includes {area_buffer:.1f}x buffer for {page_count} pages)")
                    logging.info(f"Original SVG bounds: {outer.bounds}")
                    logging.info(f"Scaling SVG shapes by {required_scale:.4f}x to fit {page_count} pages")
                    print(f"Auto-scaling SVG shapes by {required_scale:.4f}x to fit {page_count} pages (with packing buffer)")
                else:
                    required_scale = 1.0
                    logging.warning("Current SVG area is 0, using scale factor 1.0")
                
                # Apply scale to SVG shapes
                from shapely.affinity import scale
                outer = scale(outer, required_scale, required_scale)
                inners = [scale(inner, required_scale, required_scale) for inner in inners]
                
                # Reapply relative positioning after scaling (scaling can change positions)
                if args.inner_shape and args.inner_position != "center":
                    logging.info(f"Reapplying inner positioning after scaling: {args.inner_position}")
                    inners = [position_inner_shape_relative(inner, outer, args.inner_position) for inner in inners]
                
                logging.info(f"Scaled SVG bounds: {outer.bounds}")
                scaled_width = outer.bounds[2] - outer.bounds[0] 
                scaled_height = outer.bounds[3] - outer.bounds[1]
                print(f"Scaled SVG dimensions: {scaled_width:.1f} x {scaled_height:.1f} mm")
                print(f"Tip: To avoid auto-scaling, manually scale your SVG by {required_scale:.4f}x")
                
                # Recalculate allowed region with scaled shapes
                allowed_region = boolean_allowed_region(outer, inners)
                
                # Now calculate optimal page size for the scaled region
                page_height_mm = calculate_optimal_page_size(
                    allowed_region, pages, target_dpi, args.gap_mm,
                    min_page_height_mm=1.0, max_page_height_mm=50.0, max_canvas_pixels=args.max_canvas_pixels
                )
        
            # Create allowed region (if not already done in DPI optimization)
            if args.optimize_for_dpi is None:
                allowed_region = boolean_allowed_region(outer, inners)
            
            # Plan layout
            placements = plan_layout_any_shape(
                pages=pages,
                allowed_region_mm=allowed_region,
                nominal_height_mm=page_height_mm,
                gap_mm=args.gap_mm,
                orientation=args.orientation,
                scale_min=args.scale_min,
                scale_max=args.scale_max,
                streamline_step_mm=args.streamline_step_mm,
                max_streamlines=args.max_streamlines,
                optimize_for_dpi=None,  # Already handled above
                max_canvas_pixels=args.max_canvas_pixels,
            )
    
    # Layout planning complete (done in both approaches above)
    try:
        
        logging.info(f"Generated {len(placements)} placements")
    except Exception as e:
        logging.error(f"Error during layout planning: {e}")
        print(f"Error during layout planning: {e}")
        return 4

    if not placements:
        logging.error("No placements computed with current parameters")
        print("No placements computed with current parameters.")
        return 4

    # Canvas from outer bounds
    minx, miny, maxx, maxy = allowed_region.bounds
    width_mm = (maxx - minx) + 2 * args.canvas_margin_mm
    height_mm = (maxy - miny) + 2 * args.canvas_margin_mm
    logging.info(f"Canvas dimensions before rounding: {width_mm:.2f} x {height_mm:.2f} mm")

    # Optional rounding to bin
    if args.canvas_bin_mm and args.canvas_bin_mm > 0:
        def round_up(v: float, b: float) -> float:
            n = int((v + b - 1e-9) // b)
            return (n + (0 if abs(n * b - v) < 1e-9 else 1)) * b
        width_mm = round_up(width_mm, args.canvas_bin_mm)
        height_mm = round_up(height_mm, args.canvas_bin_mm)
        logging.info(f"Canvas dimensions after rounding to {args.canvas_bin_mm}mm: {width_mm:.2f} x {height_mm:.2f} mm")

    # Recenter
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    for pl in placements:
        x, y = pl.center_xy_mm
        pl.center_xy_mm = (x - cx, y - cy)

    dpi = args.tiff_dpi
    logging.info(f"Initial DPI: {dpi}")
    
    if args.target_mb:
        bpp = 1 if args.tiff_mode == "bilevel" else 8
        dpi = compute_dpi_for_target_mb(width_mm, height_mm, args.target_mb, bits_per_pixel=bpp)
        logging.info(f"DPI adjusted for target {args.target_mb}MB: {dpi}")

    try:
        logging.info("Starting raster composition")
        logging.debug(f"Composition params - DPI: {dpi}, canvas: {width_mm:.2f}x{height_mm:.2f}mm")
        
        # Get page margins from CLI arguments
        page_margins_mm = (
            args.page_margin_left_mm,
            args.page_margin_top_mm,
            args.page_margin_right_mm,
            args.page_margin_bottom_mm
        )
        
        raster = compose_raster_any_shape(
            placements=placements,
            doc_registry=docs,
            dpi=dpi,
            canvas_width_mm=width_mm,
            canvas_height_mm=height_mm,
            origin_center=True,
            page_margins_mm=page_margins_mm,
            standard_page_width_px=args.standard_page_width_px,
            standard_page_height_px=args.standard_page_height_px,
        )
        
        logging.info(f"Raster composition complete. Image size: {raster.width}x{raster.height} pixels")
    except Exception as e:
        logging.error(f"Error during raster composition: {e}")
        print(f"Error during raster composition: {e}")
        return 5

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        save_pdf_proof(raster, args.output, width_mm, height_mm)
        print(f"Wrote PDF proof: {args.output}")

    if args.export_tiff:
        os.makedirs(os.path.dirname(args.export_tiff) or ".", exist_ok=True)
        
        # Pre-validate dimensions to provide better error messages
        canvas_w_px, canvas_h_px, safe_dpi = validate_canvas_dimensions(width_mm, height_mm, dpi)
        if safe_dpi < dpi:
            print(f"Info: DPI automatically reduced from {dpi} to {safe_dpi} to prevent image overflow")
            print(f"Canvas dimensions: {width_mm:.1f}mm x {height_mm:.1f}mm")
            if args.optimize_for_dpi is None:
                print("Tip: Use --optimize-for-dpi to auto-scale SVG shapes for your target DPI")
        
        try:
            if args.tiff_mode == "bilevel":
                save_tiff_1bit(raster, args.export_tiff, safe_dpi, compression=args.tiff_compression)
            else:
                save_tiff_gray(raster, args.export_tiff, safe_dpi, compression=args.tiff_compression)
            print(f"Wrote TIFF: {args.export_tiff}")
        except Exception as e:
            print(f"Error saving TIFF: {e}")
            print("Suggestions:")
            print("  - Use --optimize-for-dpi <target_dpi> to auto-scale SVG shapes and prevent overflow")
            print("  - Reduce DPI (use --tiff-dpi with a lower value)")
            print("  - Use --target-mb to automatically calculate safe DPI")
            print("  - Reduce canvas size or number of pages")
            return 5

    for d in docs:
        d.close()

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nanorosetta", description="Any-shape wafer layout CLI")
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("compose", help="Compose PDF pages around any inner shape constrained to any outer shape")
    c.add_argument("--input", action="append", required=True, help="Input PDF path (repeatable)")
    c.add_argument("--outer-shape", required=True, help="SVG path/polygon file for outer constraint")
    c.add_argument("--inner-shape", action="append", help="SVG path/polygon file(s) for inner keep-outs (repeatable)")
    c.add_argument("--inner-position", choices=["center", "top-left", "top-center", "top-right", "middle-left", "middle-right", "bottom-left", "bottom-center", "bottom-right"], default="center", help="Position inner shape relative to outer shape (default: center)")
    c.add_argument("--output", help="Output PDF proof path")
    c.add_argument("--export-tiff", help="Optional TIFF output path")

    # TIFF controls
    c.add_argument("--tiff-mode", choices=["bilevel", "gray"], default="bilevel", help="1-bit or 8-bit grayscale")
    c.add_argument("--tiff-compression", choices=["none", "deflate", "lzw"], default="lzw")
    c.add_argument("--tiff-dpi", type=int, default=1200, help="Raster DPI if no target size is set")
    c.add_argument("--target-mb", type=float, help="Target approximate TIFF size in MB (auto-compute DPI)")

    # Layout controls
    c.add_argument("--nominal-height-mm", type=float, default=3.0, help="Nominal page height along streamlines (mm)")
    c.add_argument("--gap-mm", type=float, default=0.5, help="Minimum gap between pages (mm)")
    c.add_argument("--orientation", choices=["tangent", "upright"], default="tangent")
    c.add_argument("--scale-min", type=float, default=0.1)
    c.add_argument("--scale-max", type=float, default=1.0)
    c.add_argument("--streamline-step-mm", type=float, default=2.0, help="Offset step for streamlines (mm)")
    c.add_argument("--max-streamlines", type=int, default=200)
    c.add_argument("--optimize-for-dpi", type=int, help="Calculate optimal page size to fill area at this DPI (overrides --nominal-height-mm)")
    c.add_argument("--max-canvas-pixels", type=int, default=100_000_000, help="Maximum canvas pixels for memory management (default: 100M)")

    # Canvas controls
    c.add_argument("--canvas-margin-mm", type=float, default=5.0, help="Extra margin around outer bounds (mm)")
    c.add_argument("--canvas-bin-mm", type=float, help="Round canvas dimensions to multiples of this value (mm)")
    
    # Page margins (crop PDF pages)
    c.add_argument("--page-margin-left-mm", type=float, default=12.7, help="Left margin (gutter) to crop from PDF pages (mm, default: 12.7 = 0.5\")")
    c.add_argument("--page-margin-top-mm", type=float, default=6.35, help="Top margin to crop from PDF pages (mm, default: 6.35 = 0.25\")")
    c.add_argument("--page-margin-right-mm", type=float, default=6.35, help="Right margin to crop from PDF pages (mm, default: 6.35 = 0.25\")")
    c.add_argument("--page-margin-bottom-mm", type=float, default=6.35, help="Bottom margin to crop from PDF pages (mm, default: 6.35 = 0.25\")")
    
    # Standard page dimensions (pixel-based processing)
    c.add_argument("--standard-page-width-px", type=int, default=1700, help="Standard page width in pixels (default: 1700)")
    c.add_argument("--standard-page-height-px", type=int, default=2200, help="Standard page height in pixels (default: 2200)")
    c.add_argument("--gap-px", type=int, default=50, help="Gap between pages in pixels (default: 50)")
    c.add_argument("--pixel-first", action="store_true", help="Use pixel-first layout approach (calculates exact canvas size needed)")
    
    # Advanced packing options
    c.add_argument("--use-optimized-packing", action="store_true", help="Use advanced optimized packing algorithm for better space utilization")
    c.add_argument("--packing-flexibility", type=float, default=0.1, help="Allow page size variation for better packing (0.0-1.0, default: 0.1)")
    c.add_argument("--adaptive-sizing", action="store_true", help="Automatically adjust page sizes to achieve target fill ratio")
    c.add_argument("--target-fill-ratio", type=float, default=0.85, help="Target space utilization ratio for adaptive sizing (default: 0.85)")
    
    # Combined SVG options
    c.add_argument("--auto-detect-inner", action="store_true", help="Automatically detect inner shapes from outer SVG file (largest shape = outer, smaller shapes = inner)")
    c.add_argument("--min-inner-area-ratio", type=float, default=0.01, help="Minimum area ratio for auto-detected inner shapes (relative to outer shape, default: 0.01)")

    c.set_defaults(func=cli_compose)

    # Add diagnose command
    d = sub.add_parser("diagnose", help="Diagnose an SVG file and show its contents")
    d.add_argument("svg_file", help="SVG file to diagnose")
    d.set_defaults(func=cli_diagnose)

    return p


def main(argv: List[str] | None = None) -> int:
    # Setup logging first
    _setup_logging()
    
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    
    try:
        result = args.func(args)
        logging.info(f"Operation completed with exit code: {result}")
        return result
    except Exception as e:
        logging.error(f"Unhandled exception: {e}", exc_info=True)
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
