#!/usr/bin/env python3
"""
Debug the placement coordinates to see what's happening.
"""

import sys
from pathlib import Path
sys.path.insert(0, '.')

from nanofiche.core import NanoFichePacker, EnvelopeShape, EnvelopeSpec
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def debug_placement():
    """Debug placement coordinates for a small grid."""
    print("Debugging Placement Coordinates")
    print("=" * 40)
    
    # Use small numbers for easy debugging
    bin_width = 100  # Small for easy math
    bin_height = 100
    num_bins = 12    # 3x4 or 4x3 grid
    
    print(f"Bin dimensions: {bin_width}x{bin_height}")
    print(f"Number of bins: {num_bins}")
    
    # Create packer
    packer = NanoFichePacker(bin_width, bin_height)
    
    # Test rectangle
    envelope_spec = EnvelopeSpec(EnvelopeShape.RECTANGLE, aspect_ratio=1.0)
    result = packer.pack_rectangle(num_bins, envelope_spec)
    
    print(f"\\nGrid result:")
    print(f"  Rows: {result.rows}, Columns: {result.columns}")
    print(f"  Canvas: {result.canvas_width}x{result.canvas_height}")
    print(f"  Total placements: {len(result.placements)}")
    
    print(f"\\nPlacement coordinates (should be top-left to bottom-right):")
    for i, (x, y) in enumerate(result.placements[:num_bins]):
        row = i // result.columns
        col = i % result.columns
        expected_x = col * bin_width
        expected_y = row * bin_height
        
        status = "✅" if (x == expected_x and y == expected_y) else "❌"
        print(f"  Image {i:2d}: pos=({x:3d},{y:3d}) expected=({expected_x:3d},{expected_y:3d}) {status}")
        print(f"           row={row}, col={col}")
    
    # Test the actual placement pattern
    print(f"\\nExpected grid pattern for {result.rows}x{result.columns}:")
    for row in range(result.rows):
        line = ""
        for col in range(result.columns):
            i = row * result.columns + col
            if i < num_bins:
                line += f"[{i:2d}]"
            else:
                line += "[  ]"
        print(f"  Row {row}: {line}")

def debug_large_case():
    """Debug a larger case to see the pattern."""
    print("\\n" + "=" * 40)
    print("Debugging Larger Case (100 images)")
    print("=" * 40)
    
    bin_width = 200
    bin_height = 200  
    num_bins = 100   # Should be 10x10
    
    packer = NanoFichePacker(bin_width, bin_height)
    envelope_spec = EnvelopeSpec(EnvelopeShape.SQUARE)
    result = packer.pack_rectangle(num_bins, envelope_spec)
    
    print(f"Grid: {result.rows}x{result.columns}")
    print(f"Canvas: {result.canvas_width}x{result.canvas_height}")
    
    # Check first few and last few coordinates
    print(f"\\nFirst 10 placements:")
    for i in range(min(10, len(result.placements))):
        x, y = result.placements[i]
        row = i // result.columns
        col = i % result.columns
        print(f"  Image {i:2d}: pos=({x:4d},{y:4d}) grid=({row},{col})")
    
    print(f"\\nLast 10 placements:")
    start_idx = max(0, min(num_bins, len(result.placements)) - 10)
    for i in range(start_idx, min(num_bins, len(result.placements))):
        x, y = result.placements[i]
        row = i // result.columns
        col = i % result.columns
        print(f"  Image {i:2d}: pos=({x:4d},{y:4d}) grid=({row},{col})")

def main():
    debug_placement()
    debug_large_case()
    
    print("\\n" + "=" * 40)
    print("If coordinates look correct here, the issue is in the renderer!")

if __name__ == "__main__":
    main()