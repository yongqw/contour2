#!/usr/bin/env python3
"""
Quick launch script for Terrain Tunneling Calculator GUI.

This script provides an easy way to start the GUI application.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
script_dir = Path(__file__).parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Launch the GUI application."""
    # Change to script directory
    os.chdir(script_dir)

    # Import and run main application
    try:
        import main
        # Simulate command line arguments for GUI mode
        sys.argv = ["main.py", "--gui"]
        main.main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()