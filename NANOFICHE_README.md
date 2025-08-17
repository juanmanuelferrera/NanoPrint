# NanoFiche Image Prep v1.0

Windows application for optimal bin packing of raster images into various envelope shapes.

## Overview

NanoFiche Image Prep arranges fixed-size image bins optimally into user-defined envelope shapes:
- **Square** - 1:1 aspect ratio
- **Rectangle** - User-defined aspect ratio (e.g., 1.29:1)  
- **Circle** - Optimal circular packing
- **Ellipse** - User-defined aspect ratio

## Key Features

✅ **Optimal Packing Algorithms** - Uses proven algorithms from NanoRosetta for maximum space utilization  
✅ **Multiple Envelope Shapes** - Square, rectangle, circle, and ellipse support  
✅ **Image Validation** - Automatically validates all images fit within bin dimensions  
✅ **Preview Workflow** - Generate preview before full output for user approval  
✅ **High-Quality Output** - Full resolution TIFF with LZW compression  
✅ **Comprehensive Logging** - Detailed project logs with timestamps and metrics  
✅ **User-Friendly GUI** - Windows native interface with all required prompts  

## Usage Workflow

### 1. Project Setup
- **Project Name**: Enter unique project identifier
- **Bin Dimensions**: Set fixed pixel dimensions (a, b) for image bins
- **Envelope Shape**: Choose from square, rectangle, circle, or ellipse
- **Aspect Ratio**: For rectangle/ellipse, specify width/height ratio

### 2. Input Selection  
- **Raster Folder**: Select folder containing images (PNG, JPEG, TIFF, BMP, GIF)
- **Output Location**: Choose where to save TIFF files and logs

### 3. Validation & Calculation
- Click **"Validate & Calculate Layout"**
- Application validates all images fit within bin dimensions
- Displays number of valid images found
- Calculates optimal packing layout

### 4. Results Review
View packing results:
- Grid dimensions (rows × columns)
- Canvas size in pixels  
- Envelope dimensions
- Packing efficiency percentage

### 5. Preview Generation
- Click **"Generate Preview"** 
- Creates downsampled TIFF (max 4,000 pixels)
- Review layout before full generation

### 6. Final Output
**Approve**: Generate full resolution TIFF with project log  
**Reject**: Generate thumbnail TIFF with project log

## Example Output

For project "test1" with:
- Bin dimensions: 1800 × 2300 pixels
- Envelope: Rectangle 1.29:1 aspect ratio  
- 1,000 image files

**Results:**
```
• Number of rows: 25
• Number of columns: 40  
• Canvas dimensions: 72,000 × 57,500 pixels
• Envelope dimensions: 72,000 × 55,814
• Aspect ratio: 1.290
• Packing efficiency: 100.0%
```

## Output Files

### TIFF Files
- **Preview**: `[project]_[datetime]_preview.tif` (max 4,000px)
- **Full**: `[project]_[datetime]_full.tif` (full resolution, if approved)
- **Thumbnail**: `[project]_[datetime]_thumbnail.tif` (max 2,000px, if rejected)

### Log Files  
- **Full**: `[project]_[datetime]_full.log` (approved projects)
- **Thumbnail**: `[project]_[datetime]_thumbnail.log` (rejected projects)

**Log Contents:**
- Project name, timestamp, input parameters
- Final output location and TIFF size
- Processing time, events, errors
- Success rate and configuration details

## Technical Specifications

### Supported Image Formats
- PNG, JPEG, TIFF, BMP, GIF
- RGB and RGBA color modes
- Any resolution within bin constraints

### Packing Algorithms
- **Rectangle/Square**: Grid-based optimization with aspect ratio matching
- **Circle**: Spiral placement algorithm adapted from NanoRosetta  
- **Ellipse**: Circular packing with aspect ratio scaling

### Output Quality
- **Full TIFF**: 300 DPI with LZW compression
- **Preview/Thumbnail**: 200 DPI with LZW compression
- Maximum canvas size: 500M pixels (safety limit)

### Performance
- Handles 1,000+ images efficiently  
- Memory-safe canvas validation
- Automatic downsampling for large outputs

## Installation

### Windows Executable
1. Download `NanoFiche_Image_Prep.exe`
2. Run directly - no installation required
3. Windows may show security warning (click "More info" → "Run anyway")

### Python Source
```bash
# Requirements: Python 3.10+
pip install pillow numpy shapely
python nanofiche.py
```

## Error Handling

### Image Validation Errors
- **"Image too large"**: Image exceeds bin dimensions
- **"Cannot read image"**: Corrupted or unsupported format

### Canvas Size Errors  
- Automatic DPI reduction for oversized outputs
- 500M pixel safety limit prevents memory overflow
- Suggestions provided for resolution adjustment

### Processing Errors
- Comprehensive error logging with stack traces
- Graceful fallback for partial failures
- User notifications with recovery suggestions

## Algorithm Details

### Rectangle Packing
Calculates optimal grid (rows × columns) to minimize envelope area while maintaining target aspect ratio:

```
target_cols_per_row = aspect_ratio × (bin_height / bin_width)
```

Tests all valid grid configurations and selects highest efficiency.

### Circle Packing  
Uses spiral placement algorithm from NanoRosetta:

1. Calculate circle radius for total bin area
2. Place bins in expanding spiral pattern
3. Optimize for 85% space utilization
4. Handle collision detection and overlap prevention

### Ellipse Packing
1. Start with optimal circle packing
2. Scale x-coordinates by aspect ratio  
3. Maintain y-coordinates unchanged
4. Recalculate envelope dimensions

## Support & Troubleshooting

### Debug Information
- Check `nanofiche_debug.log` for detailed execution traces
- Project logs contain full parameter and timing information
- Error messages include specific guidance for resolution

### Common Issues
1. **Images too large**: Reduce bin dimensions or resize source images
2. **Memory errors**: Use smaller canvas or enable automatic DPI reduction  
3. **No valid images**: Check image formats and folder permissions

### Performance Tips
- Use consistent image sizes close to bin dimensions
- Organize images with clear naming for sorted placement
- Choose output location with sufficient disk space

## Version History

**v1.0.0** - Initial release
- Complete Windows GUI application
- Four envelope shapes supported  
- Preview and approval workflow
- Comprehensive logging system
- Adapted NanoRosetta algorithms for optimal packing

---

**Built on NanoRosetta Technology**  
Uses proven packing algorithms from the NanoRosetta wafer layout system for maximum space utilization and reliability.