"""
2048 Tile Adventure - program entry point (desktop and web).

Run from the project folder:

    python main.py
"""
import asyncio

import pygame  # noqa: F401  (top-level import so Pygbag can detect it)

from ui.app import main_game_loop


async def main():
    """Start the Pygame application."""
    return await main_game_loop()


asyncio.run(main())