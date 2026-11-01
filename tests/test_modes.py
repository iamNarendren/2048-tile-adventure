"""Tests for Survival and Infection mode rules, with injected time."""

import json
import random

import pytest

from core import events
from core.board import move_tiles
from core.constants import (
    INFECTION_SPREAD_EVERY,
    SURVIVAL_BLOCK_DURATION,
    SURVIVAL_FIRST_BLOCK,
    SURVIVAL_TOTAL_TIME,
)
from core.game_flow import initialize_game
from core.modes.infection import (
    check_all_tiles_infected,
    spread_infection,
    transfer_infection_on_merge,
    update_infection_mode,
)
from core.modes.survival import (
    block_seconds_left,
    process_survival_successful_move,
    seconds_until_next_block,
    update_survival_clock,
)


def new_state(mode, tmp_path=None, seed=3):
    path = str(tmp_path / "leaderboard.json") if tmp_path is not None else None
    return initialize_game(
        "Tester", mode, now=0.0, rng=random.Random(seed), data_path=path
    )


# ---------------------------------------------------------------------------
# Survival (Module 8)
# ---------------------------------------------------------------------------
def test_survival_countdown_uses_injected_time(tmp_path):
    state = new_state("Survival", tmp_path)

    update_survival_clock(state, 0.0, rng=random.Random(1))
    assert state.survival_remaining_time == pytest.approx(SURVIVAL_TOTAL_TIME)

    update_survival_clock(state, 5.0, rng=random.Random(1))
    assert state.survival_remaining_time == pytest.approx(55.0)
    assert state.survival_block_active is False


def test_survival_blocks_start_at_10_and_20_seconds(tmp_path):
    state = new_state("Survival", tmp_path)
    rng = random.Random(42)

    result = update_survival_clock(state, 10.0, rng=rng)
    assert state.survival_block_active is True
    assert len(state.survival_blocked_cells) == 4
    assert state.survival_block_end_time == pytest.approx(13.0)
    assert state.survival_next_block_time == pytest.approx(20.0)
    assert any(event.kind == events.BLOCK_STARTED for event in result)

    # The block lasts exactly 3 seconds.
    update_survival_clock(state, 12.9, rng=rng)
    assert state.survival_block_active is True
    assert block_seconds_left(state, 12.9) == pytest.approx(0.1)

    result = update_survival_clock(state, 13.0, rng=rng)
    assert state.survival_block_active is False
    assert state.survival_blocked_cells == set()
    assert any(event.kind == events.BLOCK_ENDED for event in result)

    update_survival_clock(state, 19.9, rng=rng)
    assert state.survival_block_active is False

    result = update_survival_clock(state, 20.0, rng=rng)
    assert state.survival_block_active is True
    assert state.survival_next_block_time == pytest.approx(30.0)
    assert any(event.kind == events.BLOCK_STARTED for event in result)


def test_survival_warning_helpers(tmp_path):
    state = new_state("Survival", tmp_path)
    assert seconds_until_next_block(state, 9.5) == pytest.approx(0.5)
    update_survival_clock(state, 10.0, rng=random.Random(1))
    assert seconds_until_next_block(state, 10.0) is None


def test_survival_ends_at_zero_and_stops_clock(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Survival", tmp_path)

    result = update_survival_clock(state, SURVIVAL_TOTAL_TIME, rng=random.Random(1))
    assert state.survival_remaining_time == 0.0
    assert state.game_over is True
    assert state.score_saved is True
    assert any(event.kind == events.GAME_OVER for event in result)

    # The clock must not keep counting after game over.
    remaining_before = state.survival_remaining_time
    assert update_survival_clock(state, 90.0, rng=random.Random(1)) == []
    assert state.survival_remaining_time == remaining_before

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Survival"]) == 1


def test_process_survival_successful_move_is_a_no_op(tmp_path):
    state = new_state("Survival", tmp_path)
    before = state.snapshot()
    assert process_survival_successful_move(state) == []
    assert state.snapshot() == before


# ---------------------------------------------------------------------------
# Infection (Module 9)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "left, right, expected",
    [
        (False, False, False),
        (True, False, True),
        (False, True, True),
        (True, True, False),
    ],
)
def test_transfer_infection_on_merge(left, right, expected):
    assert transfer_infection_on_merge(left, right) is expected


def test_spread_infection_reaches_direct_neighbours_only():
    state = new_state("Infection")
    state.board = [
        [2, 4, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 8, 0],
        [0, 0, 0, 0],
    ]
    state.infected_tiles = {(0, 0)}

    newly = spread_infection(state)

    assert newly == {(0, 1)}
    assert state.infected_tiles == {(0, 0), (0, 1)}


def test_infection_spreads_on_every_third_update():
    state = new_state("Infection")
    state.board = [
        [2, 4, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 8, 0],
        [0, 0, 0, 0],
    ]
    state.infected_tiles = {(0, 0)}
    state.infection_move_counter = 0

    for _ in range(INFECTION_SPREAD_EVERY - 1):
        result = update_infection_mode(state)
        assert not any(event.kind == events.INFECTION_SPREAD for event in result)
        assert (0, 1) not in state.infected_tiles

    result = update_infection_mode(state)
    assert any(event.kind == events.INFECTION_SPREAD for event in result)
    assert state.infection_move_counter == 0
    assert (0, 1) in state.infected_tiles


def test_infection_spreads_on_third_successful_move(tmp_path):
    state = new_state("Infection", tmp_path)
    state.board = [
        [0, 2, 0, 0],
        [0, 4, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.infected_tiles = {(0, 1)}
    state.infection_move_counter = 0

    move_tiles(state, "LEFT", rng=random.Random(1), now=1.0)
    move_tiles(state, "RIGHT", rng=random.Random(1), now=2.0)
    result = move_tiles(state, "LEFT", rng=random.Random(1), now=3.0)

    assert state.move_count == 3
    assert any(event.kind == events.INFECTION_SPREAD for event in result)
    assert state.infection_move_counter == 0


def test_new_spawned_tile_is_not_infected(tmp_path):
    state = new_state("Infection", tmp_path)
    state.board = [
        [0, 2, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.infected_tiles = {(0, 1)}

    move_tiles(state, "LEFT", rng=random.Random(2), now=1.0)

    assert state.last_spawn is not None
    assert state.last_spawn.cell not in state.infected_tiles


def test_all_tiles_infected_ends_game_once(tmp_path):
    path = tmp_path / "leaderboard.json"
    state = new_state("Infection", tmp_path)
    state.board = [
        [2, 4, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.infected_tiles = {(0, 0), (0, 1)}
    state.infection_move_counter = 0

    result = update_infection_mode(state)

    assert check_all_tiles_infected(state) is True
    assert state.game_over is True
    assert any(event.kind == events.GAME_OVER for event in result)
    assert state.score_saved is True

    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["leaderboards"]["Infection"]) == 1


def test_check_all_tiles_infected_false_for_empty_board():
    state = new_state("Infection")
    state.board = [[0] * 4 for _ in range(4)]
    state.infected_tiles = set()
    assert check_all_tiles_infected(state) is False


def test_infected_marker_moves_vertically(tmp_path):
    state = new_state("Infection", tmp_path)
    state.board = [
        [0, 0, 0, 0],
        [2, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.infected_tiles = {(1, 0)}

    move_tiles(state, "UP", rng=random.Random(4), now=1.0)

    assert state.board[0][0] == 2
    assert (0, 0) in state.infected_tiles
    assert (1, 0) not in state.infected_tiles
