from __future__ import annotations

import logging
import math
from typing import List, Tuple, Optional
import random

from shapely.geometry import MultiPolygon, Point, box
from shapely.ops import unary_union

from .layout import PageSpec, Placement


def calculate_space_utilization(
    placements: List[Placement], 
    allowed_region: MultiPolygon
) -> float:
    """Calculate how efficiently the placements utilize the available space."""
    if not placements or allowed_region.is_empty:
        return 0.0
    
    # Calculate total area used by pages
    total_page_area = sum(p.width_mm * p.height_mm for p in placements)
    available_area = allowed_region.area
    
    return total_page_area / available_area if available_area > 0 else 0.0


def analyze_shape_characteristics(shape: MultiPolygon) -> dict:
    """Analyze shape characteristics for optimal packing strategies."""
    bounds = shape.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    area = shape.area
    bounding_area = width * height
    
    # Calculate shape complexity metrics
    rectangularity = area / bounding_area if bounding_area > 0 else 0
    aspect_ratio = width / height if height > 0 else 1
    
    # Detect common shape types
    shape_type = "complex"
    if rectangularity > 0.95:
        shape_type = "rectangular"
    elif abs(aspect_ratio - 1.0) < 0.1 and rectangularity > 0.75:
        shape_type = "square_like"
    elif aspect_ratio > 2.0 or aspect_ratio < 0.5:
        shape_type = "elongated"
    
    return {
        "width": width,
        "height": height,
        "area": area,
        "aspect_ratio": aspect_ratio,
        "rectangularity": rectangularity,
        "shape_type": shape_type
    }


