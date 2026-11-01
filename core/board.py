"""
Board mechanics for 2048 Tile Adventure (Pseudocode Modules 4, 5 and 10).

Everything in this module works on plain Python lists and sets.  It never
imports a GUI library, never reads the clock and never plays a sound.

A board is a list of ``GRID_SIZE`` rows, each containing ``GRID_SIZE`` ints.
Infection markers are a separate set of (row, col) positions; during a move a
parallel grid of True/False flags travels with the numbers, so markers stay
attached to their tile through slides, merges and all four directions.
"""

import random
from dataclasses import dataclass, field

from core import events
from core.achievements import check_achievements, check_milestones
from core.constants import (
    BLOCK_FREEZES_TILES,
    DIRECTIONS,
    GRID_SIZE,
    SPAWN_CHANCE_2,
    TARGET_TILE,
    get_tile_color,
)
from core.events import make_event
from core.leaderboard import save_progress
from core.modes.infection import transfer_infection_on_merge, update_infection_mode
from core.modes.survival import process_survival_successful_move


# ---------------------------------------------------------------------------
# Data containers returned by the board functions.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MergeInfo:
    """Details of one merge, used by animations and by tests."""

    cell: tuple[int, int]          # destination position of the merged tile
    old_value: int                 # value of each source tile (e.g. 2)
    value: int                     # value after merging (e.g. 4)
    infected: bool                 # infection state of the merged tile
    sources: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class TileMove:
    """One source tile sliding to its destination (UI animation data)."""

    from_cell: tuple[int, int]
    to_cell: tuple[int, int]
    value: int
    infected: bool = False
    merged: bool = False           # this tile is one of two tiles merging
    frozen: bool = False           # blocked Survival cell: it does not move


@dataclass
class MoveResult:
    """The complete outcome of applying a direction to a board."""

    moved: bool
    board: list[list[int]]
    infected_tiles: set[tuple[int, int]]
    score_gained: int
    merges: list[MergeInfo] = field(default_factory=list)
    moves: list[TileMove] = field(default_factory=list)


@dataclass(frozen=True)
class RowMerge:
    """Internal helper describing a merge inside a single row."""

    dest_index: int
    value: int
    merged_value: int
    infected: bool
    sources: tuple[int, ...]


@dataclass
class RowMergeResult:
    """Full result of merging one row, including infection bookkeeping."""

    row: list[int]
    infected_row: list[bool]
    score_gained: int
    merges: list[RowMerge]
    origins: list[tuple[int, ...]]


@dataclass(frozen=True)
class SpawnResult:
    """Where a new tile appeared and which value it received."""

    cell: tuple[int, int]
    value: int


# ---------------------------------------------------------------------------
# Basic board helpers
# ---------------------------------------------------------------------------
def make_empty_board(size=GRID_SIZE):
    """Create a size x size grid filled with zeros."""
    return [[0 for _ in range(size)] for _ in range(size)]


def copy_board(board):
    """Return a deep-enough copy of a numeric grid."""
    return [row[:] for row in board]


def transpose(board):
    """Return the transposed grid (rows become columns).

    Kept as an explicit helper because the pseudocode mentions it; the move
    engine below uses direction line coordinates, which is equivalent but also
    supports blocked cells in the middle of a line.
    """
    size = len(board)
    return [[board[row][col] for row in range(size)] for col in range(size)]


def reverse_rows(board):
    """Return a grid with every row reversed (left <-> right)."""
    return [list(reversed(row)) for row in board]


def largest_tile(board):
    """Return the biggest number on the board (0 for an empty board)."""
    largest = 0
    for row in board:
        for value in row:
            if value > largest:
                largest = value
    return largest


def has_tile(board, value):
    """True when at least one cell equals ``value``."""
    return any(value in row for row in board)


# ---------------------------------------------------------------------------
# Merging one row (Module 4)
# ---------------------------------------------------------------------------
def handle_tile_merge(old_value, merged_value, left_infected=False, right_infected=False):
    """Pseudocode Module 4 - decide the infection state of a merged tile.

    The pseudocode's two-argument version delegates to the Infection module.
    We pass the infection flags of both source tiles as extra arguments so the
    pure board code can apply the rule without knowing the game mode.  In
    Classic and Survival there are never any infected tiles, so the result is
    always False and the rule is a harmless no-op.
    """
    # ``old_value`` and ``merged_value`` document which tiles merged; the
    # actual state change is the exclusive-OR rule from the Infection module.
    return transfer_infection_on_merge(left_infected, right_infected)


