"""
Core packing algorithms for NanoFiche Image Prep.

Adapts existing nanorosetta algorithms for fixed-size image bin packing.
"""

import math
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum
from pathlib import Path
from PIL import Image

# Import existing algorithms
from nanorosetta.simple_bins import calculate_circle_radius, pack_bins_in_circle, BinPlacement
from nanorosetta.pixel_layout import calculate_pixel_layout, calculate_required_region_size_pixels
from nanorosetta.optimized_packing import analyze_shape_characteristics, generate_candidate_positions


class EnvelopeShape(Enum):
    """Supported envelope shapes for bin packing."""
    SQUARE = "square"
    RECTANGLE = "rectangle"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"


@dataclass
class ImageBin:
    """Represents a single image bin with file path and dimensions."""
    file_path: Path
    width: int
    height: int
    index: int  # Position in sorted order


@dataclass
class EnvelopeSpec:
    """Specification for the packing envelope."""
    shape: EnvelopeShape
    aspect_ratio: float = 1.0  # width/height ratio
    param1: Optional[float] = None  # e parameter for rectangle/ellipse
    param2: Optional[float] = None  # f parameter for rectangle/ellipse


@dataclass
class PackingResult:
    """Result of bin packing operation."""
    rows: int
    columns: int
    canvas_width: int
    canvas_height: int
    envelope_width: float
    envelope_height: float
    total_bins: int
    bins_placed: int
    placements: List[Tuple[int, int]]  # (x, y) coordinates for each bin
    efficiency: float


