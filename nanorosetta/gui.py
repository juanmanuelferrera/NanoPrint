from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import List

import fitz  # PyMuPDF

from .geometry import parse_svg_path, boolean_allowed_region
from .layout import PageSpec, plan_layout_any_shape
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

        row = 0
        ttk.Label(frm, text="Input PDFs").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Button(frm, text="Add PDFs", command=self._choose_pdfs).grid(row=row, column=1, sticky=tk.W, **pad)
        self.pdf_list = tk.Listbox(frm, height=3)
        self.pdf_list.grid(row=row, column=2, columnspan=3, sticky=tk.EW, **pad)

        row += 1
        ttk.Label(frm, text="Outer SVG").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.outer_shape_var).grid(row=row, column=1, columnspan=3, sticky=tk.EW, **pad)
        ttk.Button(frm, text="Browse", command=self._choose_outer).grid(row=row, column=4, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Inner SVGs").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Button(frm, text="Add Inner", command=self._choose_inners).grid(row=row, column=1, sticky=tk.W, **pad)
        self.inner_list = tk.Listbox(frm, height=3)
        self.inner_list.grid(row=row, column=2, columnspan=3, sticky=tk.EW, **pad)

        # Options
        row += 1
        self.nominal_height_var = tk.DoubleVar(value=3.0)
        self.gap_var = tk.DoubleVar(value=0.5)
        self.orientation_var = tk.StringVar(value="tangent")
        self.canvas_margin_var = tk.DoubleVar(value=5.0)
        self.canvas_bin_var = tk.DoubleVar(value=0.0)
        self.target_mb_var = tk.DoubleVar(value=900.0)
        self.tiff_mode_var = tk.StringVar(value="bilevel")
        self.tiff_comp_var = tk.StringVar(value="lzw")
        self.tiff_dpi_var = tk.IntVar(value=1200)
        self.optimize_dpi_var = tk.IntVar(value=0)  # 0 = disabled, >0 = DPI value

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
        ttk.Label(frm, text="Orientation").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Combobox(frm, textvariable=self.orientation_var, values=["tangent", "upright"], width=10).grid(row=row, column=1, sticky=tk.W, **pad)
        ttk.Label(frm, text="Canvas Margin (mm)").grid(row=row, column=2, sticky=tk.E, **pad)
        ttk.Entry(frm, textvariable=self.canvas_margin_var, width=10).grid(row=row, column=3, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Canvas Bin (mm)").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.canvas_bin_var, width=10).grid(row=row, column=1, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Output PDF Proof").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.output_pdf_var).grid(row=row, column=1, columnspan=3, sticky=tk.EW, **pad)
        ttk.Button(frm, text="Browse", command=self._choose_output_pdf).grid(row=row, column=4, sticky=tk.W, **pad)

        row += 1
        ttk.Label(frm, text="Export TIFF").grid(row=row, column=0, sticky=tk.W, **pad)
        ttk.Entry(frm, textvariable=self.export_tiff_var).grid(row=row, column=1, columnspan=3, sticky=tk.EW, **pad)
        ttk.Button(frm, text="Browse", command=self._choose_export_tiff).grid(row=row, column=4, sticky=tk.W, **pad)

        # Run
        row += 1
        ttk.Button(frm, text="Run", command=self._run_async).grid(row=row, column=0, sticky=tk.W, **pad)
        self.progress = ttk.Label(frm, text="Idle")
        self.progress.grid(row=row, column=1, columnspan=3, sticky=tk.W, **pad)

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
            self.input_pdfs.extend(list(paths))
            self.pdf_list.delete(0, tk.END)
            for p in self.input_pdfs:
                self.pdf_list.insert(tk.END, p)

    def _choose_outer(self) -> None:
        p = filedialog.askopenfilename(title="Select outer SVG", filetypes=[("SVG","*.svg")])
        if p:
            self.outer_shape_var.set(p)

    def _choose_inners(self) -> None:
        paths = filedialog.askopenfilenames(title="Select inner SVG(s)", filetypes=[("SVG","*.svg")])
        if paths:
            self.inner_shapes.extend(list(paths))
            self.inner_list.delete(0, tk.END)
            for p in self.inner_shapes:
                self.inner_list.insert(tk.END, p)

    def _choose_output_pdf(self) -> None:
        p = filedialog.asksaveasfilename(title="Save PDF proof", defaultextension=".pdf", filetypes=[("PDF","*.pdf")])
        if p:
            self.output_pdf_var.set(p)

    def _choose_export_tiff(self) -> None:
        p = filedialog.asksaveasfilename(title="Save TIFF", defaultextension=".tif", filetypes=[("TIFF","*.tif;*.tiff")])
        if p:
            self.export_tiff_var.set(p)

    def _run_async(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            self.progress.config(text="Running...")
            self.log.delete("1.0", tk.END)

            if not self.input_pdfs:
                raise ValueError("Please add at least one input PDF.")
            if not self.outer_shape_var.get():
                raise ValueError("Please select an outer SVG.")
            if not self.export_tiff_var.get() and not self.output_pdf_var.get():
                raise ValueError("Please set an output (TIFF and/or PDF proof).")

            # Collect pages
            docs: List[fitz.Document] = []
            pages: List[PageSpec] = []
            for doc_idx, p in enumerate(self.input_pdfs):
                d = fitz.open(p)
                docs.append(d)
                for i in range(d.page_count):
                    r = d.load_page(i).rect
                    pages.append(PageSpec(doc_index=doc_idx, page_index=i, width_pt=r.width, height_pt=r.height))

            # Shapes and region
            outer = parse_svg_path(self.outer_shape_var.get())
            inners = [parse_svg_path(p) for p in self.inner_shapes]
            allowed = boolean_allowed_region(outer, inners)
            if allowed.is_empty:
                raise ValueError("Allowed region is empty. Check shapes.")

            optimize_dpi = int(self.optimize_dpi_var.get())
            optimize_dpi = optimize_dpi if optimize_dpi > 0 else None
            
            placements = plan_layout_any_shape(
                pages=pages,
                allowed_region_mm=allowed,
                nominal_height_mm=float(self.nominal_height_var.get()),
                gap_mm=float(self.gap_var.get()),
                orientation=self.orientation_var.get(),
                optimize_for_dpi=optimize_dpi,
            )
            if not placements:
                raise ValueError("No placements computed with current parameters.")

            # Canvas from bounds + margin
            minx, miny, maxx, maxy = allowed.bounds
            width_mm = (maxx - minx) + 2 * float(self.canvas_margin_var.get())
            height_mm = (maxy - miny) + 2 * float(self.canvas_margin_var.get())

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
            if target_mb and target_mb > 0:
                bpp = 1 if tiff_mode == "bilevel" else 8
                dpi = compute_dpi_for_target_mb(width_mm, height_mm, target_mb, bits_per_pixel=bpp)

            # Render
            raster = compose_raster_any_shape(
                placements=placements,
                doc_registry=docs,
                dpi=dpi,
                canvas_width_mm=width_mm,
                canvas_height_mm=height_mm,
                origin_center=True,
            )

            if self.output_pdf_var.get():
                save_pdf_proof(raster, self.output_pdf_var.get(), width_mm, height_mm)
                self._log(f"Wrote PDF proof: {self.output_pdf_var.get()}\n")

            if self.export_tiff_var.get():
                comp = self.tiff_comp_var.get()
                if tiff_mode == "bilevel":
                    save_tiff_1bit(raster, self.export_tiff_var.get(), dpi, compression=comp)
                else:
                    save_tiff_gray(raster, self.export_tiff_var.get(), dpi, compression=comp)
                self._log(f"Wrote TIFF: {self.export_tiff_var.get()}\n")

            for d in docs:
                d.close()

            self.progress.config(text="Done")
            messagebox.showinfo("NanoPrint", "Finished")
        except Exception as e:
            self.progress.config(text="Error")
            messagebox.showerror("NanoPrint", str(e))
            self._log(f"Error: {e}\n")

    def _log(self, msg: str) -> None:
        self.log.insert(tk.END, msg)
        self.log.see(tk.END)


def run_gui() -> None:
    app = NanoPrintGUI()
    app.mainloop()