def merge_row_left_detailed(row, infected_row=None):
    """Merge one row to the left and return every detail of what happened.

    This is the single source of truth for 2048 merging.  The algorithm is the
    pseudocode one: remove zeros, scan left to right, merge equal neighbours
    once, then pad with zeros.  The extra bookkeeping records:
      * the score gained (the caller adds it to the game score),
      * where each source tile came from (for sliding animations),
      * the infection flag of the merged tile (both infected = cured).
    """
    size = len(row)
    flags = list(infected_row) if infected_row is not None else [False] * size
    if len(flags) < size:
        flags += [False] * (size - len(flags))

    # (value, infected, original_index) for every non-zero tile.
    tiles = [
        (row[index], bool(flags[index]), index)
        for index in range(size)
        if row[index] != 0
    ]

    merged_row = []
    merged_flags = []
    origins = []
    merges = []
    score_gained = 0

    index = 0
    while index < len(tiles):
        value, infected, origin = tiles[index]

        if index + 1 < len(tiles) and tiles[index + 1][0] == value:
            # --- A merge: two equal tiles become one double-value tile. ---
            next_value, next_infected, next_origin = tiles[index + 1]
            new_value = value * 2
            new_infected = handle_tile_merge(
                value, new_value, infected, next_infected
            )

            score_gained += new_value
            dest_index = len(merged_row)
            merges.append(
                RowMerge(
                    dest_index=dest_index,
                    value=value,
                    merged_value=new_value,
                    infected=new_infected,
                    sources=(origin, next_origin),
                )
            )

            merged_row.append(new_value)
            merged_flags.append(new_infected)
            origins.append((origin, next_origin))
            index += 2          # skip both source tiles: merge only once
        else:
            # --- A single tile simply slides (or stays) where it is. ------
            merged_row.append(value)
            merged_flags.append(infected)
            origins.append((origin,))
            index += 1

    # Pad the row with empty cells on the right.
    while len(merged_row) < size:
        merged_row.append(0)
        merged_flags.append(False)
        origins.append(())

    return RowMergeResult(
        row=merged_row,
        infected_row=merged_flags,
        score_gained=score_gained,
        merges=merges,
        origins=origins,
    )


def merge_row_left(row, infected_row=None):
    """Pseudocode Module 4 - return just the merged row.

    Example: [2, 2, 2, 2] -> [4, 4, 0, 0]
             [2, 2, 4, 0] -> [4, 4, 0, 0]
             [4, 2, 2, 0] -> [4, 4, 0, 0]
    Use ``merge_row_left_detailed`` when you also need the score and the
    positions of the merged tiles.
    """
    return merge_row_left_detailed(row, infected_row).row


# ---------------------------------------------------------------------------
# Applying a direction to the whole board (Module 4)
# ---------------------------------------------------------------------------
def _line_coordinates(direction, size):
    """Return the four lines of the board in *destination-first* order.

    For LEFT the destination is column 0, for RIGHT it is column 3, and so
    on.  Reading every line in this order lets one merge routine handle all
    four directions without duplicating logic.
    """
    lines = []
    for index in range(size):
        if direction == "LEFT":
            line = [(index, col) for col in range(size)]
        elif direction == "RIGHT":
            line = [(index, size - 1 - col) for col in range(size)]
        elif direction == "UP":
            line = [(row, index) for row in range(size)]
        elif direction == "DOWN":
            line = [(size - 1 - row, index) for row in range(size)]
        else:
            raise ValueError("Unknown direction: %r" % (direction,))
        lines.append(line)
    return lines


def _apply_segment(cells, board, infected_cells, new_board, new_infected_grid):
    """Merge one unblocked segment of a line and write it into the new grid.

    Returns ``(score_gained, tile_moves, merge_infos)``.
    """
    values = [board[row][col] for row, col in cells]
    flags = [(row, col) in infected_cells for row, col in cells]

    result = merge_row_left_detailed(values, flags)
    tile_moves = []
    merge_infos = []

    for dest_index, cell in enumerate(cells):
        row, col = cell
        new_board[row][col] = result.row[dest_index]
        new_infected_grid[row][col] = result.infected_row[dest_index]

        origins = result.origins[dest_index]
        if result.row[dest_index] == 0 or not origins:
            continue

        is_merge = len(origins) > 1
        for origin_index in origins:
            tile_moves.append(
                TileMove(
                    from_cell=cells[origin_index],
                    to_cell=cell,
                    value=values[origin_index],
                    infected=flags[origin_index],
                    merged=is_merge,
                )
            )

    for merge in result.merges:
        merge_infos.append(
            MergeInfo(
                cell=cells[merge.dest_index],
                old_value=merge.value,
                value=merge.merged_value,
                infected=merge.infected,
                sources=tuple(cells[index] for index in merge.sources),
            )
        )

    return result.score_gained, tile_moves, merge_infos


