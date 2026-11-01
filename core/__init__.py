"""
Pure-Python game core for 2048 Tile Adventure.

This package never imports a GUI library.  It can be reused by the desktop UI, by the
unit tests, or by a future web front-end.

Typical use::

    from core.game_flow import initialize_game
    from core.board import move_tiles

    state = initialize_game("Ada", "Classic", now=0.0)
    events = move_tiles(state, "LEFT", now=0.0)
    for event in events:
        print(event.kind, event.data)
"""

__version__ = "1.0.0"
