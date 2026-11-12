"""
Heuristic AI solver behind the HINT button (Pseudocode Module 7).

The solver is pure Python.  For each direction it:
  1. copies the board and simulates the move with the same board engine,
  2. skips the direction if nothing would change,
  3. scores the resulting board with a weighted heuristic,
then returns the best direction.  It never touches the real game state: the
HINT button only *shows* the suggested direction, the player still makes the
move.

Heuristic weights (each one is a named constant below):
  * empty cells       - free space is the most important survival factor
  * merge potential   - adjacent equal tiles create future merges
  * corner bonus      - a large tile parked in a corner is safe
  * monotonicity      - rows/columns sorted in one direction are easier to merge
  * smoothness        - neighbouring values should be close, not wildly different
  * largest tile      - gently rewards growing the biggest tile
"""

from core.board import apply_move_to_grid, largest_tile
from core.constants import DIRECTIONS

# --- Named heuristic weights ------------------------------------------------
W_EMPTY = 270.0        # each empty cell is very valuable
W_MERGE = 70.0         # each adjacent equal pair (a useful future merge)
W_CORNER = 120.0       # keep the largest tile in a corner
W_MONOTONIC = 45.0     # reward rows/columns that decrease/increase smoothly
W_SMOOTHNESS = 12.0    # penalise large jumps between neighbouring tiles
W_MAX_TILE = 1.5       # slight preference for a bigger largest tile

# Penalty for dragging the largest tile out of its corner.
W_CORNER_LOSS = 0.5


def count_empty_cells(board):
    """Number of zero cells on the board."""
    return sum(1 for row in board for value in row if value == 0)


def count_merge_pairs(board):
    """Number of horizontally/vertically adjacent equal pairs."""
    size = len(board)
    pairs = 0
    for row in range(size):
        for col in range(size):
            value = board[row][col]
            if value == 0:
                continue
            if col + 1 < size and board[row][col + 1] == value:
                pairs += 1
            if row + 1 < size and board[row + 1][col] == value:
                pairs += 1
    return pairs


def largest_tile_in_corner(board):
    """True when the biggest tile sits in one of the four corners."""
    size = len(board)
    biggest = largest_tile(board)
    if biggest == 0:
        return False
    corners = (
        board[0][0],
        board[0][size - 1],
        board[size - 1][0],
        board[size - 1][size - 1],
    )
    return biggest in corners


def monotonicity(board):
    """Measure how consistently rows and columns are ordered.

    For every line we sum the increases and the decreases separately and keep
    the better (less negative) direction.  A board that is sorted along rows
    and columns scores close to zero; a jagged board scores very negative.
    """
    size = len(board)
    lines = []

    for row in range(size):
        lines.append(board[row])
    for col in range(size):
        lines.append([board[row][col] for row in range(size)])

    total = 0.0
    for line in lines:
        increasing = 0.0
        decreasing = 0.0
        for index in range(size - 1):
            difference = line[index] - line[index + 1]
            if difference > 0:
                decreasing += difference      # the line goes down
            else:
                increasing += difference      # the line goes up
        # Keep whichever direction the line is more consistent in.
        total += max(increasing, decreasing)

    return total


def smoothness(board):
    """Return a negative penalty for large jumps between neighbouring tiles."""
    size = len(board)
    total = 0.0
    for row in range(size):
        for col in range(size):
            value = board[row][col]
            if value == 0:
                continue
            if col + 1 < size and board[row][col + 1] != 0:
                total -= abs(value - board[row][col + 1])
            if row + 1 < size and board[row + 1][col] != 0:
                total -= abs(value - board[row + 1][col])
    return total


def evaluate_board(board, merges=0):
    """Score one simulated board; higher is better.

    ``merges`` is the number of merges the simulated move created.
    """
    score = 0.0
    score += count_empty_cells(board) * W_EMPTY
    score += merges * W_MERGE
    score += count_merge_pairs(board) * W_MERGE
    score += largest_tile(board) * W_MAX_TILE
    score += monotonicity(board) * W_MONOTONIC
    score += smoothness(board) * W_SMOOTHNESS
    if largest_tile_in_corner(board):
        score += W_CORNER
    return score


def score_moves(board):
    """Return {direction: heuristic value} for every direction that changes.

    This helper is also useful for tests, because it shows every score.
    """
    values = {}
    was_cornered = largest_tile_in_corner(board)

    for direction in DIRECTIONS:
        result = apply_move_to_grid(board, direction)
        if not result.moved:
            continue

        value = evaluate_board(result.board, merges=len(result.merges))

        # Extra penalty when the move pulls the biggest tile out of a corner.
        if was_cornered and not largest_tile_in_corner(result.board):
            value -= W_CORNER * W_CORNER_LOSS

        values[direction] = value

    return values


def choose_best_move(board):
    """Pseudocode Module 7 - return the best direction, or None.

    The board is never modified: every simulation works on a copy made by
    ``apply_move_to_grid``.
    """
    values = score_moves(board)
    if not values:
        return None

    best_direction = None
    best_value = float("-inf")
    for direction, value in values.items():
        if value > best_value:
            best_value = value
            best_direction = direction
    return best_direction


def get_hint(state):
    """Return the direction the HINT button should show, or None.

    The state is only read, never changed.  No hint is given once the round is
    over or while the win prompt is waiting for an answer.
    """
    if state.game_over or state.win_prompt_pending:
        return None
    return choose_best_move(state.board)
