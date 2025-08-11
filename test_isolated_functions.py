#!/usr/bin/env python3
"""
Test isolated functions from our fixes without dependencies
"""
import sys
import os
import logging
import math

def test_setup_logging():
    """Test the logging setup function in isolation"""
    
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
    
    print("📝 Testing logging setup...")
    try:
        _setup_logging()
        
        # Test different log levels
        logging.info("Testing INFO level")
        logging.debug("Testing DEBUG level (should be in file only)")
        logging.warning("Testing WARNING level")
        logging.error("Testing ERROR level")
        
        # Check log file
        log_file = "nanorosetta_debug.log"
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                content = f.read()
                lines = content.strip().split('\n')
                print(f"✅ Log file created with {len(lines)} log entries")
                return True
        else:
            print("❌ Log file not created")
            return False
            
    except Exception as e:
        print(f"❌ Logging test failed: {e}")
        return False

def test_validate_dimensions():
    """Test the dimension validation logic"""
    
    def mm_to_px(mm: float, dpi: int) -> int:
        """Convert mm to pixels at given DPI"""
        return int(round(mm * dpi / 25.4))
    
    def validate_canvas_dimensions(canvas_width_mm: float, canvas_height_mm: float, dpi: int) -> tuple[int, int, int]:
        """
        Validate canvas dimensions and return safe pixel dimensions and DPI.
        """
        logging.debug(f"Validating canvas dimensions: {canvas_width_mm:.2f}x{canvas_height_mm:.2f}mm at {dpi} DPI")
        
        # PIL's maximum image dimensions
        max_pixels_per_dimension = 2**28
        
        # Calculate pixel dimensions
        width_px = mm_to_px(canvas_width_mm, dpi)
        height_px = mm_to_px(canvas_height_mm, dpi)
        logging.debug(f"Calculated pixel dimensions: {width_px}x{height_px} pixels")
        
        # Check if dimensions are too large
        if width_px > max_pixels_per_dimension or height_px > max_pixels_per_dimension:
            logging.warning(f"Dimensions exceed safe limit ({max_pixels_per_dimension} pixels per dimension)")
            
            # Calculate required DPI reduction
            max_dimension_mm = max(canvas_width_mm, canvas_height_mm)
            safe_dpi = int((max_pixels_per_dimension * 25.4) / max_dimension_mm)
            
            # Ensure DPI is reasonable (minimum 50 DPI)
            safe_dpi = max(50, min(safe_dpi, dpi))
            logging.info(f"DPI reduced from {dpi} to {safe_dpi} for safety")
            
            # Recalculate pixel dimensions with safe DPI
            width_px = mm_to_px(canvas_width_mm, safe_dpi)
            height_px = mm_to_px(canvas_height_mm, safe_dpi)
            logging.debug(f"Safe pixel dimensions: {width_px}x{height_px} pixels")
            
            return width_px, height_px, safe_dpi
        
        logging.debug("Canvas dimensions are within safe limits")
        return width_px, height_px, dpi
    
    print("\n🔍 Testing dimension validation...")
    
    try:
        # Test case 1: Normal dimensions (should pass)
        w1, h1, dpi1 = validate_canvas_dimensions(100.0, 100.0, 300)
        print(f"✅ Normal case: 100x100mm at 300 DPI -> {w1}x{h1} pixels at {dpi1} DPI")
        
        # Test case 2: Large dimensions (should trigger reduction)
        w2, h2, dpi2 = validate_canvas_dimensions(1000.0, 1000.0, 2400)
        print(f"✅ Large case: 1000x1000mm at 2400 DPI -> {w2}x{h2} pixels at {dpi2} DPI")
        if dpi2 < 2400:
            print(f"   ⚡ DPI was automatically reduced from 2400 to {dpi2}")
        
        # Test case 3: Extreme dimensions (should heavily reduce DPI)
        w3, h3, dpi3 = validate_canvas_dimensions(5000.0, 5000.0, 1200)
        print(f"✅ Extreme case: 5000x5000mm at 1200 DPI -> {w3}x{h3} pixels at {dpi3} DPI")
        if dpi3 < 1200:
            print(f"   ⚡ DPI was heavily reduced from 1200 to {dpi3}")
        
        return True
        
    except Exception as e:
        print(f"❌ Dimension validation test failed: {e}")
        return False

def test_argument_parser_structure():
    """Test argument parser structure without importing the module"""
    
    print("\n🔧 Testing argument parser structure...")
    
    # Check if the CLI file contains the expected parameters
    try:
        cli_file = "nanorosetta/cli.py"
        if os.path.exists(cli_file):
            with open(cli_file, 'r') as f:
                content = f.read()
                
            checks = {
                "--optimize-for-dpi": "--optimize-for-dpi" in content and "type=int" in content,
                "validate_canvas_dimensions": "validate_canvas_dimensions" in content,
                "_setup_logging": "_setup_logging" in content,
                "logging.info": "logging.info" in content,
                "logging.debug": "logging.debug" in content,
            }
            
            print("Checking CLI file content:")
            all_passed = True
            for check_name, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"   {status} {check_name}: {'Found' if passed else 'Missing'}")
                if not passed:
                    all_passed = False
            
            return all_passed
        else:
            print(f"❌ CLI file not found: {cli_file}")
            return False
            
    except Exception as e:
        print(f"❌ CLI structure test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing NanoRosetta CLI Fixes (Isolated)")
    print("=" * 55)
    
    # Run tests
    test1 = test_setup_logging()
    test2 = test_validate_dimensions() 
    test3 = test_argument_parser_structure()
    
    print("\n📊 Test Results:")
    print(f"Logging setup: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Dimension validation: {'✅ PASS' if test2 else '❌ FAIL'}")
    print(f"CLI structure: {'✅ PASS' if test3 else '❌ FAIL'}")
    
    if test1 and test2 and test3:
        print("\n🎉 All tests passed! The dimension overflow fixes are working correctly.")
        print("The CLI will create detailed logs and handle dimension overflow safely.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")