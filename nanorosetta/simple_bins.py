"""
Simple bin-based layout with calculated circle envelope.

This module implements a simplified approach where:
- Each PDF page gets its own fixed-size bin (e.g., 2000x2000 pixels)
- A circle envelope is calculated to optimally fit all bins
- Simple packing algorithm places bins within the circle
"""

from __future__ import annotations

import math
import logging
from typing import List, Tuple
from dataclasses import dataclass

from shapely.geometry import Point
from .layout import PageSpec, Placement


@dataclass
class BinPlacement:
    """Represents a bin placement within the circle envelope."""
    center_x: float
    center_y: float
    bin_width: int
    bin_height: int
    page_spec: PageSpec


def calculate_circle_radius(total_bins: int, bin_width: int, bin_height: int) -> float:
    """
    Calculate the radius of a circle needed to contain all bins.
    
    Args:
        total_bins: Number of bins to pack
        bin_width: Width of each bin in pixels
        bin_height: Height of each bin in pixels
    
    Returns:
        Circle radius in pixels
    """
    # Calculate total area needed
    bin_area = bin_width * bin_height
    total_area = bin_area * total_bins
    
    # Add some packing efficiency factor (bins won't pack perfectly)
    packing_efficiency = 0.85  # Assume 85% efficiency for circle packing
    required_area = total_area / packing_efficiency
    
    # Calculate circle radius from area
    radius = math.sqrt(required_area / math.pi)
    
    logging.info(f"Calculated circle radius: {radius:.0f}px for {total_bins} bins "
                f"({bin_width}x{bin_height}px each)")
    
    return radius


def pack_bins_in_circle(pages: List[PageSpec], bin_width: int, bin_height: int) -> Tuple[List[BinPlacement], float]:
    """
    Pack bins in a circle using a simple spiral placement algorithm.
    
    Args:
        pages: List of pages to place
        bin_width: Width of each bin in pixels
        bin_height: Height of each bin in pixels
    
    Returns:
        Tuple of (bin_placements, circle_radius)
    """
    total_bins = len(pages)
    circle_radius = calculate_circle_radius(total_bins, bin_width, bin_height)
    
    bin_placements = []
    
    # Simple spiral packing algorithm
    angle_step = 2 * math.pi / max(8, int(math.sqrt(total_bins)))  # Adaptive angle step
    radius_step = max(bin_width, bin_height) * 0.8  # Step between spiral arms
    
    current_radius = radius_step
    current_angle = 0
    
    for i, page in enumerate(pages):
        # Find position on spiral
        while True:
            x = current_radius * math.cos(current_angle)
            y = current_radius * math.sin(current_angle)
            
            # Check if bin fits within circle
            bin_corner_distance = math.sqrt(
                (abs(x) + bin_width/2)**2 + (abs(y) + bin_height/2)**2
            )
            
            if bin_corner_distance <= circle_radius:
                # Position is valid
                bin_placements.append(BinPlacement(
                    center_x=x,
                    center_y=y,
                    bin_width=bin_width,
                    bin_height=bin_height,
                    page_spec=page
                ))
                break
            
            # Move to next position on spiral
            current_angle += angle_step
            if current_angle >= 2 * math.pi:
                current_angle = 0
                current_radius += radius_step
                
                # Safety check to prevent infinite loop
                if current_radius > circle_radius * 2:
                    logging.warning(f"Spiral packing failed for bin {i}, using fallback position")
                    bin_placements.append(BinPlacement(
                        center_x=0, center_y=0,  # Fallback to center
                        bin_width=bin_width,
                        bin_height=bin_height,
                        page_spec=page
                    ))
                    break
    
    logging.info(f"Packed {len(bin_placements)} bins in circle (radius: {circle_radius:.0f}px)")
    return bin_placements, circle_radius


def simple_bin_layout(pages: List[PageSpec], bin_width: int, bin_height: int, dpi: int = 300) -> Tuple[List[Placement], float, float]:
    """
    Create layout using simple bin approach with calculated circle envelope.
    
    Args:
        pages: List of pages to layout
        bin_width: Width of each bin in pixels
        bin_height: Height of each bin in pixels
    
    Returns:
        Tuple of (placements, canvas_width_px, canvas_height_px)
    """
    logging.info(f"Starting simple bin layout: {len(pages)} pages, {bin_width}x{bin_height}px bins")
    
    # Pack bins in circle
    bin_placements, circle_radius = pack_bins_in_circle(pages, bin_width, bin_height)
    
    # Convert bin placements to standard Placement objects
    placements = []
    for i, bin_placement in enumerate(bin_placements):
        # Convert pixel coordinates to mm for compatibility with existing render system
        center_x_mm = bin_placement.center_x * 25.4 / dpi  # Use provided DPI for mm conversion
        center_y_mm = bin_placement.center_y * 25.4 / dpi
        width_mm = bin_placement.bin_width * 25.4 / dpi
        height_mm = bin_placement.bin_height * 25.4 / dpi
        
        placement = Placement(
            page_global_index=i,  # Global index for this placement
            doc_index=bin_placement.page_spec.doc_index,
            page_index=bin_placement.page_spec.page_index,
            center_xy_mm=(center_x_mm, center_y_mm),
            width_mm=width_mm,
            height_mm=height_mm,
            rotation_deg=0.0  # No rotation in simple mode
        )
        placements.append(placement)
    
    # Calculate canvas size (circle diameter plus some margin)
    margin_px = max(bin_width, bin_height) * 0.1  # 10% margin
    canvas_size_px = (circle_radius * 2) + (margin_px * 2)
    canvas_width_mm = canvas_size_px * 25.4 / dpi  # Convert to mm using provided DPI
    canvas_height_mm = canvas_width_mm  # Square canvas
    
    logging.info(f"Simple bin layout complete: {len(placements)} placements, "
                f"canvas: {canvas_width_mm:.1f}x{canvas_height_mm:.1f}mm")
    
    return placements, canvas_width_mm, canvas_height_mm