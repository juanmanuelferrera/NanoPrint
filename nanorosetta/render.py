from __future__ import annotations

import io
import math
from typing import List, Optional

import fitz  # PyMuPDF
from PIL import Image

from .units import mm_to_px, mm_to_pt
from .layout import Placement


def _render_pdf_page_to_pil(src_doc: fitz.Document, page_index: int, target_height_px: int) -> Image.Image:
    page = src_doc.load_page(page_index)
    h_pt = page.rect.height
    if h_pt <= 0:
        h_pt = 1.0
    scale = max(1e-6, target_height_px / h_pt)
    mat = fitz.Matrix(scale, scale)
    pm = page.get_pixmap(matrix=mat, colorspace=fitz.csGRAY, alpha=False)
    img = Image.frombytes("L", (pm.width, pm.height), pm.samples)
    return img


def compose_raster_any_shape(
    placements: List[Placement],
    doc_registry: List[fitz.Document],
    dpi: int,
    canvas_width_mm: float,
    canvas_height_mm: float,
    origin_center: bool = True,
    background: int = 255,
) -> Image.Image:
    canvas_w_px = mm_to_px(canvas_width_mm, dpi)
    canvas_h_px = mm_to_px(canvas_height_mm, dpi)
    
    # Check for dimension overflow (PIL typically has limits around 2^31-1 pixels)
    max_dimension = 2**30  # Conservative limit
    if canvas_w_px > max_dimension or canvas_h_px > max_dimension:
        raise ValueError(f"code=5: image dimensions might overflow (width={canvas_w_px}, height={canvas_h_px} pixels). Try reducing DPI or canvas size.")
    
    base = Image.new("L", (canvas_w_px, canvas_h_px), color=background)

    cx = canvas_w_px // 2 if origin_center else 0
    cy = canvas_h_px // 2 if origin_center else 0

    for pl in placements:
        src_doc = doc_registry[pl.doc_index]
        target_h_px = max(1, mm_to_px(pl.height_mm, dpi))
        page_img = _render_pdf_page_to_pil(src_doc, pl.page_index, target_h_px)
        rot = page_img.rotate(-pl.rotation_deg, expand=True, fillcolor=255)

        x_center_px = cx + mm_to_px(pl.center_xy_mm[0], dpi)
        y_center_px = cy + mm_to_px(pl.center_xy_mm[1], dpi)

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
    max_dpi = 10000  # Conservative limit to prevent overflow
    dpi = min(dpi, max_dpi)
    
    return int(max(1, round(dpi)))


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

    with io.BytesIO() as buf:
        rgb = img.convert("RGB")
        rgb.save(buf, format="PNG")
        stream = buf.getvalue()

    rect = fitz.Rect(0, 0, width_pt, height_pt)
    page.insert_image(rect, stream=stream, keep_proportion=False)
    doc.save(path)
    doc.close()
