"""
Game-wide constants for 2048 Tile Adventure.

Pseudocode mapping:
  * Module 1  - GRID_SIZE, TARGET_TILE, spawn chances, LEADERBOARD_LIMIT
  * Module 10 - tile colour names and animation durations
  * Module 11 - milestone scores

This module is pure Python.  It must not depend on any GUI library, because
the whole ``core`` package must stay reusable by any front end.
"""

# ---------------------------------------------------------------------------
# Board and spawning (Module 1 and Module 5)
# ---------------------------------------------------------------------------
GRID_SIZE = 4
TARGET_TILE = 2048
SPAWN_CHANCE_2 = 90          # 90 % chance that a new tile is a 2
SPAWN_CHANCE_4 = 10          # 10 % chance that a new tile is a 4
LEADERBOARD_LIMIT = 10

DIRECTIONS = ("LEFT", "RIGHT", "UP", "DOWN")
MODES = ("Classic",)        # save data is grouped by mode; Classic is the only one
DEFAULT_PLAYER_NAME = "Player"
PLAYER_NAME_MAX_LENGTH = 12

# ---------------------------------------------------------------------------
# Milestones (Module 11)
# ---------------------------------------------------------------------------
# Milestones are score thresholds.  Each one fires once per game.
MILESTONES = (250, 750, 1500, 2500, 5000)

# ---------------------------------------------------------------------------
# Tile colour names (Module 10).  The UI converts these names to RGB values.
# ---------------------------------------------------------------------------
TILE_COLOR_NAMES = {
    0: "Empty Cell Color",
    2: "Lavender",
    4: "Sky Blue",
    8: "Turquoise",
    16: "Mint Green",
    32: "Golden Yellow",
    64: "Orange",
    128: "Coral Pink",
    256: "Violet",
    512: "Electric Blue",
    1024: "Deep Purple",
    2048: "Glowing Gold",
}


def get_tile_color(tile_value):
    """Pseudocode Module 10 - return the colour *name* for a tile value.

    The renderer maps this name to an RGB tuple, keeping colour decisions in
    the UI layer while the core still owns the documented mapping.
    """
    if tile_value >= TARGET_TILE:
        return "Glowing Gold"
    return TILE_COLOR_NAMES.get(tile_value, "Empty Cell Color")


# ---------------------------------------------------------------------------
# Animation durations (seconds) used by the UI.  Kept here so the timings are
# easy to tune in one place.
# ---------------------------------------------------------------------------
MOVE_ANIMATION_DURATION = 0.11
MERGE_ANIMATION_DURATION = 0.16
SPAWN_ANIMATION_DURATION = 0.16
SCREEN_FADE_DURATION = 0.22

# ---------------------------------------------------------------------------
# Save file
# ---------------------------------------------------------------------------
LEADERBOARD_FILENAME = "leaderboard.json"
