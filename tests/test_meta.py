"""Tests for achievements, milestones, leaderboards, robot and AI solver."""

import json
import random

import pytest

from core import events
from core.ai_solver import choose_best_move, evaluate_board, score_moves
from core.achievements import (
    achievement_progress,
    check_achievements,
    check_milestones,
)
from core.board import make_empty_board
from core.constants import DIRECTIONS, get_tile_color
from core.game_flow import initialize_game
from core.leaderboard import (
    best_score_for_mode,
    get_leaderboard,
    lifetime_stats,
    load_local_leaderboards,
    save_progress,
    save_score,
)
from core.robot import handle_robot_click, update_robot_color


def new_state(mode="Classic", tmp_path=None, seed=7):
    path = str(tmp_path / "leaderboard.json") if tmp_path is not None else None
    return initialize_game(
        "Tester", mode, now=0.0, rng=random.Random(seed), data_path=path
    )


# ---------------------------------------------------------------------------
# Achievements and milestones (Module 11)
# ---------------------------------------------------------------------------
def test_all_achievements_unlock_once(tmp_path):
    state = new_state("Classic", tmp_path)

    state.score = 100
    assert [event.data["name"] for event in check_achievements(state)] == ["Score 100"]
    assert check_achievements(state) == []

    state.score = 500
    assert [event.data["name"] for event in check_achievements(state)] == ["Score 500"]
    state.score = 1000
    assert [event.data["name"] for event in check_achievements(state)] == ["Score 1000"]

    state.largest_tile = 2048
    assert [event.data["name"] for event in check_achievements(state)] == ["Reach 2048"]

    state.merge_count = 1
    assert [event.data["name"] for event in check_achievements(state)] == ["First Merge"]

    # Everything is unlocked now; no event can fire again.
    assert check_achievements(state) == []
    assert len(state.achievements) == 5


