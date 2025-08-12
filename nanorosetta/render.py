from __future__ import annotations

import io
import logging
import math
from typing import List, Optional

import fitz  # PyMuPDF
from PIL import Image

from .units import mm_to_px, mm_to_pt
from .layout import Placement


def _render_pdf_page_to_pil(src_doc: fitz.Document, page_index: int, target_height_px: int) -> Image.Image:
    """
    Render PDF page to PIL Image by sampling at 200 DPI then scaling up.
    This prevents memory issues when target dimensions are very large.
    """
    page = src_doc.load_page(page_index)
    h_pt = page.rect.height
    w_pt = page.rect.width
    if h_pt <= 0:
        h_pt = 1.0
    if w_pt <= 0:
        w_pt = 1.0
    
    # Sample at 200 DPI to avoid memory issues with high DPI
    sample_dpi = 200
    sample_scale = sample_dpi / 72.0  # PyMuPDF uses 72 DPI as base
    
    logging.debug(f"Rendering page {page_index}: {w_pt:.1f}x{h_pt:.1f}pt at {sample_dpi} DPI")
    
    # Create pixmap at sample resolution
    mat = fitz.Matrix(sample_scale, sample_scale)
    pm = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, alpha=False)
    sampled_img = Image.frombytes("L", (pm.width, pm.height), pm.samples)
    
    logging.debug(f"Sampled image size: {sampled_img.width}x{sampled_img.height} pixels")
    
    # Calculate target width maintaining aspect ratio
    target_width_px = int((target_height_px * w_pt) / h_pt)
    
    logging.debug(f"Scaling to target size: {target_width_px}x{target_height_px} pixels")
    
    # Scale up to target dimensions using high-quality resampling
    if target_width_px != sampled_img.width or target_height_px != sampled_img.height:
        scaled_img = sampled_img.resize((target_width_px, target_height_px), Image.LANCZOS)
        return scaled_img
    else:
        return sampled_img


def validate_canvas_dimensions(canvas_width_mm: float, canvas_height_mm: float, dpi: int) -> tuple[int, int, int]:
    """
    Validate canvas dimensions and return safe pixel dimensions and DPI.
    
    Args:
        canvas_width_mm: Canvas width in mm
        canvas_height_mm: Canvas height in mm
        dpi: Target DPI
    
    Returns:
        Tuple of (safe_width_px, safe_height_px, safe_dpi)
    """
    logging.debug(f"Validating canvas dimensions: {canvas_width_mm:.2f}x{canvas_height_mm:.2f}mm at {dpi} DPI")
    
    # PIL's maximum image dimensions (varies by system, but typically 2^31-1)
    # Use a conservative limit of 2^28 (268,435,456 pixels) to be safe
    max_pixels_per_dimension = 2**28
    
    # Calculate pixel dimensions
    width_px = mm_to_px(canvas_width_mm, dpi)
    height_px = mm_to_px(canvas_height_mm, dpi)
    logging.debug(f"Calculated pixel dimensions: {width_px}x{height_px} pixels")
    
    # Check if dimensions are too large
    if width_px > max_pixels_per_dimension or height_px > max_pixels_per_dimension:
        logging.warning(f"Dimensions exceed safe limit ({max_pixels_per_dimension} pixels per dimension)")
        
        # Calculate required DPI reduction
        max_dimension_mm = max(canvas_width_mm, canvas_height_mm)
        safe_dpi = int((max_pixels_per_dimension * 25.4) / max_dimension_mm)
        
        # Ensure DPI is reasonable (minimum 50 DPI)
        safe_dpi = max(50, min(safe_dpi, dpi))
        logging.info(f"DPI reduced from {dpi} to {safe_dpi} for safety")
        
        # Recalculate pixel dimensions with safe DPI
        width_px = mm_to_px(canvas_width_mm, safe_dpi)
        height_px = mm_to_px(canvas_height_mm, safe_dpi)
        logging.debug(f"Safe pixel dimensions: {width_px}x{height_px} pixels")
        
        return width_px, height_px, safe_dpi
    
    logging.debug("Canvas dimensions are within safe limits")
    return width_px, height_px, dpi


