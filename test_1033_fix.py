#!/usr/bin/env python3
"""
Test the fixed algorithm with 1,033 images (matching your scenario).
"""

import sys
from pathlib import Path
sys.path.insert(0, '.')

from nanofiche.core import NanoFichePacker, EnvelopeShape, EnvelopeSpec
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

def test_1033_images():
    """Test with 1,033 images to match your scenario."""
    print("Testing NanoFiche with 1,033 images")
    print("=" * 50)
    
    # Use your exact scenario
    bin_width = 2198  # Your bin width  
    bin_height = 2198  # Your bin height
    num_bins = 1033   # Your number of images
    
    print(f"Bin dimensions: {bin_width}x{bin_height}")
    print(f"Number of bins: {num_bins}")
    
    # Create packer
    packer = NanoFichePacker(bin_width, bin_height)
    
    # Test different envelope configurations
    test_cases = [
        ("Square", EnvelopeSpec(EnvelopeShape.SQUARE)),
        ("Rectangle 1.29:1", EnvelopeSpec(EnvelopeShape.RECTANGLE, aspect_ratio=1.29)),
        ("Rectangle 1.0:1", EnvelopeSpec(EnvelopeShape.RECTANGLE, aspect_ratio=1.0)),
    ]
    
    for name, envelope_spec in test_cases:
        print(f"\\nTesting {name}:")
        print("-" * 30)
        
        try:
            result = packer.pack_rectangle(num_bins, envelope_spec)
            
            print(f"Grid: {result.rows} rows × {result.columns} columns")
            print(f"Total slots: {result.total_bins}")
            print(f"Canvas: {result.canvas_width:,} × {result.canvas_height:,} pixels")
            print(f"Canvas aspect: {result.canvas_width/result.canvas_height:.3f}")
            print(f"Bins placed: {result.bins_placed}")
            print(f"Efficiency: {result.efficiency:.1%}")
            
            # Check if this matches expected results
            if name == "Rectangle 1.29:1":
                # Your expected: 25 rows × 40 columns = 1000 total
                # But we have 1033, so should be close
                expected_rows = 32  # sqrt(1033) ≈ 32
                expected_cols = 33  # ceil(1033/32) = 33
                print(f"Expected around: {expected_rows}×{expected_cols} = {expected_rows*expected_cols}")
                
                # Check canvas size reasonableness
                expected_canvas_w = expected_cols * bin_width  # ~72,534
                expected_canvas_h = expected_rows * bin_height  # ~70,336
                print(f"Expected canvas: ~{expected_canvas_w:,}×{expected_canvas_h:,}")
                
                # Verify it's reasonable
                if result.canvas_width > 100000 or result.canvas_height > 100000:
                    print("⚠️  WARNING: Canvas size seems too large!")
                else:
                    print("✅ Canvas size looks reasonable")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

def main():
    test_1033_images()
    
    print("\\n" + "="*50)
    print("Test completed!")
    print("\\nExpected results for 1,033 images with 2198×2198 bins:")
    print("- Grid should be around 32×33 (1,056 slots)")
    print("- Canvas should be around 72,534×70,336 pixels")
    print("- Only 1 image placed suggests a placement bug")

if __name__ == "__main__":
    main()