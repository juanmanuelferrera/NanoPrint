#!/bin/bash

# Test script to demonstrate DPI optimization with different values
echo "Testing DPI optimization with different values..."

# Create output directory
mkdir -p test_output

# Test with 200 DPI
echo "Testing with 200 DPI..."
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 200 \
  --export-tiff ./test_output/test_200dpi.tiff \
  --output ./test_output/test_200dpi.pdf

# Test with 600 DPI
echo "Testing with 600 DPI..."
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 600 \
  --export-tiff ./test_output/test_600dpi.tiff \
  --output ./test_output/test_600dpi.pdf

# Test with 1200 DPI
echo "Testing with 1200 DPI..."
python -m nanorosetta.cli compose \
  --input ./examples/sample.pdf \
  --outer-shape ./examples/outer_rect.svg \
  --inner-shape ./examples/inner_circle.svg \
  --optimize-for-dpi 1200 \
  --export-tiff ./test_output/test_1200dpi.tiff \
  --output ./test_output/test_1200dpi.pdf

echo "Tests completed! Check test_output/ directory for results."
