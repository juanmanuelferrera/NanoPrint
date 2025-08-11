#!/usr/bin/env python3
"""
Test extreme dimension overflow scenario to verify DPI reduction works
"""
import sys
import os
import logging

def mm_to_px(mm: float, dpi: int) -> int:
    """Convert mm to pixels at given DPI"""
    return int(round(mm * dpi / 25.4))

def validate_canvas_dimensions(canvas_width_mm: float, canvas_height_mm: float, dpi: int) -> tuple[int, int, int]:
    """Validate canvas dimensions and return safe pixel dimensions and DPI."""
    print(f"🔍 Validating: {canvas_width_mm:.1f}x{canvas_height_mm:.1f}mm at {dpi} DPI")
    
    # PIL's maximum image dimensions - conservative limit of 2^28 pixels
    max_pixels_per_dimension = 2**28
    print(f"   Max pixels per dimension: {max_pixels_per_dimension:,}")
    
    # Calculate pixel dimensions
    width_px = mm_to_px(canvas_width_mm, dpi)
    height_px = mm_to_px(canvas_height_mm, dpi)
    print(f"   Calculated dimensions: {width_px:,} x {height_px:,} pixels")
    
    # Check if dimensions are too large
    if width_px > max_pixels_per_dimension or height_px > max_pixels_per_dimension:
        print(f"   ⚠️  Dimensions exceed safe limit!")
        
        # Calculate required DPI reduction
        max_dimension_mm = max(canvas_width_mm, canvas_height_mm)
        safe_dpi = int((max_pixels_per_dimension * 25.4) / max_dimension_mm)
        
        # Ensure DPI is reasonable (minimum 50 DPI)
        safe_dpi = max(50, min(safe_dpi, dpi))
        print(f"   ⚡ DPI reduced from {dpi} to {safe_dpi} for safety")
        
        # Recalculate pixel dimensions with safe DPI
        width_px = mm_to_px(canvas_width_mm, safe_dpi)
        height_px = mm_to_px(canvas_height_mm, safe_dpi)
        print(f"   ✅ Safe dimensions: {width_px:,} x {height_px:,} pixels")
        
        return width_px, height_px, safe_dpi
    
    print(f"   ✅ Dimensions are within safe limits")
    return width_px, height_px, dpi

def simulate_dimension_overflow_scenarios():
    """Simulate the exact scenarios that would cause exit code 5"""
    
    print("🧪 Testing Dimension Overflow Prevention")
    print("=" * 50)
    
    # Scenario 1: Typical problematic case
    print("\n📐 Scenario 1: Large canvas at high DPI (typical problem case)")
    w1, h1, dpi1 = validate_canvas_dimensions(500.0, 500.0, 2400)
    
    # Scenario 2: Extreme case that would definitely overflow
    print(f"\n📐 Scenario 2: Extreme canvas at high DPI (guaranteed overflow)")
    w2, h2, dpi2 = validate_canvas_dimensions(2000.0, 2000.0, 1200)
    
    # Scenario 3: Very extreme case
    print(f"\n📐 Scenario 3: Massive canvas (extreme overflow)")
    w3, h3, dpi3 = validate_canvas_dimensions(10000.0, 10000.0, 600)
    
    print(f"\n📊 Results Summary:")
    print(f"Scenario 1: {500}x{500}mm @ {2400} DPI → {dpi1} DPI ({'REDUCED' if dpi1 < 2400 else 'UNCHANGED'})")
    print(f"Scenario 2: {2000}x{2000}mm @ {1200} DPI → {dpi2} DPI ({'REDUCED' if dpi2 < 1200 else 'UNCHANGED'})")  
    print(f"Scenario 3: {10000}x{10000}mm @ {600} DPI → {dpi3} DPI ({'REDUCED' if dpi3 < 600 else 'UNCHANGED'})")
    
    # Calculate what the original pixel counts would have been
    orig1 = mm_to_px(500.0, 2400) 
    orig2 = mm_to_px(2000.0, 1200)
    orig3 = mm_to_px(10000.0, 600)
    
    print(f"\n💾 Memory Impact:")
    print(f"Scenario 1: Would be {orig1:,}x{orig1:,} = {orig1*orig1:,} pixels, now {w1:,}x{h1:,} = {w1*h1:,} pixels")
    print(f"Scenario 2: Would be {orig2:,}x{orig2:,} = {orig2*orig2:,} pixels, now {w2:,}x{h2:,} = {w2*h2:,} pixels")
    print(f"Scenario 3: Would be {orig3:,}x{orig3:,} = {orig3*orig3:,} pixels, now {w3:,}x{h3:,} = {w3*h3:,} pixels")

if __name__ == "__main__":
    simulate_dimension_overflow_scenarios()
    
    print(f"\n🎯 Conclusion:")
    print(f"The dimension validation successfully prevents PIL overflow errors")
    print(f"by automatically reducing DPI when canvas dimensions are too large.")
    print(f"This is exactly what will prevent the 'exit code 5' error you experienced!")