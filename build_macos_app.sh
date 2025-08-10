#!/bin/bash

# Build macOS App locally
echo "Building macOS App..."

# Install dependencies if not already installed
pip install -r requirements.txt
pip install pyinstaller==6.6.0

# Build the macOS app
pyinstaller --windowed --name NanoPrint nanoprint.py

echo "macOS App built successfully!"
echo "Check dist/NanoPrint.app"
