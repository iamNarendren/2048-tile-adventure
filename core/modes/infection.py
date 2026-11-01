"""
Infection mode rules (Pseudocode Module 9).

Infection is stored as a set of (row, col) positions in ``state.infected_tiles``.
The board code moves a parallel grid of infection flags together with the
numbers, so markers always travel with their tile when it slides or merges.
"""

import random

from core import events
from core.constants import GRID_SIZE, INFECTION_SPREAD_EVERY
from core.events import make_event
from core.leaderboard import save_score


# The four direct neighbours of a cell (up, down, left, right).
NEIGHBOUR_OFFSETS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def transfer_infection_on_merge(left_infected, right_infected):
    """Pseudocode Module 9 - decide the infection state of a merged tile.

    * both source tiles infected -> cured (False)
    * exactly one infected      -> infected (True)
    * neither infected          -> normal (False)

    This is an exclusive-OR, which keeps the rule short and easy to test.
    ``board.merge_row_left`` calls this for every merge so markers are handled
    in exactly one place.
    """
    return bool(left_infected) != bool(right_infected)


def infect_one_random_occupied_tile(state, rng=None):
    """Pseudocode Module 9 - infect one random occupied cell.

    Returns the chosen (row, col), or None when the board is empty.
    """
    rng = rng or random
    occupied = state.occupied_cells()
    if not occupied:
        return None
    cell = rng.choice(occupied)
    state.infected_tiles.add(cell)
    return cell


def spread_infection(state):
    """Pseudocode Module 9 - infect uninfected neighbours of infected tiles.

    Only cells that already contain a tile can be infected.  We iterate over a
    snapshot (``list``) so cells infected during this spread cannot spread
    again in the same step.
    """
    newly_infected = set()

    for row, col in list(state.infected_tiles):
        for d_row, d_col in NEIGHBOUR_OFFSETS:
            n_row = row + d_row
            n_col = col + d_col

            if not (0 <= n_row < GRID_SIZE and 0 <= n_col < GRID_SIZE):
                continue
            if state.board[n_row][n_col] == 0:
                continue
            if (n_row, n_col) in state.infected_tiles:
                continue

            newly_infected.add((n_row, n_col))

    state.infected_tiles.update(newly_infected)
    return newly_infected


def check_all_tiles_infected(state):
    """Pseudocode Module 9 - True when every occupied tile is infected."""
    occupied = state.occupied_cells()
    if not occupied:
        return False
    for cell in occupied:
        if cell not in state.infected_tiles:
            return False
    return True


def update_infection_mode(state, rng=None):
    """Pseudocode Module 9 - called exactly once after a successful move.

    The counter counts *moves*, never frames.  Every third move infection
    spreads to direct neighbours.  If every occupied tile is infected the
    round ends; ``save_score`` is safe to call again because the state keeps a
    ``score_saved`` flag.
    """
    if state.game_over:
        return []

    result_events = []
    state.infection_move_counter += 1

    if state.infection_move_counter >= INFECTION_SPREAD_EVERY:
        newly_infected = spread_infection(state)
        state.infection_move_counter = 0
        result_events.append(
            make_event(events.INFECTION_SPREAD, cells=sorted(newly_infected))
        )

    # Game over is detected here at the end of the move, and again by
    # check_game_status() as a safety net.  score_saved prevents double saves.
    if check_all_tiles_infected(state):
        state.game_over = True
        state.game_over_reason = "All tiles infected - Game Over"
        save_score(state)
        result_events.append(
            make_event(events.GAME_OVER, reason=state.game_over_reason)
        )

    return result_events
