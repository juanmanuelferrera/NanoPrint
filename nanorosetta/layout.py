from __future__ import annotations

import logging
import math
from typing import List, Literal, Sequence, Tuple

import numpy as np
from shapely.geometry import MultiPolygon, LineString
from shapely.ops import unary_union

from .units import mm_to_px, px_to_mm

Orientation = Literal["tangent", "upright"]


class PageSpec:
    def __init__(self, doc_index: int, page_index: int, width_pt: float, height_pt: float) -> None:
        self.doc_index = doc_index
        self.page_index = page_index
        self.width_pt = width_pt
        self.height_pt = height_pt
        self.aspect_ratio = width_pt / height_pt if height_pt > 0 else 1.0


class Placement:
    def __init__(
        self,
        page_global_index: int,
        doc_index: int,
        page_index: int,
        center_xy_mm: Tuple[float, float],
        width_mm: float,
        height_mm: float,
        rotation_deg: float,
    ) -> None:
        self.page_global_index = page_global_index
        self.doc_index = doc_index
        self.page_index = page_index
        self.center_xy_mm = center_xy_mm
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.rotation_deg = rotation_deg


def calculate_safe_page_dimensions(
    page_count: int,
    target_dpi: int,
    max_canvas_pixels: int = 100_000_000,  # 100M pixels max
    min_page_height_mm: float = 1.0,
    max_page_height_mm: float = 50.0,
) -> float:
    """
    Calculate safe page dimensions for large document counts.
    
    Args:
        page_count: Number of pages to layout
        target_dpi: Target output DPI
        max_canvas_pixels: Maximum total canvas pixels (memory constraint)
        min_page_height_mm: Minimum page height in mm
        max_page_height_mm: Maximum page height in mm
    
    Returns:
        Safe page height in mm
    """
    # Estimate canvas area needed (assuming roughly square layout)
    estimated_canvas_side_pixels = math.sqrt(max_canvas_pixels)
    
    # Convert to mm
    canvas_side_mm = estimated_canvas_side_pixels / (target_dpi / 25.4)
    
    # Estimate how many pages can fit in this area
    # Assume pages are roughly 1:1.4 aspect ratio (A4-like)
    avg_aspect_ratio = 1.4
    
    # Calculate optimal page size to fit all pages
    # This is a simplified calculation - in practice, layout algorithm will optimize
    estimated_pages_per_row = math.sqrt(page_count * avg_aspect_ratio)
    estimated_rows = page_count / estimated_pages_per_row
    
    if estimated_pages_per_row > 0 and estimated_rows > 0:
        # Calculate page height that fits in the canvas
        page_height_mm = min(
            canvas_side_mm / estimated_rows,
            canvas_side_mm / (estimated_pages_per_row * avg_aspect_ratio)
        )
    else:
        # Fallback calculation
        page_height_mm = math.sqrt(canvas_side_mm * canvas_side_mm / page_count / avg_aspect_ratio)
    
    # Constrain to reasonable bounds
    page_height_mm = max(min_page_height_mm, min(max_page_height_mm, page_height_mm))
    
    return page_height_mm


def calculate_required_svg_scale(
    pages: List[PageSpec],
    page_height_mm: float,
    gap_mm: float = 0.5,
    margin_mm: float = 5.0,
) -> float:
    """
    Calculate the scale factor needed for SVG shapes to accommodate all pages.
    
    Args:
        pages: List of page specifications
        page_height_mm: Height of each page in mm
        gap_mm: Gap between pages in mm
        margin_mm: Margin around the layout in mm
    
    Returns:
        Scale factor to apply to SVG shapes
    """
    if not pages:
        return 1.0
    
    # Calculate total area needed for all pages
    total_page_area_mm2 = 0
    for page in pages:
        page_width_mm = page.aspect_ratio * page_height_mm
        page_area_mm2 = page_width_mm * page_height_mm
        total_page_area_mm2 += page_area_mm2
    
    # Add gap area (simplified calculation)
    # Assume pages are arranged in a roughly square grid
    page_count = len(pages)
    estimated_pages_per_row = math.sqrt(page_count)
    estimated_rows = page_count / estimated_pages_per_row
    
    # Calculate gap area
    avg_page_width_mm = sum(p.aspect_ratio for p in pages) / len(pages) * page_height_mm
    gap_area_mm2 = (estimated_pages_per_row - 1) * estimated_rows * avg_page_width_mm * gap_mm
    gap_area_mm2 += (estimated_rows - 1) * estimated_pages_per_row * page_height_mm * gap_mm
    
    # Total area needed including gaps and margin
    total_needed_area_mm2 = total_page_area_mm2 + gap_area_mm2
    
    # Calculate required scale factor
    # We need to scale the SVG shapes so their area difference can accommodate this
    # For simplicity, assume we need to scale by the square root of the area ratio
    # This is a rough approximation - the actual layout algorithm will optimize placement
    
    # Estimate current SVG area (this would come from the actual SVG shapes)
    # For now, we'll return a scale factor that the caller can apply
    # The actual calculation should be done in the CLI where we have access to the SVG shapes
    
    return math.sqrt(total_needed_area_mm2 / 1000.0)  # Rough estimate, will be refined


