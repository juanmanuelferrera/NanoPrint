"""
GUI for NanoFiche Image Prep - Windows application for optimal bin packing.

Provides user interface for all required prompts and workflow management.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from .core import NanoFichePacker, EnvelopeShape, EnvelopeSpec, ImageBin, PackingResult
from .renderer import NanoFicheRenderer
from .logger import setup_logging


class NanoFicheGUI:
    """Main GUI class for NanoFiche Image Prep application."""
    
    def __init__(self, root: tk.Tk):
        """Initialize the GUI application."""
        self.root = root
        self.root.title("NanoFiche Image Prep v1.0")
        self.root.geometry("800x700")
        
        # Initialize components
        self.packer: Optional[NanoFichePacker] = None
        self.renderer = NanoFicheRenderer()
        self.image_bins: List[ImageBin] = []
        self.packing_result: Optional[PackingResult] = None
        
        # Setup logging
        setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Create GUI
        self.create_widgets()
        
        # Status
        self.update_status("Ready")
    
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        
        # Title
        title_label = ttk.Label(main_frame, text="NanoFiche Image Prep", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        row += 1
        
        # 1. Project Name
        ttk.Label(main_frame, text="1. Project Name:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.project_name_var = tk.StringVar(value="project1")
        ttk.Entry(main_frame, textvariable=self.project_name_var, width=30).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1
        
        # 2. Bin Dimensions
        ttk.Label(main_frame, text="2. Bin Dimensions (pixels):").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        bin_frame = ttk.Frame(main_frame)
        bin_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        ttk.Label(bin_frame, text="Width (a):").grid(row=0, column=0, sticky=tk.W)
        self.bin_width_var = tk.IntVar(value=1800)
        ttk.Entry(bin_frame, textvariable=self.bin_width_var, width=8).grid(row=0, column=1, padx=(5, 10))
        
        ttk.Label(bin_frame, text="Height (b):").grid(row=0, column=2, sticky=tk.W)
        self.bin_height_var = tk.IntVar(value=2300)
        ttk.Entry(bin_frame, textvariable=self.bin_height_var, width=8).grid(row=0, column=3, padx=(5, 0))
        row += 1
        
        # 3. Envelope Shape
        ttk.Label(main_frame, text="3. Envelope Shape:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        shape_frame = ttk.Frame(main_frame)
        shape_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        self.shape_var = tk.StringVar(value="rectangle")
        shapes = [("Square", "square"), ("Rectangle", "rectangle"), ("Circle", "circle"), ("Ellipse", "ellipse")]
        
        for i, (text, value) in enumerate(shapes):
            ttk.Radiobutton(shape_frame, text=text, variable=self.shape_var, 
                           value=value, command=self.on_shape_change).grid(row=0, column=i, padx=(0, 10))
        row += 1
        
        # Shape parameters (visible for rectangle/ellipse)
        self.params_frame = ttk.Frame(main_frame)
        self.params_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        ttk.Label(self.params_frame, text="Aspect Ratio (width/height):").grid(row=0, column=0, sticky=tk.W)
        self.aspect_ratio_var = tk.DoubleVar(value=1.29)
        ttk.Entry(self.params_frame, textvariable=self.aspect_ratio_var, width=8).grid(row=0, column=1, padx=(5, 0))
        
        self.on_shape_change()  # Set initial visibility
        row += 1
        
        # 4. Raster Files Folder
        ttk.Label(main_frame, text="4. Raster Files Folder:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        folder_frame.columnconfigure(0, weight=1)
        
        self.folder_path_var = tk.StringVar()
        ttk.Entry(folder_frame, textvariable=self.folder_path_var, state="readonly").grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Browse...", command=self.browse_folder).grid(row=0, column=1)
        row += 1
        
        # 5. Output Location
        ttk.Label(main_frame, text="5. Output Location:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=row, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_path_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_path_var, state="readonly").grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).grid(row=0, column=1)
        row += 1
        
        # Validation and Calculate button
        ttk.Button(main_frame, text="Validate & Calculate Layout", 
                  command=self.calculate_layout).grid(row=row, column=0, columnspan=3, pady=20)
        row += 1
        
        # Results display
        self.results_frame = ttk.LabelFrame(main_frame, text="Packing Results", padding="10")
        self.results_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        self.results_frame.columnconfigure(1, weight=1)
        
        # Results will be populated dynamically
        self.results_text = tk.Text(self.results_frame, height=8, width=80, state="disabled")
        results_scroll = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=results_scroll.set)
        
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        results_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        main_frame.rowconfigure(row, weight=1)
        self.results_frame.rowconfigure(0, weight=1)
        row += 1
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        self.preview_button = ttk.Button(button_frame, text="Generate Preview", 
                                        command=self.generate_preview, state="disabled")
        self.preview_button.grid(row=0, column=0, padx=(0, 10))
        
        self.approve_button = ttk.Button(button_frame, text="Approve & Generate Full TIFF", 
                                        command=self.approve_and_generate, state="disabled")
        self.approve_button.grid(row=0, column=1, padx=(0, 10))
        
        self.reject_button = ttk.Button(button_frame, text="Reject & Generate Thumbnail", 
                                       command=self.reject_and_generate, state="disabled")
        self.reject_button.grid(row=0, column=2)
        row += 1
        
        # Status bar
        self.status_var = tk.StringVar()
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief="sunken")
        status_label.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
    
    def on_shape_change(self):
        """Handle envelope shape selection change."""
        shape = self.shape_var.get()
        if shape in ["rectangle", "ellipse"]:
            # Show aspect ratio parameter
            for child in self.params_frame.winfo_children():
                child.grid()
        else:
            # Hide parameters for square and circle
            for child in self.params_frame.winfo_children():
                child.grid_remove()
    
    def browse_folder(self):
        """Browse for raster files folder."""
        folder_path = filedialog.askdirectory(title="Select Raster Files Folder")
        if folder_path:
            self.folder_path_var.set(folder_path)
    
    def browse_output(self):
        """Browse for output location."""
        output_path = filedialog.askdirectory(title="Select Output Location")
        if output_path:
            self.output_path_var.set(output_path)
    
    def calculate_layout(self):
        """Validate inputs and calculate optimal packing layout."""
        try:
            # Validate inputs
            if not self.validate_inputs():
                return
            
            self.update_status("Validating images...")
            
            # Initialize packer
            bin_width = self.bin_width_var.get()
            bin_height = self.bin_height_var.get()
            self.packer = NanoFichePacker(bin_width, bin_height)
            
            # Validate images
            folder_path = Path(self.folder_path_var.get())
            self.image_bins, errors = self.packer.validate_images(folder_path)
            
            if errors:
                error_msg = "\\n".join(errors[:10])  # Show first 10 errors
                if len(errors) > 10:
                    error_msg += f"\\n... and {len(errors) - 10} more errors"
                messagebox.showerror("Image Validation Errors", error_msg)
                return
            
            if not self.image_bins:
                messagebox.showerror("No Valid Images", "No valid images found in the selected folder.")
                return
            
            self.update_status("Calculating optimal layout...")
            
            # Create envelope specification
            shape = EnvelopeShape(self.shape_var.get())
            envelope_spec = EnvelopeSpec(
                shape=shape,
                aspect_ratio=self.aspect_ratio_var.get() if shape in [EnvelopeShape.RECTANGLE, EnvelopeShape.ELLIPSE] else 1.0
            )
            
            # Calculate packing
            self.packing_result = self.packer.pack_bins(self.image_bins, envelope_spec)
            
            # Display results
            self.display_results()
            
            # Enable action buttons
            self.preview_button.config(state="normal")
            self.approve_button.config(state="normal")
            self.reject_button.config(state="normal")
            
            self.update_status(f"Layout calculated successfully - {len(self.image_bins)} images ready for packing")
            
        except Exception as e:
            self.logger.error(f"Error calculating layout: {e}", exc_info=True)
            messagebox.showerror("Calculation Error", f"Error calculating layout: {str(e)}")
            self.update_status("Error calculating layout")
    
    def validate_inputs(self) -> bool:
        """Validate all input parameters."""
        # Project name
        if not self.project_name_var.get().strip():
            messagebox.showerror("Validation Error", "Project name is required.")
            return False
        
        # Bin dimensions
        try:
            bin_width = self.bin_width_var.get()
            bin_height = self.bin_height_var.get()
            if bin_width <= 0 or bin_height <= 0:
                raise ValueError("Dimensions must be positive")
        except (tk.TclError, ValueError):
            messagebox.showerror("Validation Error", "Bin dimensions must be positive integers.")
            return False
        
        # Aspect ratio for rectangle/ellipse
        shape = self.shape_var.get()
        if shape in ["rectangle", "ellipse"]:
            try:
                aspect_ratio = self.aspect_ratio_var.get()
                if aspect_ratio <= 0:
                    raise ValueError("Aspect ratio must be positive")
            except (tk.TclError, ValueError):
                messagebox.showerror("Validation Error", "Aspect ratio must be a positive number.")
                return False
        
        # Folder path
        if not self.folder_path_var.get():
            messagebox.showerror("Validation Error", "Please select a raster files folder.")
            return False
        
        # Output path
        if not self.output_path_var.get():
            messagebox.showerror("Validation Error", "Please select an output location.")
            return False
        
        return True
    
    def display_results(self):
        """Display packing results in the results text area."""
        if not self.packing_result:
            return
        
        result = self.packing_result
        
        # Format results text
        results_text = f"""Optimal Packing Solution:

