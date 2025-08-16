from __future__ import annotations

import logging
import math
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List

import fitz  # PyMuPDF

from .geometry import parse_svg_path, parse_combined_svg, boolean_allowed_region
from .layout import PageSpec, plan_layout_any_shape
from .optimized_packing import optimized_packing_layout, adaptive_size_packing
from .pixel_layout import calculate_pixel_layout, calculate_required_region_size_pixels, calculate_svg_scale_factor
from .render import (
    compose_raster_any_shape,
    save_pdf_proof,
    save_tiff_1bit,
    save_tiff_gray,
    compute_dpi_for_target_mb,
)


class NanoPrintGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NanoPrint")
        self.geometry("720x560")
        self.logger = logging.getLogger(__name__)
        self._build_widgets()

    def _build_widgets(self) -> None:
        pad = {"padx": 6, "pady": 4}

        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True)

        # Inputs
        self.input_pdfs: List[str] = []
        self.outer_shape_var = tk.StringVar()
        self.inner_shapes: List[str] = []
        self.output_pdf_var = tk.StringVar()
        self.export_tiff_var = tk.StringVar()
        
        # Combined SVG options
        self.auto_detect_inner_var = tk.BooleanVar(value=False)
        self.min_inner_area_ratio_var = tk.DoubleVar(value=0.01)
        
        # Advanced packing options
        self.use_optimized_packing_var = tk.BooleanVar(value=False)  # Changed to False - optimized packing makes pages too small
        self.adaptive_sizing_var = tk.BooleanVar(value=False)
        self.target_fill_ratio_var = tk.DoubleVar(value=0.85)
        self.pixel_first_var = tk.BooleanVar(value=True)  # Stay in pixel space
        self.auto_scale_svg_var = tk.BooleanVar(value=True)  # Auto-scale SVG to fit all pages

        row = 0
        ttk.Label(frm, text="Input PDFs").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Button(frm, text="Add PDFs", command=self._choose_pdfs).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Button(frm, text="Clear PDFs", command=self._clear_pdfs).grid(row=row, column=2, sticky=tk.W, **pad)
        self.pdf_list = tk.Listbox(frm, height=3)
        self.pdf_list.grid(row=row, column=3, columnspan=2, sticky=tk.EW, **pad)

        row += 1
        ttk.Label(frm, text="Outer SVG").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.outer_shape_var).grid(row=row, column=1, columnspan=2, sticky=tk.EW, **pad)
        ttk.Button(frm, text="Browse", command=self._choose_outer).grid(row=row, column=3, sticky=tk.W, **pad)
        ttk.Button(frm, text="Clear", command=self._clear_outer).grid(row=row, column=4, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Inner SVGs").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Button(frm, text="Add Inner", command=self._choose_inners).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Button(frm, text="Clear Inners", command=self._clear_inners).grid(row=row, column=2, sticky=tk.W, **pad)
        self.inner_list = tk.Listbox(frm, height=3)
        self.inner_list.grid(row=row, column=3, columnspan=2, sticky=tk.EW, **pad)
        
        # Combined SVG option
        row += 1
        self.auto_detect_checkbox = ttk.Checkbutton(frm, text="Auto-detect inner shapes from outer SVG", 
                                                   variable=self.auto_detect_inner_var,
                                                   command=self._on_auto_detect_changed)
        self.auto_detect_checkbox.grid(row=row, column=0, columnspan=3, sticky=tk.W, **pad)
        
        ttk.Label(frm, text="Min area ratio:").grid(row=row, column=3, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.min_inner_area_ratio_var, width=8).grid(row=row, column=4, sticky=tk.W, **pad)

        # Options
        row += 1
        self.nominal_height_var = tk.DoubleVar(value=3.0)
        self.gap_var = tk.DoubleVar(value=0.5)
        self.orientation_var = tk.StringVar(value="tangent")
        self.canvas_margin_var = tk.DoubleVar(value=5.0)
        self.canvas_bin_var = tk.DoubleVar(value=0.0)
        self.target_mb_var = tk.DoubleVar(value=900.0)
        
        # Page margins in mm - left, top, right, bottom
        self.page_margin_left_var = tk.DoubleVar(value=12.7)  # 0.5" = 12.7mm gutter
        self.page_margin_top_var = tk.DoubleVar(value=6.35)   # 0.25" = 6.35mm
        self.page_margin_right_var = tk.DoubleVar(value=6.35) # 0.25" = 6.35mm
        self.page_margin_bottom_var = tk.DoubleVar(value=6.35) # 0.25" = 6.35mm
        self.tiff_mode_var = tk.StringVar(value="bilevel")
        self.tiff_comp_var = tk.StringVar(value="lzw")
        self.tiff_dpi_var = tk.IntVar(value=1200)
        self.optimize_dpi_var = tk.IntVar(value=0)  # 0 = disabled, >0 = DPI value
        self.max_canvas_pixels_var = tk.IntVar(value=100_000_000)  # 100M pixels default

        row += 1
        ttk.Label(frm, text="Target MB").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.target_mb_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="TIFF Mode").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Combobox(frm, textvariable=self.tiff_mode_var, values=["bilevel", "gray"], width=10).grid(row=row, column=3, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Compression").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Combobox(frm, textvariable=self.tiff_comp_var, values=["lzw", "deflate", "none"], width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="Fallback DPI").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.tiff_dpi_var, width=8).grid(row=row, column=3, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Nominal Height (mm)").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.nominal_height_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="Gap (mm)").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.gap_var, width=10).grid(row=row, column=3, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Optimize for DPI").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.optimize_dpi_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="(0=disabled)").grid(row=row, column=2, sticky=tk.W, **pad)
        
        row += 1
        ttk.Label(frm, text="Max Canvas Pixels").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.max_canvas_pixels_var, width=15).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="(memory limit)").grid(row=row, column=2, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Orientation").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Combobox(frm, textvariable=self.orientation_var, values=["tangent", "upright"], width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="Canvas Margin (mm)").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.canvas_margin_var, width=10).grid(row=row, column=3, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Canvas Bin (mm)").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.canvas_bin_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)

        # Page margins section
        row += 1
        ttk.Label(frm, text="Page Margin Left (mm)").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.page_margin_left_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="Page Margin Top (mm)").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.page_margin_top_var, width=10).grid(row=row, column=3, sticky=tk.W, **pad)
        
        row += 1
        ttk.Label(frm, text="Page Margin Right (mm)").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.page_margin_right_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="Page Margin Bottom (mm)").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.page_margin_bottom_var, width=10).grid(row=row, column=3, sticky=tk.W, **pad)

        # Advanced Packing Options
        row += 1
        ttk.Label(frm, text="ADVANCED PACKING", font=("TkDefaultFont", 9, "bold")).grid(row=row, column=0, columnspan=2, sticky=tk.W, **pad)
        
        row += 1
        ttk.Checkbutton(frm, text="Auto-scale SVG to fit all pages (recommended)", 
                       variable=self.auto_scale_svg_var).grid(row=row, column=0, columnspan=4, sticky=tk.W, **pad)
        
        row += 1
        ttk.Checkbutton(frm, text="Use optimized packing (WARNING: may make pages very small)", 
                       variable=self.use_optimized_packing_var).grid(row=row, column=0, columnspan=4, sticky=tk.W, **pad)
        
        row += 1
        ttk.Checkbutton(frm, text="Adaptive sizing (auto-adjust page sizes for best fit)", 
                       variable=self.adaptive_sizing_var,
                       command=self._on_adaptive_sizing_changed).grid(row=row, column=0, columnspan=3, sticky=tk.W, **pad)
        
        ttk.Label(frm, text="Target fill:").grid(row=row, column=3, sticky=tk.E, **pad)
        self.target_fill_entry = ttk.Entry(frm, textvariable=self.target_fill_ratio_var, width=8)
        self.target_fill_entry.grid(row=row, column=4, sticky=tk.W, **pad)
        
        # Pixel-first is now always enabled
        # row += 1
        # ttk.Checkbutton(frm, text="Pixel-first layout (for consistent quality)", 
        #                variable=self.pixel_first_var).grid(row=row, column=0, columnspan=4, sticky=tk.W, **pad)

        # PDF proof output removed for better performance and reliability
        # row += 1
        # ttk.Label(frm, text="Output PDF Proof").grid(row=row, column=0, sticky=tk.W, **pad)
        # ttk.Entry(frm, textvariable=self.output_pdf_var).grid(row=row, column=1, columnspan=2, sticky=tk.EW, **pad)
        # ttk.Button(frm, text="Browse", command=self._choose_output_pdf).grid(row=row, column=3, sticky=tk.W, **pad)
        # ttk.Button(frm, text="Clear", command=self._clear_output_pdf).grid(row=row, column=4, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Export TIFF").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.export_tiff_var).grid(row=row, column=1, columnspan=2, sticky=tk.EW, **pad)
        ttk.Button(frm, text="Browse", command=self._choose_export_tiff).grid(row=row, column=3, sticky=tk.W, **pad)
        ttk.Button(frm, text="Clear", command=self._clear_export_tiff).grid(row=row, column=4, sticky=tk.W, **pad)

        # Run
        row += 1
        ttk.Button(frm, text="Run", command=self._run_async).grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Button(frm, text="Clear All", command=self._clear_all).grid(row=row, column=1, sticky=tk.W, **pad)
        self.progress = ttk.Label(frm, text="Idle")
        self.progress.grid(row=row, column=2, columnspan=3, sticky=tk.W, **pad)

        # Log
        row += 1
        self.log = tk.Text(frm, height=10)
        self.log.grid(row=row, column=0, columnspan=5, sticky=tk.NSEW, **pad)

        # Grid weights
        for c in range(5):
            frm.columnconfigure(c, weight=1)
        for r in range(row + 1):
            frm.rowconfigure(r, weight=0)
        frm.rowconfigure(row, weight=1)

    def _choose_pdfs(self) -> None:
        paths = filedialog.askopenfilenames(title="Select PDF(s)", filetypes=[("PDF","*.pdf")])
        if paths:
            # Replace existing PDFs instead of appending
            self.input_pdfs = list(paths)
            self.pdf_list.delete(0, tk.END)
            for p in self.input_pdfs:
                self.pdf_list.insert(tk.END, p)
            self._log(f"Selected {len(self.input_pdfs)} PDF file(s)")

    def _clear_pdfs(self) -> None:
        self.input_pdfs = []
        self.pdf_list.delete(0, tk.END)
        self._log("Cleared PDF selections")

    def _choose_outer(self) -> None:
        p = filedialog.askopenfilename(title="Select outer SVG", filetypes=[("SVG","*.svg")])
        if p:
            self.outer_shape_var.set(p)
            self._log(f"Selected outer SVG: {p}")

    def _clear_outer(self) -> None:
        self.outer_shape_var.set("")
        self._log("Cleared outer SVG selection")

    def _choose_inners(self) -> None:
        paths = filedialog.askopenfilenames(title="Select inner SVG(s)", filetypes=[("SVG","*.svg")])
        if paths:
            # Replace existing inner shapes instead of appending
            self.inner_shapes = list(paths)
            self.inner_list.delete(0, tk.END)
            for p in self.inner_shapes:
                self.inner_list.insert(tk.END, p)
            self._log(f"Selected {len(self.inner_shapes)} inner SVG file(s)")

    def _clear_inners(self) -> None:
        self.inner_shapes = []
        self.inner_list.delete(0, tk.END)
        self._log("Cleared inner SVG selections")
    
    def _on_auto_detect_changed(self):
        """Handle auto-detect checkbox changes."""
        if self.auto_detect_inner_var.get():
            # Disable inner shape selection when auto-detect is enabled
            self.inner_list.config(state=tk.DISABLED)
            self._log("Auto-detect enabled: inner shapes will be detected from outer SVG")
        else:
            # Re-enable inner shape selection
            self.inner_list.config(state=tk.NORMAL)
            self._log("Auto-detect disabled: manual inner shape selection enabled")
    
    def _on_adaptive_sizing_changed(self):
        """Handle adaptive sizing checkbox changes."""
        if self.adaptive_sizing_var.get():
            self.target_fill_entry.config(state=tk.NORMAL)
            self._log("Adaptive sizing enabled: pages will be auto-sized for optimal space utilization")
        else:
            self.target_fill_entry.config(state=tk.DISABLED)
            self._log("Adaptive sizing disabled: using nominal page sizes")

    def _choose_output_pdf(self) -> None:
        p = filedialog.asksaveasfilename(title="Save PDF proof", defaultextension=".pdf", filetypes=[("PDF","*.pdf")])
        if p:
            self.output_pdf_var.set(p)
            self._log(f"Selected output PDF: {p}")

    def _clear_output_pdf(self) -> None:
        self.output_pdf_var.set("")
        self._log("Cleared output PDF selection")

    def _choose_export_tiff(self) -> None:
        p = filedialog.asksaveasfilename(title="Save TIFF", defaultextension=".tif", filetypes=[("TIFF","*.tif;*.tiff")])
        if p:
            self.export_tiff_var.set(p)
            self._log(f"Selected export TIFF: {p}")

    def _clear_export_tiff(self) -> None:
        self.export_tiff_var.set("")
        self._log("Cleared export TIFF selection")

    def _clear_all(self) -> None:
        self._clear_pdfs()
        self._clear_outer()
        self._clear_inners()
        self._clear_output_pdf()
        self._clear_export_tiff()
        # Reset all parameters to defaults
        self.nominal_height_var.set(3.0)
        self.gap_var.set(0.5)
        self.orientation_var.set("tangent")
        self.canvas_margin_var.set(5.0)
        self.canvas_bin_var.set(0.0)
        self.target_mb_var.set(900.0)
        self.tiff_mode_var.set("bilevel")
        self.tiff_comp_var.set("lzw")
        self.tiff_dpi_var.set(1200)
        self.optimize_dpi_var.set(0)
        self.max_canvas_pixels_var.set(100_000_000)
        # Reset page margins to default values
        self.page_margin_left_var.set(12.7)
        self.page_margin_top_var.set(6.35)
        self.page_margin_right_var.set(6.35)
        self.page_margin_bottom_var.set(6.35)
        self.log.delete("1.0", tk.END)
        self.progress.config(text="Idle")
        self._log("Cleared all selections and reset to defaults")

    def _run_async(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            self.progress.config(text="Running...")
            self.log.delete("1.0", tk.END)
            self.logger.debug("Starting GUI processing")

            if not self.input_pdfs:
                raise ValueError("Please add at least one input PDF.")
            if not self.outer_shape_var.get():
                raise ValueError("Please select an outer SVG.")
            if not self.export_tiff_var.get():
                raise ValueError("Please set a TIFF output file.")

            # Collect pages
            docs: List[fitz.Document] = []
            pages: List[PageSpec] = []
            for doc_idx, p in enumerate(self.input_pdfs):
                d = fitz.open(p)
                docs.append(d)
                for i in range(d.page_count):
                    r = d.load_page(i).rect
                    pages.append(PageSpec(doc_index=doc_idx, page_index=i, width_pt=r.width, height_pt=r.height))

            # Shapes and region - support both combined and separate SVG approaches
            if self.auto_detect_inner_var.get():
                # Use combined SVG auto-detection
                self.logger.debug(f"Auto-detecting shapes in: {self.outer_shape_var.get()}")
                outer, inners = parse_combined_svg(self.outer_shape_var.get(), self.min_inner_area_ratio_var.get())
                self.logger.debug(f"Auto-detected: 1 outer shape, {len(inners)} inner shapes")
            else:
                # Traditional separate file approach
                self.logger.debug(f"Parsing outer SVG: {self.outer_shape_var.get()}")
                outer = parse_svg_path(self.outer_shape_var.get())
                self.logger.debug(f"Parsing {len(self.inner_shapes)} inner SVGs")
                inners = [parse_svg_path(p) for p in self.inner_shapes]
            
            allowed = boolean_allowed_region(outer, inners)
            self.logger.debug(f"Allowed region bounds: {allowed.bounds}")
            if allowed.is_empty:
                raise ValueError("Allowed region is empty. Check shapes.")

            optimize_dpi = int(self.optimize_dpi_var.get())
            optimize_dpi = optimize_dpi if optimize_dpi > 0 else None
            
            max_canvas_pixels = int(self.max_canvas_pixels_var.get())
            
            # Auto-scale SVG if enabled
            if self.auto_scale_svg_var.get():
                self.logger.info("Auto-scaling SVG to fit all pages...")
                
                # Calculate total area needed for all pages at standard size
                standard_page_area = (1700 * 2200) / (25.4 * 25.4)  # mm²
                total_area_needed = len(pages) * standard_page_area * 1.2  # 20% buffer
                
                # Get current SVG area
                current_area = allowed.area
                
                if current_area > 0 and total_area_needed > current_area:
                    # Need to scale up
                    scale_factor = math.sqrt(total_area_needed / current_area)
                    self.logger.info(f"Scaling SVG by {scale_factor:.2f}x to fit {len(pages)} pages")
                    
                    from shapely.affinity import scale
                    outer = scale(outer, scale_factor, scale_factor)
                    inners = [scale(inner, scale_factor, scale_factor) for inner in inners]
                    allowed = boolean_allowed_region(outer, inners)
                    
                    self._log(f"SVG auto-scaled by {scale_factor:.2f}x to fit all pages\n")
            
            # Always use pixel-first approach - stay in pixel space after conversion
            self.logger.debug("Using pixel-first layout approach (staying in pixel space)")
            
            # Detect SVG aspect ratio for square canvas generation
            outer_bounds = outer.bounds
            current_width_mm = outer_bounds[2] - outer_bounds[0]
            current_height_mm = outer_bounds[3] - outer_bounds[1]
            svg_aspect_ratio = current_width_mm / current_height_mm
            
            # Calculate exact pixel dimensions needed
            required_width_px, required_height_px = calculate_required_region_size_pixels(
                len(pages), 1700, 2200, 50, target_aspect_ratio=svg_aspect_ratio
            )
            
            # Calculate and apply SVG scaling
            scale_factor = calculate_svg_scale_factor(
                current_width_mm, current_height_mm, required_width_px, required_height_px
            )
            
            self.logger.debug(f"Pixel-first scaling: {scale_factor:.4f}x to create {required_width_px:,}×{required_height_px:,} pixel canvas")
            
            # Apply scaling to shapes
            from shapely.affinity import scale
            outer = scale(outer, scale_factor, scale_factor)
            inners = [scale(inner, scale_factor, scale_factor) for inner in inners]
            allowed = boolean_allowed_region(outer, inners)
            
            # Use pixel layout - stay in pixel space from here on
            placements = calculate_pixel_layout(
                pages, allowed.bounds, 1700, 2200, 50
            )
            
            # Skip the old mm-based approaches
            if False and (self.use_optimized_packing_var.get() or self.adaptive_sizing_var.get()):
                # Advanced packing approaches
                self.logger.debug("Using optimized packing approach")
                
                if self.adaptive_sizing_var.get():
                    # Adaptive sizing for optimal space utilization
                    self.logger.debug(f"Using adaptive sizing with target fill ratio: {self.target_fill_ratio_var.get():.1%}")
                    placements = adaptive_size_packing(
                        pages, allowed, self.target_fill_ratio_var.get(), float(self.gap_var.get())
                    )
                else:
                    # Optimized packing with current settings
                    placements = optimized_packing_layout(
                        pages, allowed, float(self.nominal_height_var.get()), float(self.gap_var.get()),
                        size_flexibility=0.15,  # Allow 15% size variation for better packing
                        prioritize_space_filling=True,
                        outer_shape=outer,
                        inner_shapes=inners
                    )
            else:
                # Traditional layout approach
                self.logger.debug("Using traditional layout approach")
                placements = plan_layout_any_shape(
                    pages=pages,
                    allowed_region_mm=allowed,
                    nominal_height_mm=float(self.nominal_height_var.get()),
                    gap_mm=float(self.gap_var.get()),
                    orientation=self.orientation_var.get(),
                    optimize_for_dpi=optimize_dpi,
                    max_canvas_pixels=max_canvas_pixels,
                )
            if not placements:
                raise ValueError("No placements computed with current parameters.")

            # Scale SVG coordinates to reasonable physical dimensions
            minx, miny, maxx, maxy = allowed.bounds
            svg_width = maxx - minx
            svg_height = maxy - miny
            
            # Always use content-based sizing for better results
            # Small layouts get tighter fitting, larger layouts get some extra space
            self.logger.info(f"Using content-based canvas sizing for {len(placements)} placements")
            if True:  # Always use content-based sizing
                # Calculate actual content bounds from placements
                if placements:
                    content_minx = min(pl.center_xy_mm[0] - pl.width_mm/2 for pl in placements)
                    content_maxx = max(pl.center_xy_mm[0] + pl.width_mm/2 for pl in placements)
                    content_miny = min(pl.center_xy_mm[1] - pl.height_mm/2 for pl in placements)
                    content_maxy = max(pl.center_xy_mm[1] + pl.height_mm/2 for pl in placements)
                    
                    content_width = content_maxx - content_minx
                    content_height = content_maxy - content_miny
                    
                    self.logger.debug(f"Content bounds: ({content_minx:.1f}, {content_miny:.1f}) to ({content_maxx:.1f}, {content_maxy:.1f})")
                    self.logger.debug(f"Content dimensions: {content_width:.1f} x {content_height:.1f} mm")
                    self.logger.debug(f"SVG bounds: ({minx:.1f}, {miny:.1f}) to ({maxx:.1f}, {maxy:.1f})")
                    self.logger.debug(f"SVG dimensions: {svg_width:.1f} x {svg_height:.1f} mm")
                    
                    # Use content size + reasonable margin instead of full SVG bounds
                    margin = float(self.canvas_margin_var.get())
                    width_mm = content_width + 2 * margin
                    height_mm = content_height + 2 * margin
                    
                    # Ensure minimum canvas size for visibility
                    min_canvas_mm = 20.0  # At least 20mm per dimension
                    width_mm = max(width_mm, min_canvas_mm)
                    height_mm = max(height_mm, min_canvas_mm)
                    
                    self.logger.info(f"Content-based canvas: {width_mm:.1f}x{height_mm:.1f}mm (content: {content_width:.1f}x{content_height:.1f}mm)")
                else:
                    # Fallback for no placements
                    width_mm = 50.0  # Default small canvas
                    height_mm = 50.0
            else:
                # For larger layouts, scale SVG coordinates to reasonable size
                # Target maximum ~100mm for large dimension
                max_target_mm = 100.0
                scale_factor = min(max_target_mm / max(svg_width, svg_height), 1.0)
                
                if scale_factor < 1.0:
                    self.logger.info(f"Scaling SVG coordinates by {scale_factor:.3f} (from {svg_width:.1f}x{svg_height:.1f} to reasonable size)")
                    width_mm = svg_width * scale_factor + 2 * float(self.canvas_margin_var.get())
                    height_mm = svg_height * scale_factor + 2 * float(self.canvas_margin_var.get())
                else:
                    # SVG coordinates are already reasonable
                    width_mm = svg_width + 2 * float(self.canvas_margin_var.get())
                    height_mm = svg_height + 2 * float(self.canvas_margin_var.get())
            
            self.logger.debug(f"Canvas dimensions before binning: {width_mm:.2f}x{height_mm:.2f}mm")

            bin_mm = float(self.canvas_bin_var.get())
            if bin_mm > 0:
                def round_up(v: float, b: float) -> float:
                    n = int((v + b - 1e-9) // b)
                    return (n + (0 if abs(n * b - v) < 1e-9 else 1)) * b
                width_mm = round_up(width_mm, bin_mm)
                height_mm = round_up(height_mm, bin_mm)

            # Recenter
            cx = (minx + maxx) / 2.0
            cy = (miny + maxy) / 2.0
            for pl in placements:
                x, y = pl.center_xy_mm
                pl.center_xy_mm = (x - cx, y - cy)

            # DPI selection
            target_mb = float(self.target_mb_var.get()) if self.target_mb_var.get() else 0.0
            tiff_mode = self.tiff_mode_var.get()
            dpi = int(self.tiff_dpi_var.get())
            self.logger.debug(f"Initial DPI: {dpi}, Target MB: {target_mb}, Mode: {tiff_mode}")
            if target_mb and target_mb > 0:
                bpp = 1 if tiff_mode == "bilevel" else 8
                dpi = compute_dpi_for_target_mb(width_mm, height_mm, target_mb, bits_per_pixel=bpp)
                self.logger.debug(f"Calculated DPI from target MB: {dpi}")

            # Render
            self.logger.info(f"Starting render: {width_mm:.2f}x{height_mm:.2f}mm at {dpi} DPI")
            self.logger.debug(f"Number of placements: {len(placements)}")
            try:
                # Get page margins from GUI
                page_margins_mm = (
                    self.page_margin_left_var.get(),
                    self.page_margin_top_var.get(),
                    self.page_margin_right_var.get(),
                    self.page_margin_bottom_var.get()
                )
                
                raster = compose_raster_any_shape(
                    placements=placements,
                    doc_registry=docs,
                    dpi=dpi,
                    canvas_width_mm=width_mm,
                    canvas_height_mm=height_mm,
                    origin_center=True,
                    page_margins_mm=page_margins_mm,
                )
                self.logger.debug(f"Render successful, raster size: {raster.size}")
            except Exception as render_error:
                self.logger.error(f"Render failed: {type(render_error).__name__}: {render_error}")
                raise

            # Save outputs - PDF proof skipped for better performance and reliability
            # if self.output_pdf_var.get():
            #     save_pdf_proof(raster, self.output_pdf_var.get(), width_mm, height_mm)
            #     self._log(f"Wrote PDF proof: {self.output_pdf_var.get()}")

            if self.export_tiff_var.get():
                try:
                    if self.tiff_mode_var.get() == "bilevel":
                        save_tiff_1bit(raster, self.export_tiff_var.get(), compression=self.tiff_comp_var.get())
                    else:
                        save_tiff_gray(raster, self.export_tiff_var.get(), compression=self.tiff_comp_var.get())
                    self._log(f"Wrote TIFF: {self.export_tiff_var.get()}")
                except Exception as e:
                    error_msg = f"Error saving TIFF: {e}\n\nSuggestions:\n"
                    error_msg += "  - Reduce DPI (use a lower value in Fallback DPI)\n"
                    error_msg += "  - Use Target MB to automatically calculate safe DPI\n"
                    error_msg += "  - Reduce canvas size or number of pages\n"
                    error_msg += "  - Try using 'gray' mode instead of 'bilevel'"
                    self._log(error_msg)
                    raise ValueError(error_msg)

            for d in docs:
                d.close()

            self.progress.config(text="Done")
            messagebox.showinfo("NanoPrint", "Finished")
        except Exception as e:
            self.progress.config(text="Error")
            error_msg = str(e)
            
            # Log full exception details
            self.logger.error(f"Processing failed: {type(e).__name__}: {error_msg}")
            self.logger.debug("Full exception details:", exc_info=True)
            
            # Check if this is the "code=5" error
            if "code=5" in error_msg:
                self.logger.error("Error code 5 detected - image dimensions overflow")
                # Extract dimensions from error if possible
                import re
                dims_match = re.search(r'width=(\d+), height=(\d+)', error_msg)
                if dims_match:
                    width_px = int(dims_match.group(1))
                    height_px = int(dims_match.group(2))
                    self.logger.error(f"Attempted dimensions: {width_px}x{height_px} pixels")
                    self.logger.error(f"Total pixels: {width_px * height_px:,}")
            
            messagebox.showerror("NanoPrint", error_msg)
            self._log(f"Error: {error_msg}\n")

    def _log(self, msg: str) -> None:
        # Write to GUI text widget
        self.log.insert(tk.END, msg)
        self.log.see(tk.END)
        
        # Also write to Python logger (strip trailing newline if present)
        msg_stripped = msg.rstrip('\n')
        if msg_stripped:
            self.logger.info(msg_stripped)


def run_gui() -> None:
    app = NanoPrintGUI()
    app.mainloop()