def test_first_merge_unlocks_after_a_real_merge(tmp_path):
    state = new_state("Classic", tmp_path)
    state.board = [
        [2, 2, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    from core.board import move_tiles

    result = move_tiles(state, "LEFT", rng=random.Random(1), now=1.0)
    names = [
        event.data["name"]
        for event in result
        if event.kind == events.ACHIEVEMENT_UNLOCKED
    ]
    assert "First Merge" in names
    assert state.merge_count == 1


def test_milestones_fire_once_each(tmp_path):
    state = new_state("Classic", tmp_path)

    state.score = 250
    assert [event.data["score"] for event in check_milestones(state)] == [250]
    assert check_milestones(state) == []

    # Jumping over several milestones fires each one exactly once.
    state.score = 5000
    scores = [event.data["score"] for event in check_milestones(state)]
    assert scores == [750, 1500, 2500, 5000]
    assert check_milestones(state) == []
    assert state.milestones == [250, 750, 1500, 2500, 5000]


def test_achievement_progress_uses_session_and_lifetime(tmp_path):
    state = new_state("Classic", tmp_path)
    state.score = 320
    state.largest_tile = 1024
    state.merge_count = 0

    lifetime = {"best_score": 900, "largest_tile": 512, "merges": 4}

    assert achievement_progress("Score 500", state, lifetime) == (900, 500)
    assert achievement_progress("Reach 2048", state, lifetime) == (1024, 2048)
    assert achievement_progress("First Merge", state, lifetime) == (4, 1)
    assert achievement_progress("Score 100") == (0, 100)


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
def test_missing_file_creates_empty_leaderboards(tmp_path):
    path = tmp_path / "does_not_exist.json"
    data = load_local_leaderboards(str(path))

    assert set(data["leaderboards"]) == {"Classic", "Survival", "Infection"}
    for mode in data["leaderboards"]:
        assert data["leaderboards"][mode] == []
        assert data["best_scores"][mode] == 0
    assert data["achievements"] == []


def test_leaderboard_sorting_limit_and_modes(tmp_path):
    path = tmp_path / "leaderboard.json"

    # 12 Classic records; only the best 10 may remain.
    for index in range(1, 13):
        state = new_state("Classic", tmp_path)
        state.score = index * 10
        save_score(state, str(path), timestamp="2026-01-01T00:00:00")

    # A separate Survival board must not be mixed in.
    survival_state = new_state("Survival", tmp_path)
    survival_state.score = 999
    save_score(survival_state, str(path), timestamp="2026-01-02T00:00:00")

    data = load_local_leaderboards(str(path))
    classic = get_leaderboard(data, "Classic")

    assert len(classic) == 10
    assert [record["score"] for record in classic] == [
        120, 110, 100, 90, 80, 70, 60, 50, 40, 30
    ]
    assert len(get_leaderboard(data, "Survival")) == 1
    assert get_leaderboard(data, "Infection") == []
    assert best_score_for_mode(data, "Classic") == 120
    assert best_score_for_mode(data, "Survival") == 999


def test_save_score_is_written_only_once_per_game(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Classic", tmp_path)
    state.score = 77

    first = save_score(state, str(path), timestamp="2026-01-01T00:00:00")
    second = save_score(state, str(path), timestamp="2026-01-01T00:00:00")

    assert first is not None
    assert second is None
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Classic"]) == 1
    assert data["stats"]["games_played"] == 1


def test_save_progress_persists_achievements_without_a_score(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Classic", tmp_path)
    state.achievements = ["First Merge", "Score 100"]
    state.score = 150

    save_progress(state, str(path))

    data = load_local_leaderboards(str(path))
    assert set(data["achievements"]) == {"First Merge", "Score 100"}
    assert data["best_scores"]["Classic"] == 150
    assert data["stats"]["games_played"] == 0     # no score record was added
    assert get_leaderboard(data, "Classic") == []

    stats = lifetime_stats(data)
    assert stats["best_score"] == 150


# ---------------------------------------------------------------------------
# Robot (Module 7)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "score, colour",
    [
        (0, "Blue"),
        (99, "Blue"),
        (100, "Green"),
        (499, "Green"),
        (500, "Purple"),
        (999, "Purple"),
        (1000, "Gold"),
        (9999, "Gold"),
    ],
)
def test_robot_colour_tiers(score, colour):
    state = new_state("Classic")
    state.score = score
    assert update_robot_color(state) == colour
    assert state.robot_color == colour


def test_robot_click_triggers_solver_on_third_click(tmp_path):
    state = new_state("Classic", tmp_path)
    state.board = [
        [2, 0, 0, 0],
        [4, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.refresh_largest_tile()

    assert handle_robot_click(state, now=1.0) == []
    assert state.robot_click_count == 1
    assert handle_robot_click(state, now=2.0) == []
    assert state.robot_click_count == 2

    result = handle_robot_click(state, now=3.0)
    kinds = [event.kind for event in result]

    assert events.ROBOT_THINKING in kinds
    assert events.ROBOT_SOLVED in kinds
    assert events.MOVED in kinds
    assert state.robot_click_count == 0
    assert state.ai_solver_active is False
    assert state.move_count == 1


def test_robot_ignores_clicks_after_game_over(tmp_path):
    state = new_state("Classic", tmp_path)
    state.game_over = True
    assert handle_robot_click(state, now=1.0) == []
    assert state.robot_click_count == 0


# ---------------------------------------------------------------------------
# AI solver (Module 7 / section 6)
# ---------------------------------------------------------------------------
def test_solver_returns_a_valid_direction_without_mutating_board():
    board = [
        [2, 2, 0, 0],
        [4, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    snapshot = [row[:] for row in board]
    infected = {(0, 0)}

    direction = choose_best_move(board, infected_tiles=infected)

    assert direction in DIRECTIONS
    assert board == snapshot
    assert infected == {(0, 0)}


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


def test_evaluate_board_rewards_empty_cells():
    empty = make_empty_board()
    full = [[2] * 4 for _ in range(4)]
    assert evaluate_board(empty) > evaluate_board(full)


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
