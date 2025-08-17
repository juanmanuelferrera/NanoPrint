#!/usr/bin/env python3
"""
Test script for NanoFiche Image Prep.

Creates sample images and tests the core functionality.
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

# Add project to path
sys.path.insert(0, '.')

from nanofiche.core import NanoFichePacker, EnvelopeShape, EnvelopeSpec


def create_test_images(output_dir: Path, num_images: int = 10, max_width: int = 1700, max_height: int = 2200):
    """Create test images for NanoFiche testing."""
    output_dir.mkdir(exist_ok=True)
    
    colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'cyan']
    
    for i in range(num_images):
        # Random size within constraints
        width = random.randint(max_width//2, max_width)
        height = random.randint(max_height//2, max_height)
        
        # Create image with colored background and text
        img = Image.new('RGB', (width, height), color=random.choice(colors))
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            # Try to use a system font, fallback to default
            font = ImageFont.load_default()
        except:
            font = None
        
        text = f"Image {i+1:02d}\\n{width}x{height}"
        
        # Calculate text position (center)
        if font:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        else:
            text_width, text_height = 100, 50  # Estimate
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        # Add border
        draw.rectangle([0, 0, width-1, height-1], outline='black', width=2)
        
        # Save image
        img_path = output_dir / f"test_image_{i+1:02d}.png"
        img.save(img_path)
        print(f"Created: {img_path}")


def test_packing_algorithms():
    """Test the core packing algorithms."""
    print("\\nTesting NanoFiche packing algorithms...")
    
    # Create test images
    test_dir = Path("test_images")
    create_test_images(test_dir, num_images=25)
    
    # Initialize packer
    packer = NanoFichePacker(bin_width=1800, bin_height=2300)
    
    # Validate images
    print("\\nValidating test images...")
    image_bins, errors = packer.validate_images(test_dir)
    
    print(f"Valid images: {len(image_bins)}")
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f"  - {error}")
    
    if not image_bins:
        print("No valid images found!")
        return
    
    # Test different envelope shapes
    shapes_to_test = [
        ("Square", EnvelopeSpec(EnvelopeShape.SQUARE)),
        ("Rectangle 1.29:1", EnvelopeSpec(EnvelopeShape.RECTANGLE, aspect_ratio=1.29)),
        ("Circle", EnvelopeSpec(EnvelopeShape.CIRCLE)),
        ("Ellipse 1.5:1", EnvelopeSpec(EnvelopeShape.ELLIPSE, aspect_ratio=1.5)),
    ]
    
    for shape_name, envelope_spec in shapes_to_test:
        print(f"\\nTesting {shape_name}:")
        try:
            result = packer.pack_bins(image_bins, envelope_spec)
            
            print(f"  Rows: {result.rows}, Columns: {result.columns}")
            print(f"  Canvas: {result.canvas_width}x{result.canvas_height}")
            print(f"  Envelope: {result.envelope_width:.1f}x{result.envelope_height:.1f}")
            print(f"  Bins placed: {result.bins_placed}/{len(image_bins)}")
            print(f"  Efficiency: {result.efficiency:.1%}")
            
        except Exception as e:
            print(f"  Error: {e}")


def main():
    """Main test function."""
    print("NanoFiche Image Prep - Test Script")
    print("=" * 40)
    
    # Test core functionality
    test_packing_algorithms()
    
    print("\\nTest completed!")
    print("\\nTo test the GUI:")
    print("  python nanofiche.py")


if __name__ == "__main__":
    main()