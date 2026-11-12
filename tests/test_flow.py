"""Tests for game setup, invalid moves, win flow and game-over detection."""

import random

import pytest

from core import events
from core.board import move_tiles
from core.constants import GRID_SIZE, TARGET_TILE
from core.game_flow import (
    check_game_status,
    clean_player_name,
    initialize_game,
    resolve_win_choice,
    start_new_game,
    update_score,
)


def new_state(tmp_path=None, seed=11):
    path = str(tmp_path / "leaderboard.json") if tmp_path is not None else None
    return initialize_game(
        "Tester", "Classic", rng=random.Random(seed), data_path=path
    )


def set_board(state, board):
    state.board = [row[:] for row in board]
    state.refresh_largest_tile()


# ---------------------------------------------------------------------------
# Player name (Module 1)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "text, expected",
    [
        ("", "Player"),
        ("   ", "Player"),
        ("Ada", "Ada"),
        ("  Ada  ", "Ada"),
        ("Grace Hopper", "Grace Hopper"),
        ("abcdefghijklmnop", "abcdefghijkl"),   # max 12 characters
        (None, "Player"),
    ],
)
def test_clean_player_name(text, expected):
    assert clean_player_name(text) == expected


# ---------------------------------------------------------------------------
# Initial state (Modules 1 and 3)
# ---------------------------------------------------------------------------
def test_start_has_exactly_two_tiles(tmp_path):
    state = new_state(tmp_path)
    assert sum(1 for row in state.board for value in row if value != 0) == 2
    assert state.score == 0
    assert state.move_count == 0
    assert state.game_over is False
    assert state.won is False
    assert state.best_score == 0
    assert state.mode == "Classic"
    assert state.largest_tile in (2, 4)


def test_unknown_mode_falls_back_to_classic(tmp_path):
    state = initialize_game(
        "Tester",
        "Survival",
        rng=random.Random(3),
        data_path=str(tmp_path / "leaderboard.json"),
    )
    assert state.mode == "Classic"


def test_start_new_game_resets_everything(tmp_path):
    state = new_state(tmp_path)
    state.score = 999
    state.best_score = 5000
    state.move_count = 42
    state.game_over = True
    state.won = True
    state.keep_playing_after_win = True
    state.win_prompt_pending = True
    state.board = [[2] * GRID_SIZE for _ in range(GRID_SIZE)]
    state.score_saved = True
    state.milestones = [250]
    state.game_over_reason = "old reason"

    start_new_game(state, rng=random.Random(5))

    assert state.score == 0
    assert state.best_score == 5000          # best score survives a restart
    assert state.move_count == 0
    assert state.game_over is False
    assert state.won is False
    assert state.keep_playing_after_win is False
    assert state.win_prompt_pending is False
    assert state.game_over_reason == ""
    assert state.score_saved is False
    assert state.milestones == []
    assert sum(1 for row in state.board for value in row if value) == 2


# ---------------------------------------------------------------------------
# Score (Module 6)
# ---------------------------------------------------------------------------
def test_update_score_and_best_score():
    state = new_state()
    state.best_score = 50
    update_score(state, 30)
    assert state.score == 30
    assert state.best_score == 50
    update_score(state, 40)
    assert state.score == 70
    assert state.best_score == 70


