"""
Game-wide constants for 2048 Tile Adventure.

Pseudocode mapping:
  * Module 1  - GRID_SIZE, TARGET_TILE, spawn chances, LEADERBOARD_LIMIT
  * Module 8  - Survival durations
  * Module 9  - infection spread interval
  * Module 10 - tile colour names and animation durations
  * Module 11 - achievement definitions and milestone scores

This module is pure Python.  It must not depend on any GUI library, because
the whole ``core`` package is reused by the desktop and web front-ends.
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
MODES = ("Classic", "Survival", "Infection")
DEFAULT_PLAYER_NAME = "Player"
PLAYER_NAME_MAX_LENGTH = 12

# ---------------------------------------------------------------------------
# Survival mode (Module 8)
# ---------------------------------------------------------------------------
SURVIVAL_TOTAL_TIME = 60.0        # seconds in one Survival round
SURVIVAL_FIRST_BLOCK = 10.0       # first temporary block after 10 seconds
SURVIVAL_BLOCK_INTERVAL = 10.0    # then every 10 seconds
SURVIVAL_BLOCK_DURATION = 3.0     # each block lasts 3 seconds
BLOCK_WARNING_SECONDS = 1.0       # UI starts flashing 1 second before a block

# When True, tiles inside the blocked row/column cannot move or merge during
# the 3-second block.  When False, a block only stops new tiles from spawning
# there.  See README.md ("Implementation notes").
BLOCK_FREEZES_TILES = True

# ---------------------------------------------------------------------------
# Infection mode (Module 9)
# ---------------------------------------------------------------------------
INFECTION_SPREAD_EVERY = 3   # infection spreads after every 3rd successful move

# ---------------------------------------------------------------------------
# Achievements and milestones (Module 11)
# ---------------------------------------------------------------------------
# Each achievement has a target and a metric so the UI can draw a progress bar.
#   score        -> current score
#   largest_tile -> biggest tile on the board
#   merges       -> number of merges made
ACHIEVEMENTS = {
    "Score 100": {
        "description": "Reach a score of 100.",
        "target": 100,
        "metric": "score",
    },
    "Score 500": {
        "description": "Reach a score of 500.",
        "target": 500,
        "metric": "score",
    },
    "Score 1000": {
        "description": "Reach a score of 1000.",
        "target": 1000,
        "metric": "score",
    },
    "Reach 2048": {
        "description": "Create the legendary 2048 tile.",
        "target": TARGET_TILE,
        "metric": "largest_tile",
    },
    "First Merge": {
        "description": "Merge two tiles for the first time.",
        "target": 1,
        "metric": "merges",
    },
}
ACHIEVEMENT_ORDER = tuple(ACHIEVEMENTS)   # keeps the UI order stable

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
ROBOT_THINKING_TIME = 0.55

# ---------------------------------------------------------------------------
# Save file
# ---------------------------------------------------------------------------
LEADERBOARD_FILENAME = "leaderboard.json"
