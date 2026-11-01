"""
Robot companion rules (Pseudocode Module 7).

The robot's colour depends on the score.  Clicking it three times asks the
AI solver to play one move.  All of this is pure Python; the drawing and the
bubble animation live in ``ui/robot_view.py``.
"""

from core import events
from core.ai_solver import run_ai_solver
from core.events import make_event


def update_robot_color(state):
    """Pseudocode Module 7 - pick the robot colour tier for the current score.

    Returns the colour *name* (the UI maps names to RGB values).
    """
    if state.score < 100:
        state.robot_color = "Blue"
    elif state.score < 500:
        state.robot_color = "Green"
    elif state.score < 1000:
        state.robot_color = "Purple"
    else:
        state.robot_color = "Gold"
    return state.robot_color


def handle_robot_click(state, now=0.0, rng=None):
    """Pseudocode Module 7 - count clicks and trigger the solver on the 3rd.

    The counter resets after the solver runs, so the player must click three
    more times for another hint.  The UI shows one dot per click and delays the
    third click briefly so the "thinking" bubble is visible.
    """
    if state.game_over or state.win_prompt_pending:
        return []

    state.robot_click_count += 1
    result_events = []

    if state.robot_click_count >= 3:
        state.robot_click_count = 0
        state.ai_solver_active = True
        result_events.append(make_event(events.ROBOT_THINKING))

        # run_ai_solver simulates all four directions, then performs the best
        # real move through move_tiles (Pseudocode Module 7).
        result_events.extend(run_ai_solver(state, now=now, rng=rng))

        state.ai_solver_active = False
        result_events.append(make_event(events.ROBOT_SOLVED))

    return result_events
