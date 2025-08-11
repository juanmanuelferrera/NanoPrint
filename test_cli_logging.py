#!/usr/bin/env python3
"""
Test the CLI logging functionality without dependencies
"""
import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_logging_setup():
    """Test the logging setup function from CLI"""
    
    # Import the logging setup function
    try:
        from nanorosetta.cli import _setup_logging
        print("✅ Successfully imported _setup_logging from CLI")
    except ImportError as e:
        print(f"❌ Could not import _setup_logging: {e}")
        return False
    
    # Test logging setup
    try:
        print("\n📝 Testing logging setup...")
        _setup_logging()
        print("✅ Logging setup completed successfully")
        
        # Test different log levels
        logging.info("This is an INFO message")
        logging.debug("This is a DEBUG message")
        logging.warning("This is a WARNING message")
        logging.error("This is an ERROR message")
        
        # Check if log file was created
        log_file = "nanorosetta_debug.log"
        if os.path.exists(log_file):
            print(f"✅ Log file '{log_file}' created successfully")
            
            # Show log file contents
            with open(log_file, 'r') as f:
                content = f.read()
                if content.strip():
                    print(f"📄 Log file content preview:")
                    print("-" * 50)
                    lines = content.strip().split('\n')
                    for line in lines[:5]:  # Show first 5 lines
                        print(line)
                    if len(lines) > 5:
                        print(f"... and {len(lines) - 5} more lines")
                    print("-" * 50)
                else:
                    print("⚠️  Log file exists but is empty")
        else:
            print(f"❌ Log file '{log_file}' was not created")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error during logging test: {e}")
        return False

def test_cli_parser():
    """Test the CLI argument parser"""
    try:
        from nanorosetta.cli import build_parser
        print("\n🔧 Testing CLI argument parser...")
        
        parser = build_parser()
        print("✅ Parser created successfully")
        
        # Test if --optimize-for-dpi parameter exists
        help_text = parser.format_help()
        if "--optimize-for-dpi" in help_text:
            print("✅ --optimize-for-dpi parameter is available")
        else:
            print("❌ --optimize-for-dpi parameter is missing")
            return False
            
        # Test basic argument parsing
        test_args = [
            "compose", 
            "--input", "test.pdf", 
            "--outer-shape", "test.svg",
            "--optimize-for-dpi", "200"
        ]
        
        try:
            args = parser.parse_args(test_args)
            print(f"✅ Arguments parsed successfully")
            print(f"   optimize_for_dpi = {getattr(args, 'optimize_for_dpi', 'NOT_FOUND')}")
            return True
        except Exception as e:
            print(f"❌ Argument parsing failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Could not import build_parser: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing NanoRosetta CLI functionality")
    print("=" * 50)
    
    # Test logging
    logging_ok = test_logging_setup()
    
    # Test parser
    parser_ok = test_cli_parser()
    
    print("\n📊 Test Results:")
    print(f"Logging functionality: {'✅ PASS' if logging_ok else '❌ FAIL'}")
    print(f"CLI parser functionality: {'✅ PASS' if parser_ok else '❌ FAIL'}")
    
    if logging_ok and parser_ok:
        print("\n🎉 All CLI tests passed! The fixes are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")