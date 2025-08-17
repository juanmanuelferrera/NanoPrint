#!/usr/bin/env python3
"""
Test the FULL renderer (not preview) to see the placement issue.
"""

import sys
from pathlib import Path
sys.path.insert(0, '.')

from nanofiche.core import NanoFichePacker, EnvelopeShape, EnvelopeSpec, ImageBin
from nanofiche.renderer import NanoFicheRenderer
from PIL import Image, ImageDraw
import logging
from datetime import datetime

# Enable debug logging
logging.basicConfig(level=logging.INFO)

def create_test_images(count=9):
    """Create simple test images with numbers."""
    test_dir = Path("test_full_render")
    test_dir.mkdir(exist_ok=True)
    
    image_bins = []
    
    for i in range(count):
        # Create small image with number
        img = Image.new('RGB', (150, 150), color='lightgreen')
        draw = ImageDraw.Draw(img)
        
        # Draw big number in center
        font_size = 80
        text = str(i)
        # Get text size (approximate)
        text_width = len(text) * font_size // 2
        text_height = font_size
        
        x = (150 - text_width) // 2
        y = (150 - text_height) // 2
        
        draw.text((x, y), text, fill='black')
        
        # Add border
        draw.rectangle([0, 0, 149, 149], outline='blue', width=3)
        
        # Save
        img_path = test_dir / f"full_test_{i:02d}.png"
        img.save(img_path)
        
        # Create ImageBin
        image_bins.append(ImageBin(img_path, 150, 150, i))
    
    return image_bins

def test_full_renderer():
    """Test FULL TIFF renderer (not preview) with known placement."""
    print("Testing FULL TIFF Renderer with 9 images (3x3 grid)")
    print("=" * 60)
    
    # Create test images
    image_bins = create_test_images(9)
    
    # Create packer and get result
    packer = NanoFichePacker(bin_width=200, bin_height=200)
    envelope_spec = EnvelopeSpec(EnvelopeShape.SQUARE)
    packing_result = packer.pack_rectangle(9, envelope_spec)
    
    print(f"Packing result:")
    print(f"  Grid: {packing_result.rows}x{packing_result.columns}")
    print(f"  Canvas: {packing_result.canvas_width}x{packing_result.canvas_height}")
    print(f"  Placements: {len(packing_result.placements)}")
    
    # Create renderer and generate FULL TIFF (not preview!)
    renderer = NanoFicheRenderer()
    output_path = Path("test_full_render_output.tif")
    log_path = Path("test_full_render_output.log")
    
    print(f"\\nGenerating FULL TIFF render to: {output_path}")
    try:
        # Use the generate_full_tiff method that was having issues
        renderer.generate_full_tiff(
            image_bins, 
            packing_result, 
            output_path, 
            log_path, 
            "test_full_render", 
            approved=True
        )
        print(f"✅ Full TIFF render completed!")
        print(f"\\nCheck the output file: {output_path}")
        print(f"Check the log file: {log_path}")
        print(f"\\nIf you only see ONE image, there's a bug in generate_full_tiff()!")
        print(f"If you see all 9 images in a 3x3 grid, the bug is fixed!")
        
    except Exception as e:
        print(f"❌ Full TIFF render failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    test_full_renderer()

if __name__ == "__main__":
    main()