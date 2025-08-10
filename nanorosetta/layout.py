from __future__ import annotations

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


def calculate_optimal_page_size(
    allowed_region_mm: MultiPolygon,
    pages: List[PageSpec],
    dpi: int,
    gap_mm: float = 0.5,
    min_page_height_mm: float = 1.0,
    max_page_height_mm: float = 50.0,
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
    
    Returns:
        Optimal page height in mm
    """
    if not pages or allowed_region_mm.is_empty:
        return min_page_height_mm
    
    # Calculate total area available
    total_area_mm2 = allowed_region_mm.area
    
    # Calculate total page area needed (including gaps)
    total_aspect_ratio = sum(p.aspect_ratio for p in pages)
    avg_aspect_ratio = total_aspect_ratio / len(pages)
    
    # Estimate how many pages can fit in the area
    # This is a simplified calculation - we'll refine it
    estimated_pages_per_row = math.sqrt(len(pages) * avg_aspect_ratio)
    estimated_rows = len(pages) / estimated_pages_per_row
    
    # Calculate optimal page height to fill the area
    # Area = rows * page_height * (cols * page_width + gaps)
    # page_width = page_height * avg_aspect_ratio
    # cols = estimated_pages_per_row
    
    # Solve for page_height:
    # total_area = rows * page_height * (cols * page_height * aspect + gaps)
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
    gap_mm: float,
    orientation: Orientation = "tangent",
    scale_min: float = 0.1,
    scale_max: float = 1.0,
    streamline_step_mm: float = 2.0,
    max_streamlines: int = 200,
    optimize_for_dpi: int = None,
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
        nominal_height_mm = calculate_optimal_page_size(
            allowed_region_mm, pages, optimize_for_dpi, gap_mm
        )
    
    # Generate inward offsets as streamlines
    offsets = [i * streamline_step_mm for i in range(max_streamlines)]
    lines = _offset_boundaries(allowed_region_mm, offsets)
    
    page_cursor = 0
    page_count = len(pages)
    
    for ln in lines:
        if page_cursor >= page_count:
            break
        
        # Determine per-page width from aspect and nominal height
        spec = pages[page_cursor]
        height_mm = nominal_height_mm
        width_mm = spec.aspect_ratio * height_mm
        step = width_mm + gap_mm
        
        for x, y, ang in _arc_length_positions(ln, step_mm=step):
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
            if page_cursor >= page_count:
                break
    
    return placements
