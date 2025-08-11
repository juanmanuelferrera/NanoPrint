#!/usr/bin/env python3
"""
Simple test script to check logging functionality
"""
import sys
import os
sys.path.insert(0, '.')

from nanorosetta.cli import _setup_logging
import logging

def test_logging():
    print("Testing logging setup...")
    
    # Setup logging
    _setup_logging()
    
    # Test logging
    logging.info("This is an info message")
    logging.debug("This is a debug message")
    logging.warning("This is a warning message")
    logging.error("This is an error message")
    
    # Check if log file was created
    if os.path.exists("nanorosetta_debug.log"):
        print("✅ Log file created successfully!")
        with open("nanorosetta_debug.log", "r") as f:
            content = f.read()
            print("Log file content:")
            print(content)
    else:
        print("❌ Log file NOT created")
        
    print("Current working directory:", os.getcwd())
    print("Files in current directory:")
    for f in os.listdir("."):
        if f.endswith(".log"):
            print(f"  📄 {f}")

if __name__ == "__main__":
    test_logging()