class NanoFichePacker:
    """Main class for optimal bin packing using adapted nanorosetta algorithms."""
    
    def __init__(self, bin_width: int, bin_height: int):
        """Initialize packer with fixed bin dimensions."""
        self.bin_width = bin_width
        self.bin_height = bin_height
        self.logger = logging.getLogger(__name__)
    
    def validate_images(self, folder_path: Path) -> Tuple[List[ImageBin], List[str]]:
        """
        Validate all images in folder and return valid bins plus errors.
        
        Args:
            folder_path: Path to folder containing raster images
            
        Returns:
            Tuple of (valid_image_bins, error_messages)
        """
        valid_bins = []
        errors = []
        
        if not folder_path.exists() or not folder_path.is_dir():
            errors.append(f"Folder does not exist: {folder_path}")
            return valid_bins, errors
        
        # Supported image formats
        supported_formats = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif'}
        
        # Get all image files and sort by name
        image_files = []
        for file_path in folder_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                image_files.append(file_path)
        
        image_files.sort(key=lambda x: x.name.lower())
        
        for index, file_path in enumerate(image_files):
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    
                    # Check if image dimensions fit within bin dimensions
                    if width <= self.bin_width and height <= self.bin_height:
                        valid_bins.append(ImageBin(file_path, width, height, index))
                    else:
                        errors.append(f"Image too large: {file_path.name} ({width}x{height}) > bin ({self.bin_width}x{self.bin_height})")
                        
            except Exception as e:
                errors.append(f"Cannot read image: {file_path.name} - {str(e)}")
        
        return valid_bins, errors
    
    def pack_rectangle(self, num_bins: int, envelope_spec: EnvelopeSpec) -> PackingResult:
        """Pack bins into rectangular envelope using grid layout."""
        target_aspect_ratio = envelope_spec.aspect_ratio
        
        # Calculate optimal grid dimensions using proper algorithm
        # We want: (cols * bin_width) / (rows * bin_height) = target_aspect_ratio
        # And: rows * cols >= num_bins (to fit all bins)
        # Solve: cols = target_aspect_ratio * rows * bin_height / bin_width
        
        bin_aspect = self.bin_width / self.bin_height
        
        # Start with square-ish arrangement and adjust for aspect ratio
        ideal_side = math.sqrt(num_bins)
        
        # Calculate reasonable range of rows to test (not all possibilities!)
        min_rows = max(1, int(ideal_side * 0.5))
        max_rows = min(num_bins, int(ideal_side * 2.0))
        
        self.logger.debug(f"Testing rows from {min_rows} to {max_rows} for {num_bins} bins")
        
        best_result = None
        best_score = -1
        
        for rows in range(min_rows, max_rows + 1):
            # Calculate columns needed
            cols = math.ceil(num_bins / rows)
            
            # Calculate actual canvas dimensions
            canvas_width = cols * self.bin_width
            canvas_height = rows * self.bin_height
            actual_aspect = canvas_width / canvas_height
            
            # Calculate how well this matches target aspect ratio
            aspect_error = abs(actual_aspect - target_aspect_ratio) / target_aspect_ratio
            
            # Calculate space efficiency
            total_slots = rows * cols
            space_efficiency = num_bins / total_slots
            
            # Combined score (prioritize space efficiency, penalize aspect error)
            score = space_efficiency - (aspect_error * 0.1)
            
            self.logger.debug(f"  {rows}x{cols}: canvas {canvas_width}x{canvas_height}, "
                            f"aspect {actual_aspect:.3f} (target {target_aspect_ratio:.3f}), "
                            f"efficiency {space_efficiency:.3f}, score {score:.3f}")
            
            if score > best_score:
                best_score = score
                
                # Generate placement coordinates
                placements = []
                for i in range(num_bins):
                    row = i // cols
                    col = i % cols
                    x = col * self.bin_width
                    y = row * self.bin_height
                    placements.append((x, y))
                
                best_result = PackingResult(
                    rows=rows,
                    columns=cols,
                    canvas_width=canvas_width,
                    canvas_height=canvas_height,
                    envelope_width=canvas_width,
                    envelope_height=canvas_height,
                    total_bins=total_slots,
                    bins_placed=num_bins,
                    placements=placements,
                    efficiency=space_efficiency
                )
        
        if best_result:
            self.logger.info(f"Selected grid: {best_result.rows}x{best_result.columns} "
                           f"for {num_bins} bins, efficiency: {best_result.efficiency:.1%}")
            return best_result
        else:
            self.logger.warning("No good grid found, using fallback")
            return self._fallback_rectangle_packing(num_bins)
    
    def pack_circle(self, num_bins: int) -> PackingResult:
        """Pack bins into circular envelope using adapted spiral algorithm."""
        # Use existing simple_bins circle packing algorithm
        from nanorosetta.layout import PageSpec
        
        # Create dummy page specs for existing algorithm
        pages = [PageSpec(0, i, self.bin_width * 72/25.4, self.bin_height * 72/25.4) 
                for i in range(num_bins)]
        
        # Convert to DPI (approximately)
        dpi = 300
        placements, canvas_width_px, canvas_height_px = self._pack_circular_bins(pages, dpi)
        
        # Calculate circle radius from canvas dimensions
        circle_radius = max(canvas_width_px, canvas_height_px) / 2
        
        return PackingResult(
            rows=int(math.sqrt(num_bins)),  # Approximate
            columns=int(math.sqrt(num_bins)),
            canvas_width=int(canvas_width_px),
            canvas_height=int(canvas_height_px),
            envelope_width=circle_radius * 2,
            envelope_height=circle_radius * 2,
            total_bins=num_bins,
            bins_placed=len(placements),
            placements=[(int(p.center_xy_mm[0] * dpi / 25.4), int(p.center_xy_mm[1] * dpi / 25.4)) 
                       for p in placements],
            efficiency=len(placements) / num_bins if num_bins > 0 else 0
        )
    
    def pack_ellipse(self, num_bins: int, envelope_spec: EnvelopeSpec) -> PackingResult:
        """Pack bins into elliptical envelope."""
        # Start with circular packing then scale for ellipse
        circle_result = self.pack_circle(num_bins)
        
        # Scale coordinates for ellipse aspect ratio
        aspect_ratio = envelope_spec.aspect_ratio
        scaled_placements = []
        
        center_x = circle_result.canvas_width / 2
        center_y = circle_result.canvas_height / 2
        
        for x, y in circle_result.placements:
            # Translate to origin, scale, translate back
            rel_x = x - center_x
            rel_y = y - center_y
            
            # Scale x coordinate for aspect ratio
            scaled_x = rel_x * aspect_ratio
            scaled_y = rel_y
            
            final_x = scaled_x + center_x * aspect_ratio
            final_y = scaled_y + center_y
            
            scaled_placements.append((int(final_x), int(final_y)))
        
        return PackingResult(
            rows=circle_result.rows,
            columns=circle_result.columns,
            canvas_width=int(circle_result.canvas_width * aspect_ratio),
            canvas_height=circle_result.canvas_height,
            envelope_width=circle_result.envelope_width * aspect_ratio,
            envelope_height=circle_result.envelope_height,
            total_bins=circle_result.total_bins,
            bins_placed=circle_result.bins_placed,
            placements=scaled_placements,
            efficiency=circle_result.efficiency
        )
    
    def pack_bins(self, image_bins: List[ImageBin], envelope_spec: EnvelopeSpec) -> PackingResult:
        """
        Pack image bins into specified envelope shape.
        
        Args:
            image_bins: List of validated image bins
            envelope_spec: Envelope shape specification
            
        Returns:
            PackingResult with optimal bin placement
        """
        num_bins = len(image_bins)
        
        if envelope_spec.shape == EnvelopeShape.SQUARE:
            # Square is rectangle with aspect ratio 1.0
            envelope_spec.aspect_ratio = 1.0
            return self.pack_rectangle(num_bins, envelope_spec)
        
        elif envelope_spec.shape == EnvelopeShape.RECTANGLE:
            return self.pack_rectangle(num_bins, envelope_spec)
        
        elif envelope_spec.shape == EnvelopeShape.CIRCLE:
            return self.pack_circle(num_bins)
        
        elif envelope_spec.shape == EnvelopeShape.ELLIPSE:
            return self.pack_ellipse(num_bins, envelope_spec)
        
        else:
            raise ValueError(f"Unsupported envelope shape: {envelope_spec.shape}")
    
    def _pack_circular_bins(self, pages, dpi):
        """Adapt simple_bins circular packing for image bins."""
        from nanorosetta.simple_bins import simple_bin_layout
        
        # Use existing simple bin layout algorithm
        bin_width_px = self.bin_width
        bin_height_px = self.bin_height
        
        return simple_bin_layout(pages, bin_width_px, bin_height_px, dpi)
    
    def _fallback_rectangle_packing(self, num_bins: int) -> PackingResult:
        """Fallback rectangular packing when optimization fails."""
        # Simple square-ish grid
        cols = math.ceil(math.sqrt(num_bins))
        rows = math.ceil(num_bins / cols)
        
        placements = []
        for i in range(num_bins):
            row = i // cols
            col = i % cols
            x = col * self.bin_width
            y = row * self.bin_height
            placements.append((x, y))
        
        canvas_width = cols * self.bin_width
        canvas_height = rows * self.bin_height
        
        return PackingResult(
            rows=rows,
            columns=cols,
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            envelope_width=canvas_width,
            envelope_height=canvas_height,
            total_bins=rows * cols,
            bins_placed=num_bins,
            placements=placements,
            efficiency=num_bins / (rows * cols)
        )