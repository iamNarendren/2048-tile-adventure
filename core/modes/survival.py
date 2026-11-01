"""
Survival mode rules (Pseudocode Module 8).

Survival is a 60-second round.  Every 10 seconds a random row or column is
blocked for 3 seconds.  The core never reads the clock: the UI passes
``now`` (seconds since the round started) into every function, which makes the
mode fully testable.
"""

import random

from core import events
from core.constants import (
    BLOCK_FREEZES_TILES,
    GRID_SIZE,
    SURVIVAL_BLOCK_DURATION,
    SURVIVAL_BLOCK_INTERVAL,
    SURVIVAL_FIRST_BLOCK,
    SURVIVAL_TOTAL_TIME,
)
from core.events import make_event
from core.leaderboard import save_score


def reset_survival_clock(state, now=0.0):
    """Pseudocode Module 8 - restart the Survival clock and clear blocks."""
    state.survival_start_time = now
    state.survival_remaining_time = SURVIVAL_TOTAL_TIME
    state.survival_next_block_time = SURVIVAL_FIRST_BLOCK
    state.survival_block_end_time = 0.0
    state.survival_block_active = False
    state.survival_blocked_cells = set()


def process_survival_successful_move(state):
    """Pseudocode Module 8 - intentionally does nothing.

    The pseudocode says this hook exists but the continuous clock and the
    temporary blocks are handled by ``update_survival_clock`` every frame.
    Keeping the function documents that design decision.
    """
    return []


def activate_temporary_block(state, now, rng=None):
    """Pseudocode Module 8 - freeze one random row or column for 3 seconds.

    Existing tiles are *not* erased.  If BLOCK_FREEZES_TILES is True the board
    code treats these cells as walls, so tiles in the line cannot move or
    merge until the block expires.  Either way, spawn_new_tile never places a
    new tile in a blocked cell.
    """
    rng = rng or random

    index = rng.randrange(GRID_SIZE)
    if rng.randint(0, 1) == 0:
        line_kind = "row"
        cells = {(index, col) for col in range(GRID_SIZE)}
    else:
        line_kind = "column"
        cells = {(row, index) for row in range(GRID_SIZE)}

    state.survival_block_active = True
    state.survival_blocked_cells = cells
    state.survival_block_end_time = now + SURVIVAL_BLOCK_DURATION

    return [
        make_event(
            events.BLOCK_STARTED,
            line=line_kind,
            index=index,
            cells=sorted(cells),
            freezes_tiles=BLOCK_FREEZES_TILES,
        )
    ]


def update_survival_clock(state, now, rng=None):
    """Pseudocode Module 8 - update the countdown and temporary blocks.

    Called once per frame by the UI while Survival is active.  ``now`` is in
    game seconds, so pausing the game (menu, win prompt) simply pauses this
    value in the UI.
    """
    if state.game_over:
        return []
    if state.mode != "Survival":
        return []

    result_events = []
    elapsed_time = now - state.survival_start_time
    state.survival_remaining_time = SURVIVAL_TOTAL_TIME - elapsed_time

    # --- Time is up: end the round, save once, stop the clock. -----------
    if state.survival_remaining_time <= 0:
        state.survival_remaining_time = 0.0
        state.game_over = True
        state.game_over_reason = "Time is up - Game Over"
        save_score(state)
        result_events.append(
            make_event(events.GAME_OVER, reason=state.game_over_reason)
        )
        return result_events

    # --- Expire an old block before deciding whether to start a new one. --
    if state.survival_block_active and now >= state.survival_block_end_time:
        state.survival_block_active = False
        state.survival_blocked_cells = set()
        state.survival_block_end_time = 0.0
        result_events.append(make_event(events.BLOCK_ENDED))

    # --- Start the next block when its scheduled time arrives. ------------
    if not state.survival_block_active and elapsed_time >= state.survival_next_block_time:
        result_events.extend(activate_temporary_block(state, now, rng))
        state.survival_next_block_time += SURVIVAL_BLOCK_INTERVAL

    return result_events


# ---------------------------------------------------------------------------
# Read-only helpers used by the HUD (no state changes, easy to unit test).
# ---------------------------------------------------------------------------
def survival_seconds_left(state):
    """Seconds left in the round, clamped to zero."""
    return max(0.0, state.survival_remaining_time)


def seconds_until_next_block(state, now):
    """Seconds until the next block, or None while a block is active."""
    if state.survival_block_active:
        return None
    elapsed_time = now - state.survival_start_time
    return max(0.0, state.survival_next_block_time - elapsed_time)


def block_seconds_left(state, now):
    """Seconds left in the current block (0 when no block is active)."""
    if not state.survival_block_active:
        return 0.0
    return max(0.0, state.survival_block_end_time - now)
