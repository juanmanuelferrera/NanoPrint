from __future__ import annotations

import argparse
import os
from typing import List, Tuple

import fitz  # PyMuPDF
from shapely.geometry import MultiPolygon

from .geometry import boolean_allowed_region, parse_svg_path
from .layout import PageSpec, plan_layout_any_shape
from .render import (
    compose_raster_any_shape,
    save_pdf_proof,
    save_tiff_1bit,
    save_tiff_gray,
    compute_dpi_for_target_mb,
)


def _collect_pages(input_paths: List[str]) -> Tuple[List[fitz.Document], List[PageSpec]]:
    docs: List[fitz.Document] = []
    pages: List[PageSpec] = []
    for doc_idx, p in enumerate(input_paths):
        d = fitz.open(p)
        docs.append(d)
        for i in range(d.page_count):
            r = d.load_page(i).rect
            pages.append(PageSpec(doc_index=doc_idx, page_index=i, width_pt=r.width, height_pt=r.height))
    return docs, pages


def cli_compose(args: argparse.Namespace) -> int:
    if not args.input:
        print("No --input PDFs provided.")
        return 2
    if not args.outer_shape:
        print("--outer-shape SVG is required.")
        return 2

    docs, pages = _collect_pages(args.input)

    outer: MultiPolygon = parse_svg_path(args.outer_shape)
    inner_shapes: List[MultiPolygon] = []
    for p in (args.inner_shape or []):
        inner_shapes.append(parse_svg_path(p))

    allowed = boolean_allowed_region(outer, inner_shapes)
    if allowed.is_empty:
        print("Allowed region is empty; check shapes.")
        return 3

    placements = plan_layout_any_shape(
        pages=pages,
        allowed_region_mm=allowed,
        nominal_height_mm=args.nominal_height_mm,
        gap_mm=args.gap_mm,
        orientation=args.orientation,
        scale_min=args.scale_min,
        scale_max=args.scale_max,
        streamline_step_mm=args.streamline_step_mm,
        max_streamlines=args.max_streamlines,
        optimize_for_dpi=args.optimize_for_dpi,
    )

    if not placements:
        print("No placements computed with current parameters.")
        return 4

    # Canvas from outer bounds
    minx, miny, maxx, maxy = allowed.bounds
    width_mm = (maxx - minx) + 2 * args.canvas_margin_mm
    height_mm = (maxy - miny) + 2 * args.canvas_margin_mm

    # Optional rounding to bin
    if args.canvas_bin_mm and args.canvas_bin_mm > 0:
        def round_up(v: float, b: float) -> float:
            n = int((v + b - 1e-9) // b)
            return (n + (0 if abs(n * b - v) < 1e-9 else 1)) * b
        width_mm = round_up(width_mm, args.canvas_bin_mm)
        height_mm = round_up(height_mm, args.canvas_bin_mm)

    # Recenter
    cx = (minx + maxx) / 2.0
    cy = (miny + maxy) / 2.0
    for pl in placements:
        x, y = pl.center_xy_mm
        pl.center_xy_mm = (x - cx, y - cy)

    dpi = args.tiff_dpi
    if args.target_mb:
        bpp = 1 if args.tiff_mode == "bilevel" else 8
        dpi = compute_dpi_for_target_mb(width_mm, height_mm, args.target_mb, bits_per_pixel=bpp)

    raster = compose_raster_any_shape(
        placements=placements,
        doc_registry=docs,
        dpi=dpi,
        canvas_width_mm=width_mm,
        canvas_height_mm=height_mm,
        origin_center=True,
    )

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        save_pdf_proof(raster, args.output, width_mm, height_mm)
        print(f"Wrote PDF proof: {args.output}")

    if args.export_tiff:
        os.makedirs(os.path.dirname(args.export_tiff) or ".", exist_ok=True)
        if args.tiff_mode == "bilevel":
            save_tiff_1bit(raster, args.export_tiff, dpi, compression=args.tiff_compression)
        else:
            save_tiff_gray(raster, args.export_tiff, dpi, compression=args.tiff_compression)
        print(f"Wrote TIFF: {args.export_tiff}")

    for d in docs:
        d.close()

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="nanorosetta", description="Any-shape wafer layout CLI")
    sub = p.add_subparsers(dest="cmd")

    c = sub.add_parser("compose", help="Compose PDF pages around any inner shape constrained to any outer shape")
    c.add_argument("--input", action="append", required=True, help="Input PDF path (repeatable)")
    c.add_argument("--outer-shape", required=True, help="SVG path/polygon file for outer constraint")
    c.add_argument("--inner-shape", action="append", help="SVG path/polygon file(s) for inner keep-outs (repeatable)")
    c.add_argument("--output", help="Output PDF proof path")
    c.add_argument("--export-tiff", help="Optional TIFF output path")

    # TIFF controls
    c.add_argument("--tiff-mode", choices=["bilevel", "gray"], default="bilevel", help="1-bit or 8-bit grayscale")
    c.add_argument("--tiff-compression", choices=["none", "deflate", "lzw"], default="lzw")
    c.add_argument("--tiff-dpi", type=int, default=1200, help="Raster DPI if no target size is set")
    c.add_argument("--target-mb", type=float, help="Target approximate TIFF size in MB (auto-compute DPI)")

    # Layout controls
    c.add_argument("--nominal-height-mm", type=float, default=3.0, help="Nominal page height along streamlines (mm)")
    c.add_argument("--gap-mm", type=float, default=0.5, help="Minimum gap between pages (mm)")
    c.add_argument("--orientation", choices=["tangent", "upright"], default="tangent")
    c.add_argument("--scale-min", type=float, default=0.1)
    c.add_argument("--scale-max", type=float, default=1.0)
    c.add_argument("--streamline-step-mm", type=float, default=2.0, help="Offset step for streamlines (mm)")
    c.add_argument("--max-streamlines", type=int, default=200)
    c.add_argument("--optimize-for-dpi", type=int, help="Calculate optimal page size to fill area at this DPI (overrides --nominal-height-mm)")

    # Canvas controls
    c.add_argument("--canvas-margin-mm", type=float, default=5.0, help="Extra margin around outer bounds (mm)")
    c.add_argument("--canvas-bin-mm", type=float, help="Round canvas dimensions to multiples of this value (mm)")

    c.set_defaults(func=cli_compose)
    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
