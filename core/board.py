"""
Board mechanics for 2048 Tile Adventure (Pseudocode Modules 4, 5 and 10).

Everything in this module works on plain Python lists.  It never imports a
GUI library, never reads the clock and never plays a sound.

A board is a list of ``GRID_SIZE`` rows, each containing ``GRID_SIZE`` ints.
An empty cell is stored as 0.
"""

import random
from dataclasses import dataclass, field

from core import events
from core.constants import (
    DIRECTIONS,
    GRID_SIZE,
    SPAWN_CHANCE_2,
)
from core.events import make_event


# ---------------------------------------------------------------------------
# Data containers returned by the board functions.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MergeInfo:
    """Details of one merge, used by animations and by tests."""

    cell: tuple[int, int]          # destination position of the merged tile
    old_value: int                 # value of each source tile (e.g. 2)
    value: int                     # value after merging (e.g. 4)
    sources: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class TileMove:
    """One source tile sliding to its destination (UI animation data)."""

    from_cell: tuple[int, int]
    to_cell: tuple[int, int]
    value: int
    merged: bool = False           # this tile is one of two tiles merging


@dataclass
class MoveResult:
    """The complete outcome of applying a direction to a board."""

    moved: bool
    board: list[list[int]]
    score_gained: int
    merges: list[MergeInfo] = field(default_factory=list)
    moves: list[TileMove] = field(default_factory=list)


@dataclass(frozen=True)
class RowMerge:
    """Internal helper describing a merge inside a single row."""

    dest_index: int
    value: int
    merged_value: int
    sources: tuple[int, ...]


@dataclass
class RowMergeResult:
    """Full result of merging one row."""

    row: list[int]
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
    engine below uses direction line coordinates, which is equivalent.
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
def merge_row_left_detailed(row):
    """Merge one row to the left and return every detail of what happened.

    This is the single source of truth for 2048 merging.  The algorithm is the
    pseudocode one: remove zeros, scan left to right, merge equal neighbours
    once, then pad with zeros.  The extra bookkeeping records:
      * the score gained (the caller adds it to the game score),
      * where each source tile came from (for sliding animations).
    """
    size = len(row)

    # (value, original_index) for every non-zero tile.
    tiles = [
        (row[index], index)
        for index in range(size)
        if row[index] != 0
    ]

    merged_row = []
    origins = []
    merges = []
    score_gained = 0

    index = 0
    while index < len(tiles):
        value, origin = tiles[index]

        if index + 1 < len(tiles) and tiles[index + 1][0] == value:
            # --- A merge: two equal tiles become one double-value tile. ---
            next_origin = tiles[index + 1][1]
            new_value = value * 2

            score_gained += new_value
            merges.append(
                RowMerge(
                    dest_index=len(merged_row),
                    value=value,
                    merged_value=new_value,
                    sources=(origin, next_origin),
                )
            )

            merged_row.append(new_value)
            origins.append((origin, next_origin))
            index += 2          # skip both source tiles: merge only once
        else:
            # --- A single tile simply slides (or stays) where it is. ------
            merged_row.append(value)
            origins.append((origin,))
            index += 1

    # Pad the row with empty cells on the right.
    while len(merged_row) < size:
        merged_row.append(0)
        origins.append(())

    return RowMergeResult(
        row=merged_row,
        score_gained=score_gained,
        merges=merges,
        origins=origins,
    )


def merge_row_left(row):
    """Pseudocode Module 4 - return just the merged row.

    Example: [2, 2, 2, 2] -> [4, 4, 0, 0]
             [2, 2, 4, 0] -> [4, 4, 0, 0]
             [4, 2, 2, 0] -> [4, 4, 0, 0]
    Use ``merge_row_left_detailed`` when you also need the score and the
    positions of the merged tiles.
    """
    return merge_row_left_detailed(row).row


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


