#!/usr/bin/env python3
"""Test script to diagnose image dimension issues."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from nanorosetta.units import mm_to_px
from nanorosetta.render import validate_canvas_dimensions, compute_dpi_for_target_mb

def test_dimensions():
    """Test various canvas dimensions and DPI combinations."""
    
    print("=== Image Dimension Calculator ===\n")
    
    # Test cases
    test_cases = [
        (100, 100, 1200),    # Small canvas, high DPI
        (500, 500, 1200),    # Medium canvas, high DPI
        (1000, 1000, 1200),  # Large canvas, high DPI
        (2000, 2000, 1200),  # Very large canvas, high DPI
        (100, 100, 2400),    # Small canvas, very high DPI
        (500, 500, 2400),    # Medium canvas, very high DPI
        (1000, 1000, 2400),  # Large canvas, very high DPI
        (2000, 2000, 2400),  # Very large canvas, very high DPI
    ]
    
    for width_mm, height_mm, dpi in test_cases:
        print(f"Canvas: {width_mm}mm x {height_mm}mm, Target DPI: {dpi}")
        
        # Calculate original pixel dimensions
        orig_width_px = mm_to_px(width_mm, dpi)
        orig_height_px = mm_to_px(height_mm, dpi)
        
        # Validate dimensions
        safe_width_px, safe_height_px, safe_dpi = validate_canvas_dimensions(width_mm, height_mm, dpi)
        
        print(f"  Original pixels: {orig_width_px:,} x {orig_height_px:,}")
        print(f"  Safe pixels: {safe_width_px:,} x {safe_height_px:,}")
        print(f"  Safe DPI: {safe_dpi}")
        
        if safe_dpi < dpi:
            print(f"  ⚠️  DPI reduced from {dpi} to {safe_dpi}")
        else:
            print(f"  ✅ DPI unchanged")
        
        print()
    
    print("=== Target MB Calculator ===\n")
    
    # Test target MB calculations
    mb_test_cases = [
        (100, 100, 100),     # Small canvas, 100MB target
        (500, 500, 500),     # Medium canvas, 500MB target
        (1000, 1000, 900),   # Large canvas, 900MB target
        (2000, 2000, 900),   # Very large canvas, 900MB target
    ]
    
    for width_mm, height_mm, target_mb in mb_test_cases:
        print(f"Canvas: {width_mm}mm x {height_mm}mm, Target: {target_mb}MB")
        
        dpi = compute_dpi_for_target_mb(width_mm, height_mm, target_mb)
        width_px = mm_to_px(width_mm, dpi)
        height_px = mm_to_px(height_mm, dpi)
        
        print(f"  Calculated DPI: {dpi}")
        print(f"  Pixel dimensions: {width_px:,} x {height_px:,}")
        print(f"  Total pixels: {width_px * height_px:,}")
        print()

if __name__ == "__main__":
    test_dimensions()
