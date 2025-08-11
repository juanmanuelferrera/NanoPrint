#!/usr/bin/env python3
"""
Simple test script to check logging functionality without dependencies
"""
import logging
import sys
import os

def _setup_logging() -> None:
    """Setup logging to both file and console."""
    log_file = "nanorosetta_debug.log"
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler - detailed logs
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    # Console handler - important messages only
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.info(f"Logging initialized. Debug log: {log_file}")

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
            print("\nLog file content:")
            print("-" * 50)
            print(content)
            print("-" * 50)
    else:
        print("❌ Log file NOT created")
        
    print(f"\nCurrent working directory: {os.getcwd()}")
    print("Log files in current directory:")
    for f in os.listdir("."):
        if f.endswith(".log"):
            print(f"  📄 {f}")

if __name__ == "__main__":
    test_logging()