def calculate_optimal_page_size(
    allowed_region_mm: MultiPolygon,
    pages: List[PageSpec],
    dpi: int,
    gap_mm: float = 0.5,
    min_page_height_mm: float = 1.0,
    max_page_height_mm: float = 50.0,
    max_canvas_pixels: int = 100_000_000,  # 100M pixels max
) -> float:
    """
    Calculate optimal page height to efficiently fill the available area.
    
    Args:
        allowed_region_mm: The region where pages can be placed
        pages: List of page specifications
        dpi: Target output DPI
        gap_mm: Gap between pages
        min_page_height_mm: Minimum page height in mm
        max_page_height_mm: Maximum page height in mm
        max_canvas_pixels: Maximum total canvas pixels (memory constraint)
    
    Returns:
        Optimal page height in mm
    """
    if not pages or allowed_region_mm.is_empty:
        return min_page_height_mm
    
    # For large page counts, use safe calculation
    if len(pages) > 500:
        return calculate_safe_page_dimensions(
            len(pages), dpi, max_canvas_pixels, min_page_height_mm, max_page_height_mm
        )
    
    # Calculate total area available
    total_area_mm2 = allowed_region_mm.area
    
    # Calculate total page area needed (including gaps)
    total_aspect_ratio = sum(p.aspect_ratio for p in pages)
    avg_aspect_ratio = total_aspect_ratio / len(pages)
    
    # Estimate how many pages can fit in the area
    # This is a simplified calculation - we'll refine it
    estimated_pages_per_row = math.sqrt(len(pages) * avg_aspect_ratio)
    estimated_rows = len(pages) / estimated_pages_per_row
    
    # Calculate how big pages would be if we used ALL available area (perfect packing)
    total_aspect_area = sum(p.aspect_ratio for p in pages)
    perfect_packing_height = math.sqrt(total_area_mm2 / total_aspect_area)
    
    logging.info(f"Packing analysis: {len(pages)} pages in {total_area_mm2:.1f}mm² available area")
    logging.info(f"Perfect packing would use {perfect_packing_height:.1f}mm page height")
    
    # Calculate optimal page height to fill the area
    # Area = rows * page_height * (cols * page_width + gaps)
    # page_width = page_height * avg_aspect_ratio
    # cols = estimated_pages_per_row
    
    # Solve for page_height:
    # total_area = rows * page_height^2 * cols * aspect + rows * page_height * gaps
    
    # Simplified: assume gaps are small relative to page area
    # total_area ≈ rows * cols * page_height^2 * aspect
    # page_height ≈ sqrt(total_area / (rows * cols * aspect))
    
    if estimated_pages_per_row > 0 and estimated_rows > 0:
        optimal_height = math.sqrt(total_area_mm2 / (estimated_rows * estimated_pages_per_row * avg_aspect_ratio))
    else:
        optimal_height = math.sqrt(total_area_mm2 / len(pages))
    
    # Constrain to reasonable bounds
    optimal_height = max(min_page_height_mm, min(max_page_height_mm, optimal_height))
    
    # Calculate actual packing efficiency with the constrained height
    actual_total_area = total_aspect_area * optimal_height**2
    packing_efficiency = actual_total_area / total_area_mm2
    
    logging.info(f"Selected page height: {optimal_height:.1f}mm")
    logging.info(f"Packing efficiency: {packing_efficiency:.1%} of available area")
    if optimal_height != perfect_packing_height:
        logging.info(f"Height constrained from {perfect_packing_height:.1f}mm to {optimal_height:.1f}mm")
    
    return optimal_height


def _offset_boundaries(region: MultiPolygon, offsets_mm: Sequence[float]) -> List[LineString]:
    """Generate offset boundaries as streamlines."""
    boundaries: List[LineString] = []
    for off in offsets_mm:
        try:
            offset_geom = region.buffer(-off, join_style=2, mitre_limit=1.0)
            if offset_geom.is_empty:
                break
            if isinstance(offset_geom, MultiPolygon):
                for poly in offset_geom.geoms:
                    if poly.length > 0:
                        boundaries.append(LineString(poly.exterior.coords))
            elif hasattr(offset_geom, 'exterior'):
                if offset_geom.length > 0:
                    boundaries.append(LineString(offset_geom.exterior.coords))
        except Exception:
            continue
    return boundaries


