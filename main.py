"""
2048 Tile Adventure - program entry point.

Run from the project folder::

    python main.py

Requirements: Python 3.10+ and pygame (pygame-ce also works).  Everything else
comes from the Python standard library.
"""

import sys


def main():
    """Start the Pygame application and return a process exit code."""
    try:
        import pygame  # noqa: F401  (checked early for a friendly error)
    except ImportError:
        print("Pygame is not installed. Run:  pip install -r requirements.txt")
        return 1

    from ui.app import main_game_loop

    return main_game_loop()


if __name__ == "__main__":
    sys.exit(main())