• Number of rows: {result.rows}
• Number of columns: {result.columns}
• Canvas dimensions: {result.canvas_width:,} x {result.canvas_height:,} pixels
• Envelope dimensions: {result.envelope_width:.1f} x {result.envelope_height:.1f}
• Aspect ratio: {result.envelope_width/result.envelope_height:.3f}
• Total bins available: {result.total_bins}
• Images to be placed: {result.bins_placed}
• Packing efficiency: {result.efficiency:.1%}

Ready for preview generation."""
        
        # Update results display
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.insert("1.0", results_text)
        self.results_text.config(state="disabled")
    
    def generate_preview(self):
        """Generate preview TIFF (downsampled, max 4000px)."""
        if not self.packing_result:
            return
        
        try:
            self.update_status("Generating preview...")
            
            output_path = Path(self.output_path_var.get())
            project_name = self.project_name_var.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            preview_path = output_path / f"{project_name}_{timestamp}_preview.tif"
            
            # Generate preview with max 4000px dimension
            self.renderer.generate_preview(
                self.image_bins,
                self.packing_result,
                preview_path,
                max_dimension=4000
            )
            
            self.update_status(f"Preview generated: {preview_path}")
            messagebox.showinfo("Preview Generated", 
                              f"Preview TIFF generated successfully:\\n{preview_path}\\n\\nReview the preview and choose to Approve or Reject.")
            
        except Exception as e:
            self.logger.error(f"Error generating preview: {e}", exc_info=True)
            messagebox.showerror("Preview Error", f"Error generating preview: {str(e)}")
            self.update_status("Error generating preview")
    
    def approve_and_generate(self):
        """User approved - generate full resolution TIFF."""
        if not self.packing_result:
            return
        
        try:
            self.update_status("Generating full resolution TIFF...")
            
            output_path = Path(self.output_path_var.get())
            project_name = self.project_name_var.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            full_path = output_path / f"{project_name}_{timestamp}_full.tif"
            log_path = output_path / f"{project_name}_{timestamp}_full.log"
            
            # Generate full resolution TIFF
            self.renderer.generate_full_tiff(
                self.image_bins,
                self.packing_result,
                full_path,
                log_path,
                project_name,
                approved=True
            )
            
            self.update_status(f"Full TIFF generated: {full_path}")
            messagebox.showinfo("Full TIFF Generated", 
                              f"Full resolution TIFF generated successfully:\\n{full_path}\\n\\nLog file: {log_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating full TIFF: {e}", exc_info=True)
            messagebox.showerror("Generation Error", f"Error generating full TIFF: {str(e)}")
            self.update_status("Error generating full TIFF")
    
    def reject_and_generate(self):
        """User rejected - generate thumbnail TIFF."""
        if not self.packing_result:
            return
        
        try:
            self.update_status("Generating thumbnail TIFF...")
            
            output_path = Path(self.output_path_var.get())
            project_name = self.project_name_var.get()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            thumbnail_path = output_path / f"{project_name}_{timestamp}_thumbnail.tif"
            log_path = output_path / f"{project_name}_{timestamp}_thumbnail.log"
            
            # Generate thumbnail TIFF (same as preview)
            self.renderer.generate_thumbnail_tiff(
                self.image_bins,
                self.packing_result,
                thumbnail_path,
                log_path,
                project_name,
                approved=False
            )
            
            self.update_status(f"Thumbnail TIFF generated: {thumbnail_path}")
            messagebox.showinfo("Thumbnail Generated", 
                              f"Thumbnail TIFF generated:\\n{thumbnail_path}\\n\\nLog file: {log_path}")
            
        except Exception as e:
            self.logger.error(f"Error generating thumbnail: {e}", exc_info=True)
            messagebox.showerror("Generation Error", f"Error generating thumbnail: {str(e)}")
            self.update_status("Error generating thumbnail")
    
    def update_status(self, message: str):
        """Update status bar message."""
        self.status_var.set(message)
        self.root.update_idletasks()