def _apply_line(cells, board, new_board):
    """Merge one line of the board and write it into the new grid.

    ``cells`` are the (row, col) positions of the line, destination first.
    Returns ``(score_gained, tile_moves, merge_infos)``.
    """
    values = [board[row][col] for row, col in cells]

    result = merge_row_left_detailed(values)
    tile_moves = []
    merge_infos = []

    for dest_index, cell in enumerate(cells):
        row, col = cell
        new_board[row][col] = result.row[dest_index]

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
                    merged=is_merge,
                )
            )

    for merge in result.merges:
        merge_infos.append(
            MergeInfo(
                cell=cells[merge.dest_index],
                old_value=merge.value,
                value=merge.merged_value,
                sources=tuple(cells[index] for index in merge.sources),
            )
        )

    return result.score_gained, tile_moves, merge_infos


def apply_move_to_grid(board, direction):
    """Simulate one direction on a board *without* spawning a new tile.

    This pure function is used by the real move, by the AI solver's
    simulations and by the tests.  The input board is never modified.
    """
    direction = direction.upper()
    if direction not in DIRECTIONS:
        raise ValueError("Unknown direction: %r" % (direction,))

    new_board = copy_board(board)

    all_moves = []
    all_merges = []
    total_score = 0

    for line in _line_coordinates(direction, len(board)):
        score, moves, merges = _apply_line(line, board, new_board)
        total_score += score
        all_moves.extend(moves)
        all_merges.extend(merges)

    return MoveResult(
        moved=new_board != board,
        board=new_board,
        score_gained=total_score,
        merges=all_merges,
        moves=all_moves,
    )


# ---------------------------------------------------------------------------
# Spawning new tiles (Module 5)
# ---------------------------------------------------------------------------
def spawn_new_tile(board, rng=None):
    """Pseudocode Module 5 - place a 2 (90 %) or 4 (10 %) in an empty cell.

    The function mutates ``board`` and returns a SpawnResult, or None when
    there is no empty cell.
    """
    rng = rng or random

    empty_cells = [
        (row, col)
        for row in range(len(board))
        for col in range(len(board[row]))
        if board[row][col] == 0
    ]
    if not empty_cells:
        return None

    cell = rng.choice(empty_cells)
    roll = rng.randint(1, 100)
    value = 2 if roll <= SPAWN_CHANCE_2 else 4

    board[cell[0]][cell[1]] = value
    return SpawnResult(cell=cell, value=value)


# ---------------------------------------------------------------------------
# Valid-move checks
# ---------------------------------------------------------------------------
def can_move(board):
    """True if any empty cell or any equal adjacent pair exists.

    Used for the "no valid moves remain" game-over check.
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


def available_directions(board):
    """Return the directions that would actually change the board."""
    moves = []
    for direction in DIRECTIONS:
        if apply_move_to_grid(board, direction).moved:
            moves.append(direction)
    return moves


# ---------------------------------------------------------------------------
# The stateful move (Module 4)
# ---------------------------------------------------------------------------
def move_tiles(state, direction, rng=None):
    """Pseudocode Module 4 - perform one move and all follow-up rules.

    Only a move that changes the board counts: it increments move_count,
    spawns one tile, checks the score milestones and finally checks the game
    status.  An invalid move changes nothing at all.
    """
    # Imported inside the function to avoid a circular import at module load:
    # game_flow imports this module for start_new_game / check_game_status.
    from core.game_flow import check_game_status, check_milestones, update_score

    if state.game_over or state.win_prompt_pending:
        return []

    direction = direction.upper()
    if direction not in DIRECTIONS:
        return []

    result = apply_move_to_grid(state.board, direction)

    if not result.moved:
        # Invalid move: no spawn, no score, no milestone checks.
        state.last_move = None
        state.last_spawn = None
        return []

    # --- Commit the new board and score. ----------------------------------
    state.board = result.board
    state.last_move = result
    update_score(state, result.score_gained)
    state.move_count += 1

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
            )
        )

    # --- Spawn exactly one tile after a successful move. ------------------
    state.last_spawn = spawn_new_tile(state.board, rng=rng)
    if state.last_spawn is not None:
        result_events.append(
            make_event(
                events.SPAWNED,
                cell=state.last_spawn.cell,
                value=state.last_spawn.value,
            )
        )

    # The largest tile is refreshed after the spawn, so a spawned 4 on a board
    # of 2s is counted immediately.
    state.refresh_largest_tile()

    # --- Milestones, then the win / game-over checks. ---------------------
    result_events.extend(check_milestones(state))
    result_events.extend(check_game_status(state))
    return result_events
