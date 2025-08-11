import sys
from nanorosetta.cli import main as cli_main, _setup_logging
from nanorosetta.gui import run_gui

if __name__ == "__main__":
    # Initialize logging for both CLI and GUI
    _setup_logging()
    
    if len(sys.argv) > 1:
        raise SystemExit(cli_main())
    run_gui()