def compose_raster_any_shape(
    placements: List[Placement],
    doc_registry: List[fitz.Document],
    dpi: int,
    canvas_width_mm: float,
    canvas_height_mm: float,
    origin_center: bool = True,
    background: int = 255,
) -> Image.Image:
    logging.info(f"Starting raster composition with {len(placements)} placements")
    logging.debug(f"Canvas: {canvas_width_mm:.2f}x{canvas_height_mm:.2f}mm, target DPI: {dpi}")
    logging.debug(f"Origin center: {origin_center}, background: {background}")
    
    # Validate and potentially reduce DPI to prevent overflow
    logging.debug("Calling validate_canvas_dimensions")
    canvas_w_px, canvas_h_px, safe_dpi = validate_canvas_dimensions(canvas_width_mm, canvas_height_mm, dpi)
    logging.debug(f"Validation result: {canvas_w_px}x{canvas_h_px}px at {safe_dpi} DPI")
    
    # Warn if DPI was reduced
    if safe_dpi < dpi:
        logging.warning(f"DPI reduced from {dpi} to {safe_dpi} to prevent image overflow")
        print(f"Warning: DPI reduced from {dpi} to {safe_dpi} to prevent image overflow")
        print(f"Canvas dimensions: {canvas_width_mm:.1f}mm x {canvas_height_mm:.1f}mm")
        print(f"Pixel dimensions: {canvas_w_px:,} x {canvas_h_px:,} pixels")
    
    try:
        logging.debug(f"Creating PIL Image: {canvas_w_px}x{canvas_h_px} pixels, mode='L', background={background}")
        base = Image.new("L", (canvas_w_px, canvas_h_px), color=background)
        logging.debug("PIL Image created successfully")
    except Exception as e:
        logging.error(f"PIL Image creation failed: {type(e).__name__}: {e}")
        logging.error(f"Attempted dimensions: {canvas_w_px:,} x {canvas_h_px:,} pixels")
        logging.error(f"Total pixels: {canvas_w_px * canvas_h_px:,}")
        logging.error(f"Memory estimate: ~{(canvas_w_px * canvas_h_px) / (1024*1024):.1f} MB")
        raise ValueError(f"Failed to create image with dimensions {canvas_w_px:,} x {canvas_h_px:,} pixels. "
                        f"Try reducing DPI (current: {safe_dpi}) or canvas size. Error: {e}")

    cx = canvas_w_px // 2 if origin_center else 0
    cy = canvas_h_px // 2 if origin_center else 0

    logging.debug(f"Processing {len(placements)} placements")
    for idx, pl in enumerate(placements):
        logging.debug(f"Processing placement {idx+1}/{len(placements)}: doc_index={pl.doc_index}, page={pl.page_index}")
        src_doc = doc_registry[pl.doc_index]
        target_h_px = max(1, mm_to_px(pl.height_mm, safe_dpi))
        logging.debug(f"Target height: {pl.height_mm:.2f}mm = {target_h_px}px")
        page_img = _render_pdf_page_to_pil(src_doc, pl.page_index, target_h_px)
        rot = page_img.rotate(-pl.rotation_deg, expand=True, fillcolor=255)

        x_center_px = cx + mm_to_px(pl.center_xy_mm[0], safe_dpi)
        y_center_px = cy + mm_to_px(pl.center_xy_mm[1], safe_dpi)

        x0 = int(round(x_center_px - rot.width / 2))
        y0 = int(round(y_center_px - rot.height / 2))
        base.paste(rot, (x0, y0))

    return base


def compute_dpi_for_target_mb(width_mm: float, height_mm: float, target_mb: float, bits_per_pixel: int = 1) -> int:
    # Uncompressed estimate: bytes ≈ pixels * bpp / 8
    # pixels = (width_mm * dpi / 25.4) * (height_mm * dpi / 25.4)
    # Solve dpi^2 = bytes * 8 / bpp * (25.4^2) / (width_mm * height_mm)
    bytes_target = max(1.0, target_mb) * 1024.0 * 1024.0
    numerator = bytes_target * 8.0 / max(1, bits_per_pixel) * (25.4 ** 2)
    denominator = max(1e-6, width_mm * height_mm)
    dpi = math.sqrt(numerator / denominator)
    
    # Limit DPI to prevent dimension overflow
    # Use more conservative limits based on canvas size
    max_dimension_mm = max(width_mm, height_mm)
    max_safe_dpi = int((2**28 * 25.4) / max_dimension_mm)  # 2^28 pixels max per dimension
    max_dpi = min(5000, max_safe_dpi)  # Additional conservative limit
    
    dpi = min(dpi, max_dpi)
    
    return int(max(50, round(dpi)))  # Minimum 50 DPI


def save_tiff_1bit(img: Image.Image, path: str, dpi: int, compression: Optional[str] = None) -> None:
    img_1 = img.convert("1")
    if compression is None or compression == "none":
        img_1.save(path, format="TIFF", dpi=(dpi, dpi))
    elif compression == "deflate":
        img_1.save(path, format="TIFF", compression="tiff_deflate", dpi=(dpi, dpi))
    elif compression == "lzw":
        img_1.save(path, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    else:
        img_1.save(path, format="TIFF", dpi=(dpi, dpi))


def save_tiff_gray(img: Image.Image, path: str, dpi: int, compression: Optional[str] = None) -> None:
    img_g = img.convert("L")
    if compression is None or compression == "none":
        img_g.save(path, format="TIFF", dpi=(dpi, dpi))
    elif compression == "deflate":
        img_g.save(path, format="TIFF", compression="tiff_deflate", dpi=(dpi, dpi))
    elif compression == "lzw":
        img_g.save(path, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    else:
        img_g.save(path, format="TIFF", dpi=(dpi, dpi))


def save_pdf_proof(img: Image.Image, path: str, width_mm: float, height_mm: float) -> None:
    width_pt = mm_to_pt(width_mm)
    height_pt = mm_to_pt(height_mm)
    doc = fitz.open()
    page = doc.new_page(width=width_pt, height=height_pt)

    # Downsample large images for PDF proof to prevent PyMuPDF overflow
    # PDF proof is just for preview, doesn't need full resolution
    max_dimension = 8000  # Conservative limit for PyMuPDF
    if img.width > max_dimension or img.height > max_dimension:
        scale_factor = min(max_dimension / img.width, max_dimension / img.height)
        new_width = int(img.width * scale_factor)
        new_height = int(img.height * scale_factor)
        logging.info(f"Downsampling PDF proof from {img.width}x{img.height} to {new_width}x{new_height} pixels")
        img = img.resize((new_width, new_height), Image.LANCZOS)

    with io.BytesIO() as buf:
        rgb = img.convert("RGB")
        rgb.save(buf, format="PNG")
        stream = buf.getvalue()

    rect = fitz.Rect(0, 0, width_pt, height_pt)
    page.insert_image(rect, stream=stream, keep_proportion=False)
    doc.save(path)
    doc.close()
