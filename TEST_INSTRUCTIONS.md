
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
