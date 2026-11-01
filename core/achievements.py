"""
Achievements and milestones (Pseudocode Module 11).

Achievements are checked after every successful move.  Each one can unlock
only once per game session (the name is stored in ``state.achievements``).
The UI also shows lifetime unlocks loaded from the save file.

Milestones are score thresholds defined in ``core.constants``; each one fires
once per game and is recorded in ``state.milestones``.
"""

from core import events
from core.constants import ACHIEVEMENTS, MILESTONES
from core.events import make_event


def _achievement_earned(state, name):
    """Return True when the current state satisfies one achievement."""
    definition = ACHIEVEMENTS[name]
    metric = definition["metric"]
    target = definition["target"]

    if metric == "score":
        return state.score >= target
    if metric == "largest_tile":
        return state.largest_tile >= target
    if metric == "merges":
        return state.merge_count >= target
    return False


def check_achievements(state):
    """Pseudocode Module 11 - unlock every achievement the player now meets.

    Returns a list of achievement_unlocked events so the UI can show a toast
    and play a sound.  A name is only added once, so re-checking is safe.
    """
    unlocked_events = []

    for name in ACHIEVEMENTS:
        if name in state.achievements:
            continue
        if _achievement_earned(state, name):
            state.achievements.append(name)
            unlocked_events.append(
                make_event(
                    events.ACHIEVEMENT_UNLOCKED,
                    name=name,
                    description=ACHIEVEMENTS[name]["description"],
                )
            )

    return unlocked_events


def check_milestones(state):
    """Pseudocode Module 11 - fire each configured milestone once per game."""
    milestone_events = []

    for milestone in sorted(MILESTONES):
        if state.score >= milestone and milestone not in state.milestones:
            state.milestones.append(milestone)
            milestone_events.append(
                make_event(events.MILESTONE_REACHED, score=milestone)
            )

    return milestone_events


def achievement_progress(name, state=None, lifetime=None):
    """Return (current, target) for an achievement's progress bar.

    ``lifetime`` comes from ``leaderboard.lifetime_stats`` and lets the
    Achievements screen show progress across all games.  The best value of the
    current session and the saved lifetime data is used.
    """
    definition = ACHIEVEMENTS[name]
    target = definition["target"]
    metric = definition["metric"]
    lifetime = lifetime or {}

    if metric == "score":
        current = max(state.score if state else 0, int(lifetime.get("best_score", 0)))
    elif metric == "largest_tile":
        current = max(
            state.largest_tile if state else 0,
            int(lifetime.get("largest_tile", 0)),
        )
    elif metric == "merges":
        current = max(
            state.merge_count if state else 0,
            int(lifetime.get("merges", 0)),
        )
    else:
        current = 0

    return current, target
