#!/usr/bin/env python3
"""
Test to verify logging works with the GUI entry point
"""
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_gui_entry_logging():
    """Test if the GUI properly initializes logging"""
    
    print("🔍 Testing GUI logging integration...")
    
    # Check if nanoprint.py exists and what it contains
    gui_file = "nanoprint.py"
    if os.path.exists(gui_file):
        print(f"✅ Found {gui_file}")
        
        with open(gui_file, 'r') as f:
            content = f.read()
            
        # Check for logging setup
        checks = {
            "_setup_logging": "_setup_logging" in content,
            "logging import": "import logging" in content or "from nanorosetta.cli import" in content,
            "main function": "def main" in content or "cli_main" in content,
        }
        
        print("Checking GUI file content:")
        for check_name, found in checks.items():
            status = "✅" if found else "❌"
            print(f"   {status} {check_name}: {'Found' if found else 'Missing'}")
            
        # Show relevant lines
        lines = content.split('\n')
        print(f"\n📄 First 15 lines of {gui_file}:")
        for i, line in enumerate(lines[:15], 1):
            print(f"   {i:2d}: {line}")
            
        return any(checks.values())
    else:
        print(f"❌ {gui_file} not found")
        return False

def test_cli_direct_logging():
    """Test CLI logging directly"""
    print(f"\n🧪 Testing CLI logging directly...")
    
    try:
        # Try to run the CLI main function with logging
        from nanorosetta.cli import main, _setup_logging
        print("✅ Successfully imported CLI functions")
        
        # Setup logging manually
        print("📝 Setting up logging...")
        _setup_logging()
        print("✅ Logging setup completed")
        
        # Check for log file
        log_file = "nanorosetta_debug.log"
        if os.path.exists(log_file):
            print(f"✅ Log file created: {log_file}")
            
            with open(log_file, 'r') as f:
                content = f.read()
                if content.strip():
                    print(f"📄 Log file content:")
                    print("-" * 40)
                    print(content)
                    print("-" * 40)
                    return True
                else:
                    print("⚠️  Log file exists but is empty")
        else:
            print(f"❌ Log file not created")
            
        return False
        
    except ImportError as e:
        print(f"❌ Could not import CLI: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing CLI logging: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing NanoRosetta GUI/CLI Logging Integration")
    print("=" * 60)
    
    # Test GUI integration
    gui_ok = test_gui_entry_logging()
    
    # Test CLI logging directly
    cli_ok = test_cli_direct_logging()
    
    print(f"\n📊 Results:")
    print(f"GUI logging integration: {'✅ OK' if gui_ok else '❌ NEEDS FIX'}")
    print(f"CLI logging functionality: {'✅ OK' if cli_ok else '❌ NEEDS FIX'}")
    
    if cli_ok and not gui_ok:
        print(f"\n💡 Issue: CLI logging works but GUI doesn't call it properly")
        print(f"   The GUI (nanoprint.py) needs to call _setup_logging()")
    elif not cli_ok:
        print(f"\n💡 Issue: CLI logging is not working - check dependencies")
    else:
        print(f"\n🎉 Logging should work correctly!")