# ---------------------------------------------------------------------------
# Moves (Module 4)
# ---------------------------------------------------------------------------
def test_invalid_move_changes_nothing(tmp_path):
    state = new_state(tmp_path)
    set_board(
        state,
        [
            [2, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )
    before = [row[:] for row in state.board]

    result = move_tiles(state, "LEFT")

    assert result == []
    assert state.board == before
    assert state.move_count == 0
    assert state.score == 0
    assert state.last_move is None


def test_unknown_direction_is_ignored(tmp_path):
    state = new_state(tmp_path)
    before = [row[:] for row in state.board]
    assert move_tiles(state, "DIAGONAL") == []
    assert state.board == before
    assert state.move_count == 0


def test_valid_move_spawns_one_tile_and_scores(tmp_path):
    state = new_state(tmp_path)
    set_board(
        state,
        [
            [2, 2, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )

    result = move_tiles(state, "LEFT", rng=random.Random(4))
    kinds = [event.kind for event in result]

    assert state.board[0][0] == 4
    assert state.score == 4
    assert state.move_count == 1
    assert kinds.count(events.MOVED) == 1
    assert kinds.count(events.MERGED) == 1
    assert kinds.count(events.SPAWNED) == 1
    # Two tiles remain: the merged 4 and the newly spawned tile.
    assert sum(1 for row in state.board for value in row if value) == 2


def test_milestone_fires_once_during_a_move(tmp_path):
    state = new_state(tmp_path)
    state.score = 248
    set_board(
        state,
        [
            [2, 2, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )

    result = move_tiles(state, "LEFT", rng=random.Random(4))
    milestones = [
        event.data["score"]
        for event in result
        if event.kind == events.MILESTONE_REACHED
    ]

    assert milestones == [250]
    assert state.milestones == [250]

    # A later move must not fire the same milestone again.
    result = move_tiles(state, "LEFT", rng=random.Random(4))
    assert not [
        event for event in result if event.kind == events.MILESTONE_REACHED
    ]


def test_largest_tile_includes_a_freshly_spawned_tile(tmp_path):
    state = new_state(tmp_path)
    set_board(
        state,
        [
            [2, 2, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )

    move_tiles(state, "LEFT", rng=random.Random(4))
    assert state.largest_tile == max(max(row) for row in state.board)


# ---------------------------------------------------------------------------
# Win flow (Module 12)
# ---------------------------------------------------------------------------
def _prepare_winning_board(state):
    set_board(
        state,
        [
            [TARGET_TILE // 2, TARGET_TILE // 2, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
    )


def test_win_sets_flags_and_waits_for_choice(tmp_path):
    state = new_state(tmp_path)
    _prepare_winning_board(state)

    result = move_tiles(state, "LEFT")

    assert state.won is True
    assert state.win_prompt_pending is True
    assert state.game_over is False
    assert any(event.kind == events.WON for event in result)

    # Keep playing: the prompt closes and the round continues.
    result = resolve_win_choice(state, keep_playing=True)
    assert result == []
    assert state.win_prompt_pending is False
    assert state.keep_playing_after_win is True
    assert state.game_over is False
    assert state.won is True

    # The prompt must never appear a second time.
    assert check_game_status(state) == []


def test_moves_are_ignored_while_the_win_prompt_is_open(tmp_path):
    state = new_state(tmp_path)
    _prepare_winning_board(state)
    move_tiles(state, "LEFT")

    before = [row[:] for row in state.board]
    assert move_tiles(state, "RIGHT") == []
    assert state.board == before


def test_end_game_after_win_saves_once(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state(tmp_path)
    _prepare_winning_board(state)
    move_tiles(state, "LEFT")

    result = resolve_win_choice(state, keep_playing=False)

    assert state.game_over is True
    assert state.win_prompt_pending is False
    assert state.score_saved is True
    assert any(event.kind == events.GAME_OVER for event in result)

    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1

    # A second status check must not add another record.
    assert check_game_status(state) == []
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1


def test_resolve_win_choice_without_a_prompt_does_nothing(tmp_path):
    state = new_state(tmp_path)
    assert resolve_win_choice(state, keep_playing=True) == []
    assert resolve_win_choice(state, keep_playing=False) == []
    assert state.game_over is False


# ---------------------------------------------------------------------------
# No valid moves (Module 12)
# ---------------------------------------------------------------------------
def test_no_valid_moves_ends_the_game_once(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state(tmp_path)
    state.board = [
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4],
        [4, 2, 4, 2],
    ]
    state.refresh_largest_tile()

    result = check_game_status(state)

    assert state.game_over is True
    assert "No more moves" in state.game_over_reason
    assert state.score_saved is True
    assert [event.kind for event in result] == [events.GAME_OVER]

    assert check_game_status(state) == []
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1


def test_moves_are_ignored_after_game_over(tmp_path):
    state = new_state(tmp_path)
    state.game_over = True
    before = [row[:] for row in state.board]
    assert move_tiles(state, "LEFT") == []
    assert state.board == before
