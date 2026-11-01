"""
The complete, front-end independent game state (Pseudocode Modules 1-9).

Everything the game needs to know lives in this dataclass: the board, score,
mode-specific clocks, infection markers and so on.  The desktop UI only reads
and draws these values; it never stores game rules of its own.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from core.board import MoveResult, SpawnResult, make_empty_board
from core.constants import (
    SURVIVAL_FIRST_BLOCK,
    SURVIVAL_TOTAL_TIME,
)


@dataclass
class GameState:
    """One player's game session.

    Field names deliberately follow the pseudocode (for example
    ``survival_remaining_time`` and ``infection_move_counter``) so the code is
    easy to map back to the assignment specification.
    """

    # --- Player and mode ---------------------------------------------------
    player_name: str = "Player"
    mode: str = "Classic"                  # "Classic" | "Survival" | "Infection"

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

    # --- Robot companion and AI solver (Module 7) --------------------------
    robot_click_count: int = 0
    robot_color: str = "Blue"
    ai_solver_active: bool = False

    # --- Achievements and milestones (Module 11) ---------------------------
    achievements: list[str] = field(default_factory=list)
    milestones: list[int] = field(default_factory=list)
    merge_count: int = 0                   # used by the "First Merge" achievement
    largest_tile: int = 0

    # --- Survival mode (Module 8) ------------------------------------------
    survival_start_time: float = 0.0       # in "game seconds", supplied by the UI
    survival_remaining_time: float = SURVIVAL_TOTAL_TIME
    survival_block_active: bool = False
    survival_blocked_cells: set[tuple[int, int]] = field(default_factory=set)
    survival_next_block_time: float = SURVIVAL_FIRST_BLOCK
    survival_block_end_time: float = 0.0

    # --- Infection mode (Module 9) -----------------------------------------
    infection_move_counter: int = 0
    infected_tiles: set[tuple[int, int]] = field(default_factory=set)

    # --- Bookkeeping --------------------------------------------------------
    score_saved: bool = False              # guards save_score() against double writes
    data_path: str = ""                    # optional override for tests / web app
    save_timestamp: str = ""               # wall-clock date supplied by the UI

    # The UI uses these two snapshots to build slide/pop/spawn animations.
    # They are plain data and harmless for non-graphical front-ends.
    last_move: Optional[MoveResult] = None
    last_spawn: Optional[SpawnResult] = None

    # ------------------------------------------------------------------
    # Small helpers used by both the UI and the mode modules.
    # ------------------------------------------------------------------
    def occupied_cells(self):
        """Return every (row, col) that currently contains a tile."""
        cells = []
        for row in range(len(self.board)):
            for col in range(len(self.board[row])):
                if self.board[row][col] != 0:
                    cells.append((row, col))
        return cells

    def infected_count(self):
        """How many occupied cells carry an infection marker."""
        return len([cell for cell in self.occupied_cells()
                    if cell in self.infected_tiles])

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
        """Return a JSON-friendly summary (useful for the future web UI)."""
        return {
            "player_name": self.player_name,
            "mode": self.mode,
            "board": [row[:] for row in self.board],
            "score": self.score,
            "best_score": self.best_score,
            "move_count": self.move_count,
            "game_over": self.game_over,
            "won": self.won,
            "infected_tiles": sorted(self.infected_tiles),
            "survival_remaining_time": round(self.survival_remaining_time, 2),
        }