def generate_candidate_positions(
    allowed_region: MultiPolygon,
    page_width_mm: float,
    page_height_mm: float,
    spacing_mm: float = 0.5,
    sample_density: int = 20,
    shape_characteristics: Optional[dict] = None
) -> List[Tuple[float, float]]:
    """Generate candidate positions within the allowed region using shape-aware sampling."""
    positions = []
    
    # Analyze shape if not provided
    if shape_characteristics is None:
        shape_characteristics = analyze_shape_characteristics(allowed_region)
    
    # Get bounding box
    minx, miny, maxx, maxy = allowed_region.bounds
    width = maxx - minx
    height = maxy - miny
    
    # Adapt sampling strategy based on shape characteristics
    shape_type = shape_characteristics["shape_type"]
    
    if shape_type == "rectangular":
        # For rectangular shapes, use efficient grid sampling
        step_x = max(page_width_mm + spacing_mm, width / sample_density)
        step_y = max(page_height_mm + spacing_mm, height / sample_density)
    elif shape_type == "square_like":
        # For square-like shapes, use denser sampling
        step_x = max(page_width_mm + spacing_mm, width / (sample_density * 1.2))
        step_y = max(page_height_mm + spacing_mm, height / (sample_density * 1.2))
    elif shape_type == "elongated":
        # For elongated shapes, sample more densely along the shorter dimension
        if width > height:
            step_x = max(page_width_mm + spacing_mm, width / sample_density)
            step_y = max(page_height_mm + spacing_mm, height / (sample_density * 1.5))
        else:
            step_x = max(page_width_mm + spacing_mm, width / (sample_density * 1.5))
            step_y = max(page_height_mm + spacing_mm, height / sample_density)
    else:
        # For complex shapes, use adaptive sampling
        step_x = max(page_width_mm + spacing_mm, width / (sample_density * 0.8))
        step_y = max(page_height_mm + spacing_mm, height / (sample_density * 0.8))
    
    # Generate grid positions
    x = minx + page_width_mm / 2
    while x <= maxx - page_width_mm / 2:
        y = miny + page_height_mm / 2
        while y <= maxy - page_height_mm / 2:
            # Create a box representing the page at this position
            page_box = box(
                x - page_width_mm / 2, y - page_height_mm / 2,
                x + page_width_mm / 2, y + page_height_mm / 2
            )
            
            # Check if the page would fit completely within the allowed region
            if allowed_region.contains(page_box):
                positions.append((x, y))
            
            y += step_y
        x += step_x
    
    # Add shape-aware random positions for better coverage
    random_samples = min(100, len(positions) // 2)
    if shape_type == "complex":
        random_samples *= 2  # More random samples for complex shapes
    
    for _ in range(random_samples):
        rand_x = random.uniform(minx + page_width_mm / 2, maxx - page_width_mm / 2)
        rand_y = random.uniform(miny + page_height_mm / 2, maxy - page_height_mm / 2)
        
        page_box = box(
            rand_x - page_width_mm / 2, rand_y - page_height_mm / 2,
            rand_x + page_width_mm / 2, rand_y + page_height_mm / 2
        )
        
        if allowed_region.contains(page_box):
            positions.append((rand_x, rand_y))
    
    return positions


def check_placement_collision(
    new_x: float, new_y: float, new_width: float, new_height: float,
    existing_placements: List[Placement],
    min_gap_mm: float = 0.5
) -> bool:
    """Check if a new placement would collide with existing placements."""
    new_box = box(
        new_x - new_width / 2 - min_gap_mm / 2,
        new_y - new_height / 2 - min_gap_mm / 2,
        new_x + new_width / 2 + min_gap_mm / 2,
        new_y + new_height / 2 + min_gap_mm / 2
    )
    
    for existing in existing_placements:
        existing_box = box(
            existing.center_xy_mm[0] - existing.width_mm / 2 - min_gap_mm / 2,
            existing.center_xy_mm[1] - existing.height_mm / 2 - min_gap_mm / 2,
            existing.center_xy_mm[0] + existing.width_mm / 2 + min_gap_mm / 2,
            existing.center_xy_mm[1] + existing.height_mm / 2 + min_gap_mm / 2
        )
        
        if new_box.intersects(existing_box):
            return True
    
    return False


def analyze_inner_constraints(
    outer_shape: MultiPolygon,
    inner_shapes: List[MultiPolygon],
    allowed_region: MultiPolygon
) -> dict:
    """Analyze inner shape constraints for optimal packing strategies."""
    if not inner_shapes:
        return {"has_inner": False, "constraint_type": "none"}
    
    outer_bounds = outer_shape.bounds
    outer_width = outer_bounds[2] - outer_bounds[0]
    outer_height = outer_bounds[3] - outer_bounds[1]
    outer_area = outer_shape.area
    
    total_inner_area = sum(shape.area for shape in inner_shapes)
    constraint_ratio = total_inner_area / outer_area
    
    # Analyze spatial distribution of inner shapes
    inner_centers = []
    for shape in inner_shapes:
        bounds = shape.bounds
        center_x = (bounds[0] + bounds[2]) / 2
        center_y = (bounds[1] + bounds[3]) / 2
        inner_centers.append((center_x, center_y))
    
    # Determine constraint type based on inner shape characteristics
    constraint_type = "distributed"
    if len(inner_shapes) == 1:
        inner_bounds = inner_shapes[0].bounds
        inner_center_x = (inner_bounds[0] + inner_bounds[2]) / 2
        inner_center_y = (inner_bounds[1] + inner_bounds[3]) / 2
        outer_center_x = (outer_bounds[0] + outer_bounds[2]) / 2
        outer_center_y = (outer_bounds[1] + outer_bounds[3]) / 2
        
        # Check if inner shape is centered
        if (abs(inner_center_x - outer_center_x) < outer_width * 0.1 and 
            abs(inner_center_y - outer_center_y) < outer_height * 0.1):
            constraint_type = "central"
        else:
            constraint_type = "offset"
    
    return {
        "has_inner": True,
        "constraint_type": constraint_type,
        "constraint_ratio": constraint_ratio,
        "inner_count": len(inner_shapes),
        "available_area_ratio": allowed_region.area / outer_area
    }


def optimized_packing_layout(
    pages: List[PageSpec],
    allowed_region: MultiPolygon,
    nominal_height_mm: float,
    gap_mm: float = 0.5,
    max_attempts: int = 1000,
    size_flexibility: float = 0.1,  # Allow 10% size variation
    prioritize_space_filling: bool = True,
    outer_shape: Optional[MultiPolygon] = None,
    inner_shapes: Optional[List[MultiPolygon]] = None
) -> List[Placement]:
    """
    Advanced packing algorithm that optimizes space utilization.
    
    Args:
        pages: List of page specifications
        allowed_region: Available region for placement
        nominal_height_mm: Base page height
        gap_mm: Minimum gap between pages
        max_attempts: Maximum placement attempts per page
        size_flexibility: How much page sizes can vary (0.0 = no variation, 1.0 = 100% variation)
        prioritize_space_filling: Whether to prioritize filling space over uniform sizing
        outer_shape: Optional outer shape for constraint analysis
        inner_shapes: Optional inner shapes for constraint analysis
    """
    if not pages or allowed_region.is_empty:
        return []
    
    logging.info(f"Starting optimized packing for {len(pages)} pages")
    logging.info(f"Available area: {allowed_region.area:.2f} mm²")
    
    # Analyze shape characteristics
    shape_chars = analyze_shape_characteristics(allowed_region)
    logging.info(f"Shape type: {shape_chars['shape_type']}, rectangularity: {shape_chars['rectangularity']:.2f}")
    
    # Analyze inner constraints if provided
    inner_constraints = None
    if outer_shape is not None and inner_shapes is not None:
        inner_constraints = analyze_inner_constraints(outer_shape, inner_shapes, allowed_region)
        logging.info(f"Inner constraints: {inner_constraints['constraint_type']}, "
                    f"available area: {inner_constraints['available_area_ratio']:.1%}")
    
    placements: List[Placement] = []
    failed_pages = []
    
    # Adjust packing strategy based on constraints
    if inner_constraints and inner_constraints["constraint_type"] == "central":
        # For central inner shapes, prioritize ring/annular packing
        size_flexibility *= 1.2  # Allow more size variation
        max_attempts = int(max_attempts * 1.5)  # Try more positions
    elif shape_chars["shape_type"] == "complex":
        # For complex shapes, use more flexible sizing
        size_flexibility *= 1.1
    
    # Calculate base page sizes
    base_sizes = []
    for page in pages:
        width_mm = page.aspect_ratio * nominal_height_mm
        base_sizes.append((width_mm, nominal_height_mm))
    
    # Sort pages by size (largest first for better packing)
    page_indices = list(range(len(pages)))
    if prioritize_space_filling:
        page_indices.sort(key=lambda i: base_sizes[i][0] * base_sizes[i][1], reverse=True)
    
    for page_idx in page_indices:
        page = pages[page_idx]
        base_width, base_height = base_sizes[page_idx]
        placed = False
        
        # Try different size variations
        size_variations = []
        if size_flexibility > 0:
            # Create size variations
            for scale in [1.0, 0.9, 1.1, 0.8, 1.2, 0.7, 1.3]:
                if abs(scale - 1.0) <= size_flexibility:
                    var_height = base_height * scale
                    var_width = page.aspect_ratio * var_height
                    size_variations.append((var_width, var_height, scale))
        else:
            size_variations = [(base_width, base_height, 1.0)]
        
        # Try each size variation
        for width_mm, height_mm, scale in size_variations:
            if placed:
                break
                
            # Generate candidate positions for this size
            candidates = generate_candidate_positions(
                allowed_region, width_mm, height_mm, gap_mm, 
                sample_density=25 if shape_chars["shape_type"] == "complex" else 20,
                shape_characteristics=shape_chars
            )
            
            # Shuffle candidates for better distribution
            random.shuffle(candidates)
            
            # Try each candidate position
            for x, y in candidates[:max_attempts]:
                if check_placement_collision(x, y, width_mm, height_mm, placements, gap_mm):
                    continue
                
                # Place the page
                placement = Placement(
                    page_global_index=page_idx,
                    doc_index=page.doc_index,
                    page_index=page.page_index,
                    center_xy_mm=(x, y),
                    width_mm=width_mm,
                    height_mm=height_mm,
                    rotation_deg=0.0,
                )
                placements.append(placement)
                placed = True
                
                if scale != 1.0:
                    logging.debug(f"Page {page_idx} scaled by {scale:.2f}x for better fit")
                break
        
        if not placed:
            failed_pages.append(page_idx)
            logging.warning(f"Could not place page {page_idx}")
    
    # Calculate final statistics
    utilization = calculate_space_utilization(placements, allowed_region)
    logging.info(f"Optimized packing results:")
    logging.info(f"  Placed: {len(placements)}/{len(pages)} pages ({len(placements)/len(pages)*100:.1f}%)")
    logging.info(f"  Space utilization: {utilization:.1%}")
    logging.info(f"  Failed pages: {len(failed_pages)}")
    
    return placements


def hybrid_packing_layout(
    pages: List[PageSpec],
    allowed_region: MultiPolygon,
    nominal_height_mm: float,
    gap_mm: float = 0.5,
    grid_first: bool = True
) -> List[Placement]:
    """
    Hybrid approach: start with grid layout, then optimize with advanced packing.
    """
    logging.info("Using hybrid packing approach")
    
    if grid_first:
        # Start with traditional grid layout
        from .layout import plan_layout_any_shape
        initial_placements = plan_layout_any_shape(
            pages, allowed_region, nominal_height_mm, gap_mm
        )
        
        # Check if we got all pages placed
        if len(initial_placements) >= len(pages):
            logging.info("Grid layout successfully placed all pages")
            return initial_placements
        
        logging.info(f"Grid layout placed {len(initial_placements)}/{len(pages)} pages")
        logging.info("Switching to optimized packing for remaining pages")
    
    # Use optimized packing for all pages or remaining pages
    return optimized_packing_layout(
        pages, allowed_region, nominal_height_mm, gap_mm,
        prioritize_space_filling=True
    )


def adaptive_size_packing(
    pages: List[PageSpec],
    allowed_region: MultiPolygon,
    target_fill_ratio: float = 0.85,
    gap_mm: float = 0.5,
    max_iterations: int = 10
) -> List[Placement]:
    """
    Adaptively adjust page sizes to achieve target fill ratio.
    """
    logging.info(f"Adaptive packing targeting {target_fill_ratio:.1%} fill ratio")
    
    # Binary search for optimal page size
    min_height = 0.5  # mm
    max_height = 50.0  # mm
    best_placements = []
    best_utilization = 0.0
    
    for iteration in range(max_iterations):
        test_height = (min_height + max_height) / 2
        
        placements = optimized_packing_layout(
            pages, allowed_region, test_height, gap_mm,
            size_flexibility=0.15,  # Allow 15% size variation
            prioritize_space_filling=True
        )
        
        utilization = calculate_space_utilization(placements, allowed_region)
        pages_placed_ratio = len(placements) / len(pages)
        
        logging.info(f"Iteration {iteration + 1}: height={test_height:.2f}mm, "
                    f"utilization={utilization:.1%}, placed={pages_placed_ratio:.1%}")
        
        # Score combines utilization and page placement success
        score = utilization * 0.7 + pages_placed_ratio * 0.3
        
        if score > best_utilization:
            best_placements = placements
            best_utilization = score
        
        # Adjust search range
        if len(placements) < len(pages):
            # Not all pages fit, try smaller pages
            max_height = test_height
        elif utilization < target_fill_ratio:
            # Pages fit but utilization is low, try larger pages
            min_height = test_height
        else:
            # Good balance, refine around this size
            if utilization > target_fill_ratio:
                min_height = test_height
            else:
                max_height = test_height
    
    final_utilization = calculate_space_utilization(best_placements, allowed_region)
    logging.info(f"Adaptive packing final result: {final_utilization:.1%} utilization, "
                f"{len(best_placements)}/{len(pages)} pages placed")
    
    return best_placements