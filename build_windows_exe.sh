#!/bin/bash

# Build Windows EXE using Docker on macOS
# This script creates a Windows executable from macOS

echo "Building Windows EXE using Docker..."

# Create a temporary Dockerfile for Windows build
cat > Dockerfile.windows << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wine \
    wine32 \
    wine64 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install pyinstaller==6.6.0

# Copy source code
COPY . /app
WORKDIR /app

# Build the EXE using Wine
RUN wine python -m pip install -r requirements.txt
RUN wine python -m pip install pyinstaller==6.6.0
RUN wine pyinstaller --windowed --onefile --name NanoPrint --collect-all numpy --collect-all shapely nanoprint.py

# Copy the built EXE to host
CMD ["cp", "dist/NanoPrint.exe", "/output/"]
EOF

# Build the Docker image
docker build -f Dockerfile.windows -t nanoprint-windows-builder .

# Create output directory
mkdir -p dist

# Run the build and copy the EXE
docker run --rm -v $(pwd)/dist:/output nanoprint-windows-builder

# Clean up
rm Dockerfile.windows

echo "Windows EXE built successfully!"
echo "Check dist/NanoPrint.exe"
