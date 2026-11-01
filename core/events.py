"""
Small, front-end agnostic event objects.

The core never draws or plays audio.  Instead it returns a list of
``GameEvent`` objects and the UI (desktop or web) decides what to do:
start a slide animation, play a sound, show a toast, open a screen, ...

Event kinds used by the project
-------------------------------
moved                - a valid move changed the board
merged               - two tiles merged (one event per merge)
spawned              - a new tile appeared
achievement_unlocked - an achievement was earned for the first time this game
milestone_reached    - the score crossed a configured milestone
won                  - the 2048 tile appeared; the UI should show the win prompt
game_over            - the round ended (data["reason"] explains why)
infection_spread     - infection jumped to new cells (data["cells"])
block_started        - a Survival row/column was frozen (data["cells"])
block_ended          - the Survival block expired
robot_thinking       - the robot started solving
robot_solved         - the robot finished its turn
"""

from dataclasses import dataclass, field


# String constants prevent typos in comparisons.
MOVED = "moved"
MERGED = "merged"
SPAWNED = "spawned"
ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
MILESTONE_REACHED = "milestone_reached"
WON = "won"
GAME_OVER = "game_over"
INFECTION_SPREAD = "infection_spread"
BLOCK_STARTED = "block_started"
BLOCK_ENDED = "block_ended"
ROBOT_THINKING = "robot_thinking"
ROBOT_SOLVED = "robot_solved"


@dataclass(frozen=True)
class GameEvent:
    """A single thing that happened, with optional extra data.

    ``kind`` is one of the string constants above.  ``data`` is a plain dict
    so any front-end can read it without importing a GUI library.
    """

    kind: str
    data: dict = field(default_factory=dict)


def make_event(kind, **data):
    """Convenience helper: make_event(MOVED, direction="LEFT")."""
    return GameEvent(kind=kind, data=data)