def apply_move_to_grid(board, direction, infected_tiles=None, blocked_cells=None):
    """Simulate one direction on a board *without* spawning a new tile.

    This pure function is used by the real move, by the AI solver's
    simulations and by the tests.  ``blocked_cells`` are Survival cells that
    act as walls when BLOCK_FREEZES_TILES is enabled; they keep their tiles and
    split a row/column into independent segments.
    """
    direction = direction.upper()
    if direction not in DIRECTIONS:
        raise ValueError("Unknown direction: %r" % (direction,))

    size = len(board)
    infected_cells = set(infected_tiles or ())
    blocked = set(blocked_cells or ())

    new_board = copy_board(board)
    new_infected_grid = [
        [(row, col) in infected_cells for col in range(size)]
        for row in range(size)
    ]

    all_moves = []
    all_merges = []
    total_score = 0

    for line in _line_coordinates(direction, size):
        segment = []
        for cell in line:
            if cell in blocked:
                # Flush the tiles before the wall, then keep the wall cell
                # exactly where it is (existing tiles are never erased).
                if segment:
                    score, moves, merges = _apply_segment(
                        segment, board, infected_cells, new_board, new_infected_grid
                    )
                    total_score += score
                    all_moves.extend(moves)
                    all_merges.extend(merges)
                    segment = []

                row, col = cell
                value = board[row][col]
                is_infected = cell in infected_cells
                new_board[row][col] = value
                new_infected_grid[row][col] = is_infected
                if value != 0:
                    all_moves.append(
                        TileMove(
                            from_cell=cell,
                            to_cell=cell,
                            value=value,
                            infected=is_infected,
                            frozen=True,
                        )
                    )
            else:
                segment.append(cell)

        if segment:
            score, moves, merges = _apply_segment(
                segment, board, infected_cells, new_board, new_infected_grid
            )
            total_score += score
            all_moves.extend(moves)
            all_merges.extend(merges)

    # Rebuild the infection set from the moved parallel grid.  Markers on
    # empty cells are dropped, and merged tiles follow the merge rule.
    new_infected_tiles = set()
    for row in range(size):
        for col in range(size):
            if new_board[row][col] != 0 and new_infected_grid[row][col]:
                new_infected_tiles.add((row, col))

    return MoveResult(
        moved=new_board != board,
        board=new_board,
        infected_tiles=new_infected_tiles,
        score_gained=total_score,
        merges=all_merges,
        moves=all_moves,
    )


# ---------------------------------------------------------------------------
# Spawning new tiles (Module 5)
# ---------------------------------------------------------------------------
def spawn_new_tile(board, rng=None, blocked_cells=None):
    """Pseudocode Module 5 - place a 2 (90 %) or 4 (10 %) in an empty cell.

    Blocked cells are excluded, so a Survival block is never filled.  The
    function mutates ``board`` and returns a SpawnResult, or None when there is
    no legal empty cell.  New tiles are never infected.
    """
    rng = rng or random
    blocked = set(blocked_cells or ())

    empty_cells = [
        (row, col)
        for row in range(len(board))
        for col in range(len(board[row]))
        if board[row][col] == 0 and (row, col) not in blocked
    ]
    if not empty_cells:
        return None

    cell = rng.choice(empty_cells)
    roll = rng.randint(1, 100)
    value = 2 if roll <= SPAWN_CHANCE_2 else 4

    board[cell[0]][cell[1]] = value
    return SpawnResult(cell=cell, value=value)


def spawn_tile_in_state(state, rng=None):
    """Spawn a tile for a GameState, respecting an active Survival block."""
    blocked = set()
    if state.mode == "Survival" and state.survival_block_active:
        blocked = state.survival_blocked_cells

    spawn = spawn_new_tile(state.board, rng=rng, blocked_cells=blocked)
    if spawn is not None:
        # Defensive: a freshly spawned tile must never inherit an old marker.
        state.infected_tiles.discard(spawn.cell)
    return spawn


