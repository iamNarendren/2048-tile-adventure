"""
The complete, front-end independent game state (Pseudocode Modules 1-6).

Everything the game needs to know lives in this dataclass: the board, score,
win/game-over flags and so on.  The desktop UI only reads and draws these
values; it never stores game rules of its own.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from core.board import MoveResult, SpawnResult, make_empty_board


@dataclass
class GameState:
    """One player's game session.

    Field names deliberately follow the pseudocode (for example
    ``win_prompt_pending`` and ``keep_playing_after_win``) so the code is easy
    to map back to the assignment specification.
    """

    # --- Player and mode ---------------------------------------------------
    player_name: str = "Player"
    mode: str = "Classic"

    # --- Board and score (Modules 3 and 6) ---------------------------------
    board: list[list[int]] = field(default_factory=make_empty_board)
    score: int = 0
    best_score: int = 0
    move_count: int = 0
    game_over: bool = False
    game_over_reason: str = ""
    won: bool = False
    keep_playing_after_win: bool = False
    win_prompt_pending: bool = False

    # --- Milestones (Module 11) --------------------------------------------
    milestones: list[int] = field(default_factory=list)
    largest_tile: int = 0

    # --- Bookkeeping --------------------------------------------------------
    score_saved: bool = False              # guards save_score() against double writes
    data_path: str = ""                    # optional override used by the tests
    save_timestamp: str = ""               # wall-clock date supplied by the UI

    # The UI uses these two snapshots to build slide/pop/spawn animations.
    # They are plain data and harmless for non-graphical front-ends.
    last_move: Optional[MoveResult] = None
    last_spawn: Optional[SpawnResult] = None

    # ------------------------------------------------------------------
    # Small helpers used by the UI and the game flow.
    # ------------------------------------------------------------------
    def refresh_largest_tile(self):
        """Recompute the largest tile after a move or a new game."""
        largest = 0
        for row in self.board:
            for value in row:
                if value > largest:
                    largest = value
        self.largest_tile = largest
        return largest

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-friendly summary of the round (used by the tests)."""
        return {
            "player_name": self.player_name,
            "mode": self.mode,
            "board": [row[:] for row in self.board],
            "score": self.score,
            "best_score": self.best_score,
            "move_count": self.move_count,
            "game_over": self.game_over,
            "won": self.won,
        }
