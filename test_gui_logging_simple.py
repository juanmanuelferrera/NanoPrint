#!/usr/bin/env python3
"""Simple test to verify GUI logging is working"""

import sys
import os
import time

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nanorosetta.cli import _setup_logging
import logging

def test_gui_logging():
    print("🧪 Testing GUI Logging Integration")
    print("=" * 60)
    
    # Setup logging (simulating what nanoprint.py does)
    _setup_logging()
    
    # Get a logger (simulating what the GUI does)
    logger = logging.getLogger("nanorosetta.gui")
    
    # Clear the log file to see fresh entries
    log_file = "nanorosetta_debug.log"
    if os.path.exists(log_file):
        with open(log_file, 'w') as f:
            f.write("")  # Clear the file
    
    # Test logging at different levels
    print("\n📝 Writing test log messages...")
    logger.info("GUI started - this simulates GUI startup")
    logger.info("User clicked 'Add PDFs' button")
    logger.debug("Debug: Processing file selection dialog")
    logger.info("Added 3 PDF files to the queue")
    logger.warning("Warning: Large file detected (>100MB)")
    logger.error("Error: Failed to load corrupted PDF")
    logger.info("Processing completed successfully")
    
    # Give a moment for logs to be written
    time.sleep(0.1)
    
    # Check if logs were written
    print("\n📄 Checking log file contents:")
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            contents = f.read()
            if contents:
                print(f"✅ Log file created with {len(contents)} bytes")
                print("\n📋 Log file contents:")
                print("-" * 60)
                print(contents)
                print("-" * 60)
                
                # Check for our specific messages
                expected_messages = [
                    "GUI started",
                    "Add PDFs",
                    "Processing completed"
                ]
                
                print("\n🔍 Verifying expected messages:")
                for msg in expected_messages:
                    if msg in contents:
                        print(f"  ✅ Found: '{msg}'")
                    else:
                        print(f"  ❌ Missing: '{msg}'")
            else:
                print("❌ Log file is empty")
    else:
        print("❌ Log file was not created")
    
    print("\n✨ Test complete!")

if __name__ == "__main__":
    test_gui_logging()