# ---------------------------------------------------------------------------
# Valid-move checks
# ---------------------------------------------------------------------------
def can_move(board):
    """True if any empty cell or any equal adjacent pair exists.

    Used for the "no valid moves remain" game-over check.  Temporary Survival
    blocks are intentionally ignored here: they expire after 3 seconds, so
    they must not end the round.
    """
    size = len(board)

    for row in range(size):
        for col in range(size):
            if board[row][col] == 0:
                return True

    for row in range(size):
        for col in range(size):
            value = board[row][col]
            if col + 1 < size and board[row][col + 1] == value:
                return True
            if row + 1 < size and board[row + 1][col] == value:
                return True

    return False


def available_directions(board, infected_tiles=None, blocked_cells=None):
    """Return the directions that would actually change the board."""
    moves = []
    for direction in DIRECTIONS:
        result = apply_move_to_grid(
            board, direction, infected_tiles, blocked_cells
        )
        if result.moved:
            moves.append(direction)
    return moves


# ---------------------------------------------------------------------------
# The stateful move (Module 4)
# ---------------------------------------------------------------------------
def move_tiles(state, direction, rng=None, now=0.0):
    """Pseudocode Module 4 - perform one move and all follow-up rules.

    Only a move that changes the board counts: it increments move_count,
    spawns one tile, advances the mode, checks achievements/milestones and
    finally checks the game status.  An invalid move changes nothing at all.

    The core receives ``now`` (game seconds) from the UI; it never reads a
    clock itself.  ``now`` is used when a mode needs to save a timestamped
    score or when the AI solver asks for a move.
    """
    # Imported inside the function to avoid a circular import at module load:
    # game_flow imports this module for start_new_game / check_game_status.
    from core.game_flow import check_game_status, update_score
    from core.robot import update_robot_color

    if state.game_over or state.win_prompt_pending:
        return []

    direction = direction.upper()
    if direction not in DIRECTIONS:
        return []

    # --- Decide which cells are frozen by a Survival block. ---------------
    blocked = set()
    if (
        state.mode == "Survival"
        and BLOCK_FREEZES_TILES
        and state.survival_block_active
    ):
        blocked = state.survival_blocked_cells

    result = apply_move_to_grid(
        state.board,
        direction,
        infected_tiles=state.infected_tiles,
        blocked_cells=blocked,
    )

    if not result.moved:
        # Invalid move: no spawn, no mode progress, no achievement checks.
        state.last_move = None
        state.last_spawn = None
        return []

    # --- Commit the new board and score. ----------------------------------
    state.board = result.board
    state.infected_tiles = result.infected_tiles
    state.last_move = result
    update_score(state, result.score_gained)
    state.move_count += 1
    state.merge_count += len(result.merges)
    state.refresh_largest_tile()

    result_events = [
        make_event(
            events.MOVED,
            direction=direction,
            score_gained=result.score_gained,
            merge_count=len(result.merges),
        )
    ]
    for merge in result.merges:
        result_events.append(
            make_event(
                events.MERGED,
                cell=merge.cell,
                value=merge.value,
                old_value=merge.old_value,
                infected=merge.infected,
            )
        )

    # --- Spawn exactly one tile after a successful move. ------------------
    state.last_spawn = spawn_tile_in_state(state, rng=rng)
    if state.last_spawn is not None:
        result_events.append(
            make_event(
                events.SPAWNED,
                cell=state.last_spawn.cell,
                value=state.last_spawn.value,
            )
        )

    # --- Mode logic runs once per successful move. ------------------------
    if state.mode == "Survival":
        result_events.extend(process_survival_successful_move(state))
    elif state.mode == "Infection":
        result_events.extend(update_infection_mode(state, rng=rng))

    # --- Achievements and milestones. -------------------------------------
    achievement_events = check_achievements(state)
    if achievement_events:
        # Persist immediately so a quit cannot lose a lifetime unlock.
        save_progress(state)
    result_events.extend(achievement_events)
    result_events.extend(check_milestones(state))

    # --- Robot colour tier and best score. --------------------------------
    update_robot_color(state)
    if state.score > state.best_score:
        state.best_score = state.score

    # --- Win / game-over safety checks. -----------------------------------
    result_events.extend(check_game_status(state))
    return result_events
