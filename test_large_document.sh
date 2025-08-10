#!/bin/bash
# Test script for large document handling with memory management
echo "Testing large document handling with memory management..."

# Create a test directory
mkdir -p test_large_output

echo "Testing with 200 DPI and 50M pixel limit (recommended for large docs)..."
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 200 \
  --max-canvas-pixels 50000000 \
  --export-tiff ./test_large_output/large_200dpi_50M.tiff \
  --output ./test_large_output/large_200dpi_50M.pdf

echo "Testing with 200 DPI and 25M pixel limit (for very large docs)..."
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 200 \
  --max-canvas-pixels 25000000 \
  --export-tiff ./test_large_output/large_200dpi_25M.tiff \
  --output ./test_large_output/large_200dpi_25M.pdf

echo "Testing with 150 DPI and 100M pixel limit (high quality for large docs)..."
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 150 \
  --max-canvas-pixels 100000000 \
  --export-tiff ./test_large_output/large_150dpi_100M.tiff \
  --output ./test_large_output/large_150dpi_100M.pdf

echo "Large document tests completed!"
echo "Check test_large_output/ directory for results."
echo ""
echo "Recommended settings for 2,000 page documents:"
echo "- DPI: 200 (good for text, reasonable file size)"
echo "- Max Canvas Pixels: 50,000,000 (prevents memory issues)"
echo "- This gives ~2,000x2,000 pixels per page"
echo "- Total canvas: ~100,000x100,000 pixels"
