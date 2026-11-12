"""
Game setup, restart and status checks (Pseudocode Modules 1, 3, 6, 11 and 12).

The desktop UI calls these functions; any other front end could call exactly
the same functions.  No GUI code, no clock reads and no drawing happens here.
"""

import random

from core import events
from core.board import (
    can_move,
    has_tile,
    make_empty_board,
    spawn_new_tile,
)
from core.constants import (
    DEFAULT_PLAYER_NAME,
    MILESTONES,
    MODES,
    PLAYER_NAME_MAX_LENGTH,
    TARGET_TILE,
)
from core.events import make_event
from core.game_state import GameState
from core.leaderboard import (
    best_score_for_mode,
    load_local_leaderboards,
    save_score,
)


# ---------------------------------------------------------------------------
# Player name (Module 1)
# ---------------------------------------------------------------------------
def clean_player_name(text):
    """Pseudocode Module 1 - apply the empty/whitespace name rule.

    The desktop screen calls this when the player presses Enter; the rule lives
    here, not in the UI, so it is testable.  Names are also capped at the
    documented 12 characters.
    """
    name = (text or "").strip()
    if not name:
        return DEFAULT_PLAYER_NAME
    return name[:PLAYER_NAME_MAX_LENGTH]


# ---------------------------------------------------------------------------
# Initialisation and restart (Modules 1 and 3)
# ---------------------------------------------------------------------------
def initialize_game(player_name, mode="Classic", rng=None, data_path=None):
    """Pseudocode Module 1 - build a complete, ready-to-play GameState.

    The UI is responsible for asking the player's name (``enter_player_name``
    is a desktop screen) and for running the game loop; this function performs
    the data part of initialisation and loads the saved best score.
    """
    if mode not in MODES:
        mode = "Classic"

    state = GameState(
        player_name=clean_player_name(player_name),
        mode=mode,
        data_path=data_path or "",
    )

    data = load_local_leaderboards(data_path)
    state.best_score = best_score_for_mode(data, mode)

    start_new_game(state, rng=rng)
    return state


def start_new_game(state, rng=None):
    """Pseudocode Module 3 - reset a round and spawn the first two tiles.

    Milestones are a per-game list and are reset here, while ``best_score``
    survives a restart.
    """
    state.score = 0
    state.move_count = 0
    state.game_over = False
    state.game_over_reason = ""
    state.won = False
    state.keep_playing_after_win = False
    state.win_prompt_pending = False

    state.board = make_empty_board()

    state.score_saved = False
    state.milestones = []
    state.last_move = None
    state.last_spawn = None

    result_events = []

    # The pseudocode spawns two tiles at the start of every round.
    for _ in range(2):
        spawn = spawn_new_tile(state.board, rng=rng)
        if spawn is not None:
            result_events.append(
                make_event(events.SPAWNED, cell=spawn.cell, value=spawn.value)
            )

    state.refresh_largest_tile()
    return result_events


# ---------------------------------------------------------------------------
# Score (Module 6) and milestones (Module 11)
# ---------------------------------------------------------------------------
def update_score(state, added_score):
    """Pseudocode Module 6 - add points and keep best_score up to date."""
    state.score += added_score
    if state.score > state.best_score:
        state.best_score = state.score
    return state.score


def check_milestones(state):
    """Pseudocode Module 11 - fire each configured milestone once per game.

    Milestones are the score thresholds in ``core.constants.MILESTONES``.
    Each one that the score has reached is recorded in ``state.milestones``
    so it can never fire twice in the same round.
    """
    milestone_events = []

    for milestone in sorted(MILESTONES):
        if state.score >= milestone and milestone not in state.milestones:
            state.milestones.append(milestone)
            milestone_events.append(
                make_event(events.MILESTONE_REACHED, score=milestone)
            )

    return milestone_events


# ---------------------------------------------------------------------------
# Game status (Module 12)
# ---------------------------------------------------------------------------
def _end_game(state, reason):
    """End the round once and save the score at most once."""
    state.game_over = True
    state.game_over_reason = reason
    save_score(state)
    return [make_event(events.GAME_OVER, reason=reason)]


def check_game_status(state):
    """Pseudocode Module 12 - win and no-move checks.

    The win prompt is *returned* as an event instead of asking a question
    inside the core: the UI shows the "Keep Playing / End Game" overlay and
    then calls ``resolve_win_choice``.  ``won`` stays True afterwards, so the
    prompt can only appear once per game.
    """
    if state.game_over or state.win_prompt_pending:
        return []

    # First time the target tile appears: pause for the player's decision.
    if has_tile(state.board, TARGET_TILE) and not state.won:
        state.won = True
        state.win_prompt_pending = True
        return [make_event(events.WON, tile=TARGET_TILE)]

    # No empty cells and no equal neighbours.
    if not can_move(state.board):
        return _end_game(state, "No more moves - Game Over")

    return []


def resolve_win_choice(state, keep_playing):
    """Handle the win overlay's two buttons.

    "Keep Playing" clears the prompt and lets the round continue; "End Game"
    ends and saves immediately.  Returns the resulting events for the UI.
    """
    if not state.win_prompt_pending:
        return []

    state.win_prompt_pending = False

    if keep_playing:
        state.keep_playing_after_win = True
        # The board may already be full after the winning merge.
        return check_game_status(state)

    return _end_game(state, "You ended the game after reaching 2048")


# Small helper used by the UI when it wants a fresh random generator.
def make_rng(seed=None):
    """Create the optional seeded random generator used by all core code."""
    return random.Random(seed)
