"""
Logging utilities for NanoFiche Image Prep.

Handles project logging with all required information.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging():
    """Setup application logging."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler for debug log
    debug_log_path = Path("nanofiche_debug.log")
    file_handler = logging.FileHandler(debug_log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logging.info("NanoFiche logging initialized")


def log_project(log_path: Path, project_name: str, timestamp: datetime,
                bin_width: int, bin_height: int, envelope_shape: int,
                num_files: int, output_path: Path, final_size: tuple,
                process_time: float, approved: bool, images_placed: int,
                error: Optional[str] = None):
    """
    Log project details to specified log file.
    
    Args:
        log_path: Path to log file
        project_name: Name of the project
        timestamp: Project start timestamp
        bin_width: Bin width in pixels
        bin_height: Bin height in pixels
        envelope_shape: Envelope shape identifier
        num_files: Number of input files
        output_path: Path to output TIFF
        final_size: Final TIFF dimensions (width, height)
        process_time: Processing time in seconds
        approved: Whether user approved the layout
        images_placed: Number of images successfully placed
        error: Error message if failed
    """
    log_content = f"""NanoFiche Image Prep - Project Log
{'=' * 50}

Project Information:
    Project Name: {project_name}
    Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}
    Status: {'APPROVED' if approved else 'REJECTED' if error is None else 'ERROR'}

Input Parameters:
    Bin Dimensions: {bin_width} x {bin_height} pixels
    Envelope Shape: {envelope_shape}
    Input Files: {num_files}
    Images Placed: {images_placed}

Output Information:
    Output Path: {output_path}
    Final TIFF Size: {final_size[0]} x {final_size[1]} pixels
    Total Pixels: {final_size[0] * final_size[1]:,}

Process Information:
    Processing Time: {process_time:.2f} seconds
    Completion Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
    
    if error:
        log_content += f"""Error Information:
    Error: {error}

"""
    
    log_content += f"""Events:
    {timestamp.strftime('%H:%M:%S')} - Project started
    {timestamp.strftime('%H:%M:%S')} - Input validation completed
    {timestamp.strftime('%H:%M:%S')} - Layout calculation completed
    {timestamp.strftime('%H:%M:%S')} - {'Full TIFF' if approved else 'Thumbnail'} generation started
    {datetime.now().strftime('%H:%M:%S')} - Process completed

Configuration:
    Max Canvas Pixels: 500,000,000
    Preview Max Dimension: 4,000 pixels
    Thumbnail Max Dimension: 2,000 pixels
    Output Format: TIFF with LZW compression
    Output DPI: {'300' if approved else '200'}

Summary:
    Project: {project_name}
    Files Processed: {images_placed}/{num_files}
    Success Rate: {(images_placed/num_files*100) if num_files > 0 else 0:.1f}%
    Final Status: {'SUCCESS' if error is None else 'FAILED'}
"""
    
    # Write log file
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        # Also log to main logger
        logger = logging.getLogger(__name__)
        logger.info(f"Project log written: {log_path}")
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to write project log {log_path}: {e}")


def log_validation_results(project_name: str, total_files: int, valid_files: int, 
                          errors: list, bin_width: int, bin_height: int):
    """
    Log image validation results to debug log.
    
    Args:
        project_name: Project name
        total_files: Total files found
        valid_files: Number of valid files
        errors: List of validation errors
        bin_width: Bin width constraint
        bin_height: Bin height constraint
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Image Validation Results for project '{project_name}':")
    logger.info(f"  Bin constraints: {bin_width}x{bin_height} pixels")
    logger.info(f"  Total files found: {total_files}")
    logger.info(f"  Valid files: {valid_files}")
    logger.info(f"  Validation errors: {len(errors)}")
    
    if errors:
        logger.warning("Validation errors:")
        for error in errors[:10]:  # Log first 10 errors
            logger.warning(f"  - {error}")
        if len(errors) > 10:
            logger.warning(f"  ... and {len(errors) - 10} more errors")


def log_packing_calculation(project_name: str, envelope_shape: str, 
                           packing_result, calculation_time: float):
    """
    Log packing calculation results.
    
    Args:
        project_name: Project name
        envelope_shape: Shape of envelope
        packing_result: PackingResult object
        calculation_time: Time taken for calculation
    """
    logger = logging.getLogger(__name__)
    
    logger.info(f"Packing Calculation for project '{project_name}':")
    logger.info(f"  Envelope shape: {envelope_shape}")
    logger.info(f"  Grid: {packing_result.rows} rows x {packing_result.columns} columns")
    logger.info(f"  Canvas: {packing_result.canvas_width}x{packing_result.canvas_height} pixels")
    logger.info(f"  Envelope: {packing_result.envelope_width:.1f}x{packing_result.envelope_height:.1f}")
    logger.info(f"  Bins placed: {packing_result.bins_placed}/{packing_result.total_bins}")
    logger.info(f"  Efficiency: {packing_result.efficiency:.1%}")
    logger.info(f"  Calculation time: {calculation_time:.3f} seconds")