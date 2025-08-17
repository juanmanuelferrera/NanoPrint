"""
Rendering engine for NanoFiche Image Prep.

Handles TIFF generation with proper scaling and image placement.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List
from PIL import Image, ImageDraw
import math

from .core import ImageBin, PackingResult
from .logger import log_project


class NanoFicheRenderer:
    """Handles TIFF rendering for NanoFiche Image Prep."""
    
    def __init__(self):
        """Initialize the renderer."""
        self.logger = logging.getLogger(__name__)
    
    def generate_preview(self, image_bins: List[ImageBin], packing_result: PackingResult, 
                        output_path: Path, max_dimension: int = 4000):
        """
        Generate preview TIFF with maximum dimension constraint.
        
        Args:
            image_bins: List of image bins to place
            packing_result: Packing layout result
            output_path: Output path for preview TIFF
            max_dimension: Maximum pixel dimension for preview (default 4000)
        """
        self.logger.info(f"Generating preview TIFF: {output_path}")
        
        # Calculate scale factor to fit within max dimension
        canvas_width = packing_result.canvas_width
        canvas_height = packing_result.canvas_height
        max_current = max(canvas_width, canvas_height)
        
        if max_current > max_dimension:
            scale_factor = max_dimension / max_current
            preview_width = int(canvas_width * scale_factor)
            preview_height = int(canvas_height * scale_factor)
        else:
            scale_factor = 1.0
            preview_width = canvas_width
            preview_height = canvas_height
        
        self.logger.info(f"Preview scale factor: {scale_factor:.3f}")
        self.logger.info(f"Preview dimensions: {preview_width}x{preview_height}")
        
        # Create canvas
        canvas = Image.new('RGB', (preview_width, preview_height), color='white')
        
        # Place images
        for i, (x, y) in enumerate(packing_result.placements[:len(image_bins)]):
            if i >= len(image_bins):
                break
                
            image_bin = image_bins[i]
            
            try:
                # Load and resize image
                with Image.open(image_bin.file_path) as img:
                    # Scale position and size
                    scaled_x = int(x * scale_factor)
                    scaled_y = int(y * scale_factor)
                    
                    # Calculate scaled image size (maintain aspect ratio within bin)
                    bin_width_scaled = int(packing_result.canvas_width / packing_result.columns * scale_factor)
                    bin_height_scaled = int(packing_result.canvas_height / packing_result.rows * scale_factor)
                    
                    # Resize image to fit within scaled bin
                    img_resized = self._resize_image_to_fit(img, bin_width_scaled, bin_height_scaled)
                    
                    # Center image within bin
                    bin_center_x = scaled_x + bin_width_scaled // 2
                    bin_center_y = scaled_y + bin_height_scaled // 2
                    
                    paste_x = bin_center_x - img_resized.width // 2
                    paste_y = bin_center_y - img_resized.height // 2
                    
                    # Ensure coordinates are within canvas
                    paste_x = max(0, min(paste_x, preview_width - img_resized.width))
                    paste_y = max(0, min(paste_y, preview_height - img_resized.height))
                    
                    # Paste image
                    if img_resized.mode == 'RGBA':
                        canvas.paste(img_resized, (paste_x, paste_y), img_resized)
                    else:
                        canvas.paste(img_resized, (paste_x, paste_y))
                        
            except Exception as e:
                self.logger.warning(f"Could not place image {image_bin.file_path}: {e}")
                continue
        
        # Add grid lines for better visualization
        self._add_grid_lines(canvas, packing_result, scale_factor)
        
        # Save preview TIFF
        canvas.save(output_path, format='TIFF', compression='lzw', dpi=(200, 200))
        self.logger.info(f"Preview TIFF saved: {output_path}")
    
    def generate_full_tiff(self, image_bins: List[ImageBin], packing_result: PackingResult,
                          output_path: Path, log_path: Path, project_name: str, approved: bool = True):
        """
        Generate full resolution TIFF output.
        
        Args:
            image_bins: List of image bins to place
            packing_result: Packing layout result
            output_path: Output path for full TIFF
            log_path: Path for log file
            project_name: Project name for logging
            approved: Whether this was user-approved
        """
        start_time = datetime.now()
        self.logger.info(f"Generating full resolution TIFF: {output_path}")
        
        try:
            # Create full resolution canvas
            canvas_width = packing_result.canvas_width
            canvas_height = packing_result.canvas_height
            
            self.logger.info(f"Full canvas dimensions: {canvas_width}x{canvas_height}")
            
            # Check for reasonable size limits
            total_pixels = canvas_width * canvas_height
            if total_pixels > 500_000_000:  # 500M pixels
                self.logger.warning(f"Large canvas size: {total_pixels:,} pixels")
            
            canvas = Image.new('RGB', (canvas_width, canvas_height), color='white')
            
            # Place images at full resolution
            images_placed = 0
            for i, (x, y) in enumerate(packing_result.placements[:len(image_bins)]):
                if i >= len(image_bins):
                    break
                    
                image_bin = image_bins[i]
                
                try:
                    # Load image
                    with Image.open(image_bin.file_path) as img:
                        # Calculate bin dimensions
                        bin_width = packing_result.canvas_width // packing_result.columns
                        bin_height = packing_result.canvas_height // packing_result.rows
                        
                        # Resize image to fit within bin (maintain aspect ratio)
                        img_resized = self._resize_image_to_fit(img, bin_width, bin_height)
                        
                        # Center image within bin
                        bin_center_x = x + bin_width // 2
                        bin_center_y = y + bin_height // 2
                        
                        paste_x = bin_center_x - img_resized.width // 2
                        paste_y = bin_center_y - img_resized.height // 2
                        
                        # Ensure coordinates are within canvas
                        paste_x = max(0, min(paste_x, canvas_width - img_resized.width))
                        paste_y = max(0, min(paste_y, canvas_height - img_resized.height))
                        
                        # Paste image
                        if img_resized.mode == 'RGBA':
                            canvas.paste(img_resized, (paste_x, paste_y), img_resized)
                        else:
                            canvas.paste(img_resized, (paste_x, paste_y))
                        
                        images_placed += 1
                        
                except Exception as e:
                    self.logger.error(f"Could not place image {image_bin.file_path}: {e}")
                    continue
            
            # Save full TIFF with high quality
            canvas.save(output_path, format='TIFF', compression='lzw', dpi=(300, 300))
            
            end_time = datetime.now()
            process_time = (end_time - start_time).total_seconds()
            
            # Log the project
            log_project(
                log_path=log_path,
                project_name=project_name,
                timestamp=start_time,
                bin_width=image_bins[0].width if image_bins else 0,
                bin_height=image_bins[0].height if image_bins else 0,
                envelope_shape=packing_result.rows,  # Simplified for now
                num_files=len(image_bins),
                output_path=output_path,
                final_size=(canvas_width, canvas_height),
                process_time=process_time,
                approved=approved,
                images_placed=images_placed
            )
            
            self.logger.info(f"Full TIFF completed: {output_path} ({images_placed} images placed)")
            
        except Exception as e:
            self.logger.error(f"Error generating full TIFF: {e}", exc_info=True)
            # Still log the failed attempt
            log_project(
                log_path=log_path,
                project_name=project_name,
                timestamp=start_time,
                bin_width=0,
                bin_height=0,
                envelope_shape=0,
                num_files=len(image_bins),
                output_path=output_path,
                final_size=(0, 0),
                process_time=0,
                approved=approved,
                images_placed=0,
                error=str(e)
            )
            raise
    
    def generate_thumbnail_tiff(self, image_bins: List[ImageBin], packing_result: PackingResult,
                               output_path: Path, log_path: Path, project_name: str, approved: bool = False):
        """
        Generate thumbnail TIFF (rejected layout).
        
        Args:
            image_bins: List of image bins to place
            packing_result: Packing layout result
            output_path: Output path for thumbnail TIFF
            log_path: Path for log file
            project_name: Project name for logging
            approved: Whether this was user-approved (False for thumbnail)
        """
        self.logger.info(f"Generating thumbnail TIFF: {output_path}")
        
        # Generate thumbnail (same as preview but smaller)
        self.generate_preview(image_bins, packing_result, output_path, max_dimension=2000)
        
        # Log the project
        start_time = datetime.now()
        log_project(
            log_path=log_path,
            project_name=project_name,
            timestamp=start_time,
            bin_width=image_bins[0].width if image_bins else 0,
            bin_height=image_bins[0].height if image_bins else 0,
            envelope_shape=packing_result.rows,  # Simplified for now
            num_files=len(image_bins),
            output_path=output_path,
            final_size=(2000, 2000),  # Max thumbnail size
            process_time=1.0,  # Approximate
            approved=approved,
            images_placed=len(image_bins)
        )
        
        self.logger.info(f"Thumbnail TIFF completed: {output_path}")
    
    def _resize_image_to_fit(self, img: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """
        Resize image to fit within specified dimensions while maintaining aspect ratio.
        
        Args:
            img: Source image
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Resized image
        """
        # Calculate scaling factor
        width_ratio = max_width / img.width
        height_ratio = max_height / img.height
        scale_factor = min(width_ratio, height_ratio)
        
        # Don't upscale
        if scale_factor > 1.0:
            scale_factor = 1.0
        
        # Calculate new dimensions
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        
        # Resize image
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    def _add_grid_lines(self, canvas: Image.Image, packing_result: PackingResult, scale_factor: float):
        """
        Add grid lines to preview for better visualization.
        
        Args:
            canvas: Canvas image to draw on
            packing_result: Packing result for grid dimensions
            scale_factor: Scale factor for coordinates
        """
        draw = ImageDraw.Draw(canvas)
        
        # Calculate scaled bin dimensions
        bin_width = int(packing_result.canvas_width / packing_result.columns * scale_factor)
        bin_height = int(packing_result.canvas_height / packing_result.rows * scale_factor)
        
        # Draw vertical lines
        for col in range(packing_result.columns + 1):
            x = int(col * bin_width)
            draw.line([(x, 0), (x, canvas.height - 1)], fill='lightgray', width=1)
        
        # Draw horizontal lines
        for row in range(packing_result.rows + 1):
            y = int(row * bin_height)
            draw.line([(0, y), (canvas.width - 1, y)], fill='lightgray', width=1)