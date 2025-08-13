from __future__ import annotations

import logging
import math
from typing import List, Tuple

from shapely.geometry import MultiPolygon, Point
from shapely.ops import unary_union

from .layout import PageSpec, Placement


def calculate_pixel_layout(
    pages: List[PageSpec],
    allowed_region_bounds: Tuple[float, float, float, float],  # (minx, miny, maxx, maxy) in mm
    standard_page_width_px: int = 1700,
    standard_page_height_px: int = 2200,
    gap_px: int = 50,  # Gap in pixels, not mm
    pixels_per_mm: float = 200/25.4,  # Default conversion, but layout is pixel-based
) -> List[Placement]:
    """
    Calculate layout based on pixel dimensions first, then convert to mm for compatibility.
    
    Args:
        pages: List of page specifications
        allowed_region_bounds: Bounds of allowed region in mm (for compatibility)
        standard_page_width_px: Standard page width in pixels
        standard_page_height_px: Standard page height in pixels  
        gap_px: Gap between pages in pixels
        pixels_per_mm: Conversion factor (only for final mm output)
    
    Returns:
        List of placements with positions converted to mm for compatibility
    """
    if not pages:
        return []
    
    logging.info(f"Pixel-based layout: {standard_page_width_px}x{standard_page_height_px}px pages with {gap_px}px gaps")
    
    # Convert allowed region to pixel coordinates
    minx_mm, miny_mm, maxx_mm, maxy_mm = allowed_region_bounds
    region_width_px = int((maxx_mm - minx_mm) * pixels_per_mm)
    region_height_px = int((maxy_mm - miny_mm) * pixels_per_mm)
    
    logging.info(f"Available region: {region_width_px}x{region_height_px} pixels")
    
    # Calculate grid dimensions in pixels
    page_step_x_px = standard_page_width_px + gap_px
    page_step_y_px = standard_page_height_px + gap_px
    
    # Calculate how many pages fit
    cols = max(1, region_width_px // page_step_x_px)
    rows = max(1, region_height_px // page_step_y_px)
    
    max_pages = cols * rows
    logging.info(f"Grid: {cols} cols × {rows} rows = {max_pages} max pages")
    
    if len(pages) > max_pages:
        logging.warning(f"Only {max_pages} of {len(pages)} pages will fit in current region")
    
    # Generate placements
    placements = []
    page_count = min(len(pages), max_pages)
    
    for i in range(page_count):
        # Calculate grid position
        col = i % cols
        row = i // cols
        
        # Calculate pixel position (center of page)
        x_px = col * page_step_x_px + standard_page_width_px // 2
        y_px = row * page_step_y_px + standard_page_height_px // 2
        
        # Convert back to mm for compatibility with existing system
        x_mm = (x_px / pixels_per_mm) + minx_mm
        y_mm = (y_px / pixels_per_mm) + miny_mm
        
        # Page dimensions in mm (for compatibility)
        width_mm = standard_page_width_px / pixels_per_mm
        height_mm = standard_page_height_px / pixels_per_mm
        
        page_spec = pages[i]
        placement = Placement(
            page_global_index=i,
            doc_index=page_spec.doc_index,
            page_index=page_spec.page_index,
            center_xy_mm=(x_mm, y_mm),
            width_mm=width_mm,
            height_mm=height_mm,
            rotation_deg=0.0,  # No rotation in pixel-based layout
        )
        placements.append(placement)
        
        logging.debug(f"Page {i}: grid({col},{row}) -> {x_px},{y_px}px -> {x_mm:.1f},{y_mm:.1f}mm")
    
    logging.info(f"Generated {len(placements)} pixel-based placements")
    return placements


def calculate_required_region_size_pixels(
    page_count: int,
    standard_page_width_px: int = 1700,
    standard_page_height_px: int = 2200,
    gap_px: int = 50,
    target_aspect_ratio: float = 1.0,  # 1.0 = square, >1.0 = wider, <1.0 = taller
) -> Tuple[int, int]:
    """
    Calculate the exact pixel dimensions needed to fit all pages with target aspect ratio.
    
    Args:
        target_aspect_ratio: Target width/height ratio (1.0 for square canvas)
    
    Returns:
        (width_px, height_px) required canvas size in pixels
    """
    page_aspect_ratio = standard_page_width_px / standard_page_height_px
    
    # Calculate grid dimensions that respect both page count and target aspect ratio
    # For a square canvas (target_aspect_ratio = 1.0):
    # canvas_width / canvas_height = 1.0
    # (cols * page_width) / (rows * page_height) = 1.0
    # cols / rows = page_height / page_width
    
    # Start with square grid as baseline
    baseline_side = math.ceil(math.sqrt(page_count))
    
    # Adjust grid to achieve target aspect ratio
    if target_aspect_ratio == 1.0:  # Square canvas
        # Adjust grid to compensate for page aspect ratio
        rows = baseline_side
        cols = math.ceil((rows * standard_page_height_px) / standard_page_width_px)
        
        # Ensure we have enough slots for all pages
        while cols * rows < page_count:
            if (cols + 1) * rows < (rows + 1) * cols:
                cols += 1
            else:
                rows += 1
    else:
        # For non-square targets, use the target aspect ratio directly
        rows = baseline_side  
        cols = math.ceil(rows * target_aspect_ratio * (standard_page_height_px / standard_page_width_px))
        
        # Ensure we have enough slots
        while cols * rows < page_count:
            if (cols + 1) * rows < (rows + 1) * cols:
                cols += 1
            else:
                rows += 1
    
    # Calculate required pixel dimensions
    width_px = cols * (standard_page_width_px + gap_px) - gap_px
    height_px = rows * (standard_page_height_px + gap_px) - gap_px
    
    actual_aspect_ratio = width_px / height_px
    
    logging.info(f"Required canvas for {page_count} pages: {width_px:,}x{height_px:,} pixels")
    logging.info(f"Grid layout: {cols} cols × {rows} rows")
    logging.info(f"Page aspect ratio: {page_aspect_ratio:.3f}, Target canvas aspect: {target_aspect_ratio:.3f}")
    logging.info(f"Actual canvas aspect ratio: {actual_aspect_ratio:.3f}")
    logging.info(f"Page dimensions: {standard_page_width_px}x{standard_page_height_px}px with {gap_px}px gaps")
    
    return width_px, height_px


def calculate_svg_scale_factor(
    current_svg_width_mm: float,
    current_svg_height_mm: float, 
    required_width_px: int,
    required_height_px: int,
    pixels_per_mm: float = 200/25.4,
) -> float:
    """
    Calculate how much to scale SVG shapes to accommodate required pixel dimensions.
    
    Returns:
        Scale factor to apply to SVG shapes
    """
    # Convert required pixels to mm
    required_width_mm = required_width_px / pixels_per_mm
    required_height_mm = required_height_px / pixels_per_mm
    
    # Calculate scale factors for width and height
    scale_x = required_width_mm / current_svg_width_mm
    scale_y = required_height_mm / current_svg_height_mm
    
    # Use the larger scale factor to ensure everything fits
    scale_factor = max(scale_x, scale_y)
    
    logging.info(f"SVG scaling: {current_svg_width_mm:.1f}x{current_svg_height_mm:.1f}mm -> {required_width_mm:.1f}x{required_height_mm:.1f}mm")
    logging.info(f"Scale factor: {scale_factor:.4f}x")
    
    return scale_factor