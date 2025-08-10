#!/usr/bin/env python3
"""Test SVG parsing with different element types."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from nanorosetta.geometry import parse_svg_path, diagnose_svg_file

def test_svg_parsing():
    """Test SVG parsing with sample files."""
    
    # Test with the problematic file
    problematic_file = "E:/Dropbox/NanoArchival/Gita/Jagan/idcircle.svg"
    
    if os.path.exists(problematic_file):
        print("=== Diagnosing problematic SVG file ===")
        print(diagnose_svg_file(problematic_file))
        
        try:
            print("\n=== Attempting to parse ===")
            result = parse_svg_path(problematic_file)
            print(f"Success! Found {len(result.geoms)} polygon(s)")
            print(f"Total area: {result.area:.2f}")
        except Exception as e:
            print(f"Parse failed: {e}")
    else:
        print(f"File not found: {problematic_file}")
    
    # Test with our sample files
    sample_files = [
        "examples/outer_rect.svg",
        "examples/inner_circle.svg"
    ]
    
    for sample_file in sample_files:
        if os.path.exists(sample_file):
            print(f"\n=== Testing {sample_file} ===")
            print(diagnose_svg_file(sample_file))
            
            try:
                result = parse_svg_path(sample_file)
                print(f"Success! Found {len(result.geoms)} polygon(s)")
                print(f"Total area: {result.area:.2f}")
            except Exception as e:
                print(f"Parse failed: {e}")
        else:
            print(f"Sample file not found: {sample_file}")

if __name__ == "__main__":
    test_svg_parsing()