def _arc_length_positions(line: LineString, step_mm: float) -> List[Tuple[float, float, float]]:
    """Generate positions along line at arc-length intervals."""
    coords = list(line.coords)
    if len(coords) < 2:
        return []
    
    # Cumulative arc-lengths
    seg_lengths = []
    for i in range(1, len(coords)):
        x0, y0 = coords[i - 1]
        x1, y1 = coords[i]
        seg_lengths.append(math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2))
    
    total = sum(seg_lengths)
    if total <= 0:
        return []
    
    # Generate positions
    positions = []
    s = 0.0
    target = step_mm / 2.0  # Start at half step
    idx = 1
    
    while target <= total and idx < len(coords):
        # Advance until we reach target along segments
        while idx < len(coords) and s + seg_lengths[idx - 1] < target:
            s += seg_lengths[idx - 1]
            idx += 1
        if idx >= len(coords):
            break
        
        # Interpolate within segment
        remain = target - s
        seg_len = seg_lengths[idx - 1]
        if seg_len <= 0:
            idx += 1
            target += step_mm
            continue
        
        t = remain / seg_len
        x0, y0 = coords[idx - 1]
        x1, y1 = coords[idx]
        x = x0 + t * (x1 - x0)
        y = y0 + t * (y1 - y0)
        
        # Local tangent angle
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        positions.append((x, y, ang))
        
        target += step_mm
    
    return positions


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
    """
    Plan page layout with optional DPI optimization.
    
    Args:
        optimize_for_dpi: If provided, calculate optimal page size to fill area at this DPI
    """
    placements: List[Placement] = []
    if not pages or allowed_region_mm.is_empty:
        return placements
    
    # Calculate optimal page size if DPI optimization is requested
    if optimize_for_dpi is not None:
        # For single pages, use a more conservative approach to avoid excessive scaling
        if len(pages) == 1:
            logging.info(f"Single page detected - using conservative sizing instead of region-filling optimization")
            # Calculate reasonable size based on page aspect ratio and target DPI
            page = pages[0]
            aspect_ratio = page.width_pt / page.height_pt if page.height_pt > 0 else 1.0
            
            # Use a reasonable height for single pages - make them clearly visible  
            # This prevents single pages from being scaled to fill the entire region
            base_height_mm = min(40.0, max(25.0, nominal_height_mm))  # Minimum 25mm for readable text
            nominal_height_mm = base_height_mm
            logging.info(f"Single page sized at {nominal_height_mm:.1f}mm height (aspect ratio: {aspect_ratio:.2f})")
        else:
            # Use full optimization for multiple pages
            logging.info(f"Multiple pages ({len(pages)}) detected - using region-filling optimization")
            nominal_height_mm = calculate_optimal_page_size(
                allowed_region_mm, pages, optimize_for_dpi, gap_mm, 
                min_page_height_mm=1.0, max_page_height_mm=50.0, max_canvas_pixels=max_canvas_pixels
            )
            logging.info(f"Optimized page height: {nominal_height_mm:.1f}mm")
    
    # Generate inward offsets as streamlines
    offsets = [i * streamline_step_mm for i in range(max_streamlines)]
    lines = _offset_boundaries(allowed_region_mm, offsets)
    
    page_cursor = 0
    page_count = len(pages)
    
    # Generate rectangular grid positions within the allowed region
    # Calculate average page dimensions
    avg_width_mm = nominal_height_mm * sum(p.aspect_ratio for p in pages) / len(pages)
    
    # Get bounding box of allowed region
    minx, miny, maxx, maxy = allowed_region_mm.bounds
    region_width = maxx - minx
    region_height = maxy - miny
    
    # Calculate grid spacing
    step_x = avg_width_mm + gap_mm
    step_y = nominal_height_mm + gap_mm
    
    # Calculate number of columns and rows that fit
    cols = max(1, int(region_width / step_x))
    rows = max(1, int(region_height / step_y))
    
    logging.info(f"Grid layout: {cols} columns × {rows} rows (step: {step_x:.1f}×{step_y:.1f}mm)")
    
    # Generate grid positions (left-to-right, top-to-bottom)
    grid_positions = []
    for row in range(rows):
        for col in range(cols):
            # Calculate position within bounding box
            x = minx + (col + 0.5) * step_x
            y = maxy - (row + 0.5) * step_y  # Start from top
            
            # Check if position is actually inside the allowed region
            from shapely.geometry import Point
            if allowed_region_mm.contains(Point(x, y)):
                grid_positions.append((x, y, 0.0))  # 0.0 angle for rectangular grid
            
            if len(grid_positions) >= page_count:
                break
        if len(grid_positions) >= page_count:
            break
    
    # Place pages in grid order
    for i, (x, y, ang) in enumerate(grid_positions):
        if page_cursor >= page_count:
            break
            
        spec = pages[page_cursor]
        height_mm = nominal_height_mm
        width_mm = spec.aspect_ratio * height_mm
        
        rot = 0.0
        if orientation == "tangent":
            rot = ang
        
        placement = Placement(
            page_global_index=page_cursor,
            doc_index=spec.doc_index,
            page_index=spec.page_index,
            center_xy_mm=(x, y),
            width_mm=width_mm,
            height_mm=height_mm,
            rotation_deg=rot,
        )
        placements.append(placement)
        page_cursor += 1
    
    return placements
