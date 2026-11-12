"""Tests for milestones, tile colours, the leaderboard file and the AI hint."""

import json
import random

import pytest

from core import events
from core.ai_solver import choose_best_move, evaluate_board, get_hint, score_moves
from core.board import make_empty_board
from core.constants import DIRECTIONS, get_tile_color
from core.game_flow import check_milestones, initialize_game
from core.leaderboard import (
    best_score_for_mode,
    get_leaderboard,
    load_local_leaderboards,
    save_progress,
    save_score,
)


def new_state(tmp_path=None, seed=7):
    path = str(tmp_path / "leaderboard.json") if tmp_path is not None else None
    return initialize_game(
        "Tester", "Classic", rng=random.Random(seed), data_path=path
    )


# ---------------------------------------------------------------------------
# Milestones (Module 11)
# ---------------------------------------------------------------------------
def test_milestones_fire_once_each(tmp_path):
    state = new_state(tmp_path)

    state.score = 250
    assert [event.data["score"] for event in check_milestones(state)] == [250]
    assert check_milestones(state) == []

    # Jumping over several milestones fires each one exactly once.
    state.score = 5000
    scores = [event.data["score"] for event in check_milestones(state)]
    assert scores == [750, 1500, 2500, 5000]
    assert check_milestones(state) == []
    assert state.milestones == [250, 750, 1500, 2500, 5000]


def test_milestone_events_have_the_right_kind(tmp_path):
    state = new_state(tmp_path)
    state.score = 250
    result = check_milestones(state)
    assert [event.kind for event in result] == [events.MILESTONE_REACHED]


# ---------------------------------------------------------------------------
# Tile colours (Module 10)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "value, name",
    [
        (0, "Empty Cell Color"),
        (2, "Lavender"),
        (4, "Sky Blue"),
        (8, "Turquoise"),
        (16, "Mint Green"),
        (32, "Golden Yellow"),
        (64, "Orange"),
        (128, "Coral Pink"),
        (256, "Violet"),
        (512, "Electric Blue"),
        (1024, "Deep Purple"),
        (2048, "Glowing Gold"),
        (8192, "Glowing Gold"),
    ],
)
def test_tile_colour_names(value, name):
    assert get_tile_color(value) == name


# ---------------------------------------------------------------------------
# Leaderboard (Module 6)
# ---------------------------------------------------------------------------
def test_missing_file_creates_empty_leaderboard(tmp_path):
    path = tmp_path / "does_not_exist.json"
    data = load_local_leaderboards(str(path))

    assert set(data["leaderboards"]) == {"Classic"}
    assert data["leaderboards"]["Classic"] == []
    assert data["best_scores"]["Classic"] == 0


def test_damaged_file_falls_back_to_empty_data(tmp_path):
    path = tmp_path / "leaderboard.json"
    path.write_text("{not valid json", encoding="utf-8")

    data = load_local_leaderboards(str(path))
    assert data["leaderboards"]["Classic"] == []
    assert data["best_scores"]["Classic"] == 0


def test_leaderboard_sorting_and_limit(tmp_path):
    path = tmp_path / "leaderboard.json"

    # 12 records; only the best 10 may remain.
    for index in range(1, 13):
        state = new_state(tmp_path)
        state.score = index * 10
        save_score(state, str(path), timestamp="2026-01-01T00:00:00")

    data = load_local_leaderboards(str(path))
    records = get_leaderboard(data, "Classic")

    assert len(records) == 10
    assert [record["score"] for record in records] == [
        120, 110, 100, 90, 80, 70, 60, 50, 40, 30
    ]
    assert best_score_for_mode(data, "Classic") == 120


