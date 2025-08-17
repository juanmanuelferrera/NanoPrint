#!/usr/bin/env python3
"""
Test the renderer with a small known case to see what happens.
"""

import sys
from pathlib import Path
sys.path.insert(0, '.')

from nanofiche.core import NanoFichePacker, EnvelopeShape, EnvelopeSpec, ImageBin
from nanofiche.renderer import NanoFicheRenderer
from PIL import Image, ImageDraw
import logging

# Enable debug logging
logging.basicConfig(level=logging.INFO)

def create_test_images(count=9):
    """Create simple test images with numbers."""
    test_dir = Path("test_render")
    test_dir.mkdir(exist_ok=True)
    
    image_bins = []
    
    for i in range(count):
        # Create small image with number
        img = Image.new('RGB', (150, 150), color='lightblue')
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
        draw.rectangle([0, 0, 149, 149], outline='red', width=2)
        
        # Save
        img_path = test_dir / f"test_{i:02d}.png"
        img.save(img_path)
        
        # Create ImageBin
        image_bins.append(ImageBin(img_path, 150, 150, i))
    
    return image_bins

def test_renderer():
    """Test renderer with known placement."""
    print("Testing Renderer with 9 images (3x3 grid)")
    print("=" * 50)
    
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
    
    print(f"\\nFirst few placements:")
    for i in range(min(9, len(packing_result.placements))):
        x, y = packing_result.placements[i]
        print(f"  Image {i}: ({x}, {y})")
    
    # Create renderer and generate preview
    renderer = NanoFicheRenderer()
    output_path = Path("test_render_output.tif")
    
    print(f"\\nGenerating test render to: {output_path}")
    try:
        renderer.generate_preview(image_bins, packing_result, output_path, max_dimension=1000)
        print(f"✅ Render completed!")
        print(f"\\nCheck the output file: {output_path}")
        print(f"You should see a 3x3 grid with numbered images 0-8")
        print(f"If you only see one image, the placement logic has an issue.")
        
    except Exception as e:
        print(f"❌ Render failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    test_renderer()

if __name__ == "__main__":
    main()