import sys
from nanorosetta.cli import main as cli_main
from nanorosetta.gui import run_gui

if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(cli_main())
    run_gui()