def test_save_score_is_written_only_once_per_game(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state(tmp_path)
    state.score = 77

    first = save_score(state, str(path), timestamp="2026-01-01T00:00:00")
    second = save_score(state, str(path), timestamp="2026-01-01T00:00:00")

    assert first is not None
    assert first["player_name"] == "Tester"
    assert second is None
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1


def test_save_progress_keeps_the_best_score_without_a_record(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state(tmp_path)
    state.score = 150

    save_progress(state, str(path))

    data = load_local_leaderboards(str(path))
    assert data["best_scores"]["Classic"] == 150
    assert get_leaderboard(data, "Classic") == []


def test_best_score_is_never_lower_than_a_saved_record(tmp_path):
    path = tmp_path / "leaderboard.json"
    path.write_text(
        json.dumps(
            {
                "leaderboards": {
                    "Classic": [
                        {
                            "player_name": "Ada",
                            "score": 400,
                            "mode": "Classic",
                            "date": "2026-01-01T00:00:00",
                        }
                    ]
                },
                "best_scores": {"Classic": 0},
            }
        ),
        encoding="utf-8",
    )

    data = load_local_leaderboards(str(path))
    assert best_score_for_mode(data, "Classic") == 400


def test_damaged_records_are_dropped_or_repaired(tmp_path):
    path = tmp_path / "leaderboard.json"
    path.write_text(
        json.dumps(
            {
                "leaderboards": {
                    "Classic": [
                        42,                                   # not a record
                        {"player_name": "Bad", "score": "zz"},  # unusable score
                        {"score": 30},                          # no name or date
                        {"player_name": "Ada", "score": -5},     # negative score
                    ]
                },
                "best_scores": {"Classic": 0},
            }
        ),
        encoding="utf-8",
    )

    data = load_local_leaderboards(str(path))
    records = get_leaderboard(data, "Classic")

    assert [record["score"] for record in records] == [30, 0]
    assert all(isinstance(record["score"], int) for record in records)
    assert all(isinstance(record["player_name"], str) for record in records)
    assert all(isinstance(record["date"], str) for record in records)

    # Saving on top of a damaged file must still work.
    state = new_state(tmp_path)
    state.score = 99
    assert save_score(state, str(path), timestamp="2026-01-01T00:00:00") is not None
    assert best_score_for_mode(load_local_leaderboards(str(path)), "Classic") == 99


# ---------------------------------------------------------------------------
# AI solver behind the HINT button (Module 7)
# ---------------------------------------------------------------------------
def test_solver_returns_a_valid_direction_without_mutating_board():
    board = [
        [2, 2, 0, 0],
        [4, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    snapshot = [row[:] for row in board]

    direction = choose_best_move(board)

    assert direction in DIRECTIONS
    assert board == snapshot


def test_solver_returns_none_when_no_move_exists():
    board = [
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4],
        [4, 2, 4, 2],
    ]
    assert choose_best_move(board) is None
    assert score_moves(board) == {}


def test_solver_scores_every_changing_direction():
    board = [
        [2, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    values = score_moves(board)
    # A single corner tile can only move right or down.
    assert set(values) == {"RIGHT", "DOWN"}
    assert all(isinstance(value, float) for value in values.values())


def test_solver_prefers_a_merge_over_a_plain_slide():
    board = [
        [2, 2, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    values = score_moves(board)
    # LEFT and RIGHT merge the pair; DOWN only slides it.
    assert values["LEFT"] > values["DOWN"]


def test_evaluate_board_rewards_empty_cells():
    empty = make_empty_board()
    full = [[2] * 4 for _ in range(4)]
    assert evaluate_board(empty) > evaluate_board(full)


def test_get_hint_reads_the_state_without_changing_it(tmp_path):
    state = new_state(tmp_path)
    state.board = [
        [2, 2, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.refresh_largest_tile()
    snapshot = state.snapshot()

    direction = get_hint(state)

    assert direction in DIRECTIONS
    assert state.snapshot() == snapshot
    assert state.move_count == 0


def test_get_hint_is_silent_after_game_over_and_during_the_win_prompt(tmp_path):
    state = new_state(tmp_path)
    state.game_over = True
    assert get_hint(state) is None

    state.game_over = False
    state.win_prompt_pending = True
    assert get_hint(state) is None


def test_get_hint_returns_none_on_a_stuck_board(tmp_path):
    state = new_state(tmp_path)
    state.board = [
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4],
        [4, 2, 4, 2],
    ]
    state.refresh_largest_tile()
    assert get_hint(state) is None


# ---------------------------------------------------------------------------
# Core purity: no GUI library and no clock reads inside core/
# ---------------------------------------------------------------------------
def test_core_has_no_gui_or_clock_dependencies():
    import ast
    import pathlib

    core_dir = pathlib.Path(__file__).resolve().parents[1] / "core"
    forbidden_modules = {"pygame", "time", "datetime"}

    for path in core_dir.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "pygame" not in source.lower(), "%s mentions pygame" % path

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported = {(node.module or "").split(".")[0]}
            else:
                continue
            bad = imported & forbidden_modules
            assert not bad, "%s imports %s" % (path, sorted(bad))
