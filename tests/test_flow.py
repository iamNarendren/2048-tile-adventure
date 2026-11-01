"""Tests for game setup, invalid moves, win flow and game-over detection."""

import random

import pytest

from core import events
from core.board import move_tiles
from core.constants import (
    GRID_SIZE,
    SURVIVAL_FIRST_BLOCK,
    SURVIVAL_TOTAL_TIME,
    TARGET_TILE,
)
from core.game_flow import (
    check_game_status,
    clean_player_name,
    initialize_game,
    resolve_win_choice,
    start_new_game,
    update_score,
)


def new_state(mode="Classic", tmp_path=None, seed=11):
    path = str(tmp_path / "leaderboard.json") if tmp_path is not None else None
    return initialize_game(
        "Tester", mode, now=0.0, rng=random.Random(seed), data_path=path
    )


def set_board(state, board, infected=None):
    state.board = [row[:] for row in board]
    state.infected_tiles = set(infected or ())
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
@pytest.mark.parametrize("mode", ["Classic", "Survival", "Infection"])
def test_start_has_exactly_two_tiles(mode, tmp_path):
    state = new_state(mode, tmp_path)
    assert sum(1 for row in state.board for value in row if value != 0) == 2
    assert state.score == 0
    assert state.move_count == 0
    assert state.game_over is False
    assert state.won is False
    assert state.best_score == 0
    assert state.robot_color == "Blue"


def test_infection_starts_with_one_infected_tile(tmp_path):
    state = new_state("Infection", tmp_path)
    assert len(state.infected_tiles) == 1
    cell = next(iter(state.infected_tiles))
    assert state.board[cell[0]][cell[1]] != 0
    assert state.infection_move_counter == 0


def test_start_new_game_resets_every_mode(tmp_path):
    for mode in ("Classic", "Survival", "Infection"):
        state = new_state(mode, tmp_path)
        state.score = 999
        state.best_score = 5000
        state.game_over = True
        state.won = True
        state.keep_playing_after_win = True
        state.win_prompt_pending = True
        state.board = [[2] * GRID_SIZE for _ in range(GRID_SIZE)]
        state.infected_tiles = {(0, 0)}
        state.infection_move_counter = 2
        state.survival_remaining_time = 1.0
        state.survival_block_active = True
        state.survival_blocked_cells = {(0, 0)}
        state.survival_next_block_time = 99
        state.survival_block_end_time = 99
        state.robot_click_count = 2
        state.ai_solver_active = True
        state.score_saved = True
        state.merge_count = 7
        state.milestones = [250]
        state.achievements = ["First Merge"]
        state.game_over_reason = "old reason"

        start_new_game(state, now=0.0, rng=random.Random(5))

        assert state.score == 0
        assert state.best_score == 5000          # best score survives a restart
        assert state.move_count == 0
        assert state.game_over is False
        assert state.won is False
        assert state.keep_playing_after_win is False
        assert state.win_prompt_pending is False
        assert state.game_over_reason == ""
        assert state.score_saved is False
        assert state.merge_count == 0
        assert state.milestones == []
        assert state.achievements == ["First Merge"]   # session achievements stay
        assert state.robot_click_count == 0
        assert state.ai_solver_active is False
        assert state.survival_remaining_time == SURVIVAL_TOTAL_TIME
        assert state.survival_block_active is False
        assert state.survival_blocked_cells == set()
        assert state.survival_next_block_time == SURVIVAL_FIRST_BLOCK
        assert state.survival_block_end_time == 0.0
        assert state.infection_move_counter == 0
        assert sum(1 for row in state.board for value in row if value) == 2
        if mode == "Infection":
            assert len(state.infected_tiles) == 1
        else:
            assert state.infected_tiles == set()


# ---------------------------------------------------------------------------
# Score (Module 6)
# ---------------------------------------------------------------------------
def test_update_score_and_best_score():
    state = new_state("Classic")
    state.best_score = 50
    update_score(state, 30)
    assert state.score == 30
    assert state.best_score == 50
    update_score(state, 40)
    assert state.score == 70
    assert state.best_score == 70


# ---------------------------------------------------------------------------
# Invalid move (Module 4)
# ---------------------------------------------------------------------------
def test_invalid_move_changes_nothing(tmp_path):
    for mode in ("Classic", "Infection"):
        state = new_state(mode, tmp_path)
        set_board(
            state,
            [
                [2, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
            ],
            infected={(0, 0)} if mode == "Infection" else (),
        )
        before = [row[:] for row in state.board]
        before_infected = set(state.infected_tiles)

        result = move_tiles(state, "LEFT", now=1.0)

        assert result == []
        assert state.board == before
        assert state.move_count == 0
        assert state.infected_tiles == before_infected
        assert state.infection_move_counter == 0
        assert state.score == 0
        assert state.last_move is None


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
    state = new_state("Classic", tmp_path)
    _prepare_winning_board(state)

    result = move_tiles(state, "LEFT", now=0.0)

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


def test_end_game_after_win_saves_once(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Classic", tmp_path)
    _prepare_winning_board(state)
    move_tiles(state, "LEFT", now=0.0)

    result = resolve_win_choice(state, keep_playing=False)

    assert state.game_over is True
    assert state.win_prompt_pending is False
    assert state.score_saved is True
    assert any(event.kind == events.GAME_OVER for event in result)
    assert len(state.achievements) == 5   # all achievements were earned

    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1

    # A second status check must not add another record.
    assert check_game_status(state) == []
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1


# ---------------------------------------------------------------------------
# No valid moves (Module 12)
# ---------------------------------------------------------------------------
def test_no_valid_moves_ends_the_game_once(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Classic", tmp_path)
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


def test_infection_all_infected_ends_game_once(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Infection", tmp_path)
    set_board(
        state,
        [
            [2, 4, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
        infected={(0, 0), (0, 1)},
    )

    result = check_game_status(state)
    assert state.game_over is True
    assert "infected" in state.game_over_reason.lower()
    assert [event.kind for event in result] == [events.GAME_OVER]

    assert check_game_status(state) == []
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Infection"]) == 1
