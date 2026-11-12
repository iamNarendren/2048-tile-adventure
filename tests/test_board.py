"""Unit tests for the pure board engine (no pygame, no file I/O)."""

import random

import pytest

from core.board import (
    apply_move_to_grid,
    available_directions,
    can_move,
    make_empty_board,
    merge_row_left,
    merge_row_left_detailed,
    reverse_rows,
    spawn_new_tile,
    transpose,
)
from core.constants import GRID_SIZE


# ---------------------------------------------------------------------------
# merge_row_left - Module 4
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "row, expected",
    [
        ([2, 2, 2, 2], [4, 4, 0, 0]),
        ([2, 2, 4, 0], [4, 4, 0, 0]),
        ([4, 2, 2, 0], [4, 4, 0, 0]),
        ([2, 0, 2, 4], [4, 4, 0, 0]),
        ([4, 4, 8, 8], [8, 16, 0, 0]),
        ([2, 4, 8, 16], [2, 4, 8, 16]),
        ([0, 0, 0, 0], [0, 0, 0, 0]),
        ([0, 2, 0, 2], [4, 0, 0, 0]),
    ],
)
def test_merge_row_left(row, expected):
    assert merge_row_left(row) == expected


def test_merge_only_once_per_move():
    # A 4 created by merging must NOT merge again with the next 4 in the same
    # move.  [4, 4, 8, 0] -> [8, 8, 0, 0], never [16, 0, 0, 0].
    assert merge_row_left([4, 4, 8, 0]) == [8, 8, 0, 0]
    result = merge_row_left_detailed([2, 2, 2, 2])
    assert result.score_gained == 8
    assert len(result.merges) == 2


def test_merge_row_records_sources_and_score():
    result = merge_row_left_detailed([0, 2, 2, 4])
    assert result.row == [4, 4, 0, 0]
    assert result.score_gained == 4
    assert len(result.merges) == 1
    merge = result.merges[0]
    assert merge.dest_index == 0
    assert merge.sources == (1, 2)


# ---------------------------------------------------------------------------
# All four directions - Module 4
# ---------------------------------------------------------------------------
def test_moves_in_all_four_directions():
    board = [
        [2, 0, 0, 2],
        [0, 0, 0, 0],
        [4, 4, 0, 0],
        [0, 0, 0, 0],
    ]

    left = apply_move_to_grid(board, "LEFT")
    assert left.board[0] == [4, 0, 0, 0]
    assert left.board[2] == [8, 0, 0, 0]
    assert left.score_gained == 12

    right = apply_move_to_grid(board, "RIGHT")
    assert right.board[0] == [0, 0, 0, 4]
    assert right.board[2] == [0, 0, 0, 8]
    assert right.score_gained == 12

    vertical = [
        [2, 0, 0, 0],
        [2, 0, 0, 0],
        [4, 0, 0, 0],
        [4, 0, 0, 0],
    ]
    up = apply_move_to_grid(vertical, "UP")
    assert [row[0] for row in up.board] == [4, 8, 0, 0]
    assert up.score_gained == 12

    down = apply_move_to_grid(vertical, "DOWN")
    assert [row[0] for row in down.board] == [0, 0, 4, 8]
    assert down.score_gained == 12


def test_move_does_not_mutate_input_board():
    board = [[2, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    snapshot = [row[:] for row in board]
    apply_move_to_grid(board, "LEFT")
    assert board == snapshot


def test_invalid_direction_is_rejected():
    with pytest.raises(ValueError):
        apply_move_to_grid(make_empty_board(), "DIAGONAL")


# ---------------------------------------------------------------------------
# Spawning - Module 5
# ---------------------------------------------------------------------------
def test_spawn_ratio_is_roughly_90_10():
    rng = random.Random(2024)
    counts = {2: 0, 4: 0}

    for _ in range(3000):
        board = make_empty_board()
        spawn = spawn_new_tile(board, rng=rng)
        assert spawn is not None
        counts[spawn.value] += 1

    four_ratio = counts[4] / 3000
    assert 0.05 < four_ratio < 0.16, counts


def test_spawn_does_nothing_on_a_full_board():
    board = [[2] * GRID_SIZE for _ in range(GRID_SIZE)]
    assert spawn_new_tile(board) is None


def test_spawn_uses_the_only_empty_cell():
    board = [[2] * GRID_SIZE for _ in range(GRID_SIZE)]
    board[2][3] = 0
    spawn = spawn_new_tile(board, rng=random.Random(1))
    assert spawn is not None
    assert spawn.cell == (2, 3)
    assert board[2][3] in (2, 4)


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------
def test_transpose_and_reverse_rows():
    board = [
        [1, 2, 3, 4],
        [5, 6, 7, 8],
        [9, 10, 11, 12],
        [13, 14, 15, 16],
    ]
    assert transpose(board)[0] == [1, 5, 9, 13]
    assert transpose(transpose(board)) == board
    assert reverse_rows(board)[0] == [4, 3, 2, 1]
    assert reverse_rows(reverse_rows(board)) == board


def test_available_directions():
    single_corner_tile = [
        [2, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    assert sorted(available_directions(single_corner_tile)) == ["DOWN", "RIGHT"]

    stuck = [
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4],
        [4, 2, 4, 2],
    ]
    assert available_directions(stuck) == []


# ---------------------------------------------------------------------------
# Valid-move detection
# ---------------------------------------------------------------------------
def test_can_move():
    full_checkerboard = [
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4],
        [4, 2, 4, 2],
    ]
    assert can_move(full_checkerboard) is False
    assert can_move(make_empty_board()) is True

    full_checkerboard[3][3] = 4   # creates an equal neighbour
    assert can_move(full_checkerboard) is True
