#!/usr/bin/env python3
"""
Create comprehensive test files for NanoFiche Image Prep.

This script creates various test scenarios to thoroughly test the application.
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import random

def create_test_scenario(name: str, num_images: int, max_width: int, max_height: int, 
                        bin_width: int = 1800, bin_height: int = 2300):
    """Create a test scenario with specific parameters."""
    
    scenario_dir = Path(f"test_scenarios/{name}")
    scenario_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\\nCreating test scenario: {name}")
    print(f"  Images: {num_images}")
    print(f"  Max size: {max_width}x{max_height}")
    print(f"  Bin constraint: {bin_width}x{bin_height}")
    
    colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'cyan', 
              'brown', 'gray', 'navy', 'maroon', 'olive', 'teal', 'silver']
    
    valid_count = 0
    oversized_count = 0
    
    for i in range(num_images):
        # Create different sized images for variety
        if i < num_images * 0.7:  # 70% normal sized
            width = random.randint(max_width//2, max_width)
            height = random.randint(max_height//2, max_height)
        elif i < num_images * 0.9:  # 20% smaller
            width = random.randint(max_width//4, max_width//2)
            height = random.randint(max_height//4, max_height//2)
        else:  # 10% potentially oversized for testing validation
            width = random.randint(max_width, int(max_width * 1.2))
            height = random.randint(max_height, int(max_height * 1.2))
        
        # Check if oversized
        if width > bin_width or height > bin_height:
            oversized_count += 1
        else:
            valid_count += 1
        
        # Create image
        color = random.choice(colors)
        img = Image.new('RGB', (width, height), color=color)
        draw = ImageDraw.Draw(img)
        
        # Add text with scenario info
        font = ImageFont.load_default()
        text_lines = [
            f"Scenario: {name}",
            f"Image: {i+1:03d}/{num_images}",
            f"Size: {width}x{height}",
            f"Valid: {'YES' if width <= bin_width and height <= bin_height else 'NO'}"
        ]
        
        # Draw text
        y_offset = 10
        for line in text_lines:
            draw.text((10, y_offset), line, fill='white', font=font)
            y_offset += 20
        
        # Add border (red if oversized, green if valid)
        border_color = 'red' if width > bin_width or height > bin_height else 'green'
        draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=3)
        
        # Add corner markers
        corner_size = 20
        draw.rectangle([0, 0, corner_size, corner_size], fill=border_color)
        draw.rectangle([width-corner_size, 0, width, corner_size], fill=border_color)
        draw.rectangle([0, height-corner_size, corner_size, height], fill=border_color)
        draw.rectangle([width-corner_size, height-corner_size, width, height], fill=border_color)
        
        # Save with descriptive filename
        status = "VALID" if width <= bin_width and height <= bin_height else "OVERSIZED"
        filename = f"{i+1:03d}_{status}_{width}x{height}.png"
        img_path = scenario_dir / filename
        img.save(img_path)
    
    print(f"  Created: {num_images} images")
    print(f"  Valid: {valid_count}")
    print(f"  Oversized: {oversized_count}")
    print(f"  Location: {scenario_dir}")
    
    return scenario_dir, valid_count, oversized_count


def create_test_instructions():
    """Create a test instructions file."""
    instructions = """
# NanoFiche Image Prep - Test Instructions

## Test Scenarios Created

### 1. Small Test (test_scenarios/small_test/)
- **Purpose**: Quick testing with few images
- **Images**: 10 total (9 valid, 1 oversized for validation testing)
- **Best for**: Initial functionality testing

### 2. Medium Grid (test_scenarios/medium_grid/)  
- **Purpose**: Perfect grid layouts
- **Images**: 25 total (all valid)
- **Expected**: 5x5 grid for square/rectangle envelopes

### 3. Large Set (test_scenarios/large_set/)
- **Purpose**: Performance testing with many images
- **Images**: 100 total (90 valid, 10 oversized)
- **Best for**: Testing efficiency with larger datasets

### 4. Example 1000 (test_scenarios/example_1000/)
- **Purpose**: Matches your example specification
- **Images**: 1000 total (all valid)
- **Expected Results**: 25 rows × 40 columns for 1.29:1 rectangle

## How to Test

### Step 1: Launch Application
```bash
python nanofiche.py
```

### Step 2: Test Each Scenario
For each test scenario above:

1. **Project Name**: Enter descriptive name (e.g., "small_test_run1")
2. **Bin Dimensions**: 
   - Width (a): 1800
   - Height (b): 2300
3. **Envelope Shape**: Try different shapes:
   - Square (should create square-ish grids)
   - Rectangle 1.29:1 (matches your example)
   - Circle (spiral packing)
   - Ellipse 1.5:1 (elongated circular packing)
4. **Raster Folder**: Browse to test scenario folder
5. **Output Location**: Browse to desired output folder

### Step 3: Validate Results
1. Click "Validate & Calculate Layout"
2. Check that:
   - Valid image count matches expectations
   - Error messages show oversized images
   - Packing results show reasonable efficiency

### Step 4: Test Workflow
1. Click "Generate Preview" 
2. Check preview TIFF opens correctly
3. Try both "Approve" and "Reject" workflows
4. Verify log files are created with correct information

## Expected Results by Shape

### Square Envelope
- Should create square-ish grids
- Aspect ratio close to 1.0

### Rectangle 1.29:1  
- For 1000 images: ~25 rows × 40 columns
- Canvas aspect ratio should be close to 1.29

### Circle
- Circular boundary with spiral placement
- Slightly lower efficiency due to circular constraints

### Ellipse 1.5:1
- Elliptical boundary 
- Wider than circle packing

## Troubleshooting

### GUI Issues
- If GUI doesn't appear, check console for error messages
- Try running: `python -c "import tkinter; tkinter._test()"`

### Image Issues  
- Red-bordered images should show validation errors
- Green-bordered images should be accepted

### Memory Issues
- Start with small_test scenario first
- Large datasets may take time to process

## File Locations

All test files created in:
- `test_scenarios/small_test/` - 10 images
- `test_scenarios/medium_grid/` - 25 images  
- `test_scenarios/large_set/` - 100 images
- `test_scenarios/example_1000/` - 1000 images

Output will be saved to your chosen output directory with files like:
- `[project]_[timestamp]_preview.tif`
- `[project]_[timestamp]_full.tif` (if approved)
- `[project]_[timestamp]_full.log`
"""
    
    with open("TEST_INSTRUCTIONS.md", "w") as f:
        f.write(instructions)
    
    print("\\nTest instructions saved to: TEST_INSTRUCTIONS.md")


def main():
    """Create all test scenarios."""
    print("NanoFiche Image Prep - Test File Generator")
    print("=" * 50)
    
    # Create test scenarios
    scenarios = [
        ("small_test", 10, 1700, 2200),     # Quick test
        ("medium_grid", 25, 1700, 2200),   # Perfect 5x5 grid
        ("large_set", 100, 1700, 2200),    # Performance test
        ("example_1000", 1000, 1700, 2200) # Your example case
    ]
    
    total_images = 0
    for name, count, max_w, max_h in scenarios:
        scenario_dir, valid, oversized = create_test_scenario(name, count, max_w, max_h)
        total_images += count
    
    create_test_instructions()
    
    print(f"\\n{'='*50}")
    print(f"Test file creation completed!")
    print(f"Total images created: {total_images}")
    print(f"\\nTo test the application:")
    print(f"1. Run: python nanofiche.py")
    print(f"2. Follow instructions in TEST_INSTRUCTIONS.md")
    print(f"3. Start with 'small_test' scenario")


if __name__ == "__main__":
    main()