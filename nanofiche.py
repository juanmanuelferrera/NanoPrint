#!/usr/bin/env python3
"""
NanoFiche Image Prep - Windows App for optimal bin packing of raster images

Packs fixed-size image bins into envelope shapes (square, rectangle, circle, ellipse)
with optimal space utilization and user approval workflow.
"""

import sys
import tkinter as tk
from nanofiche.gui import NanoFicheGUI

def main():
    """Main entry point for NanoFiche Image Prep application."""
    root = tk.Tk()
    app = NanoFicheGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()