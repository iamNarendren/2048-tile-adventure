"""
Local JSON storage for the leaderboard and the best score
(Pseudocode Module 6).

This is the only core module that touches the file system.  Plain Python file
I/O is allowed by the assignment, and keeping it here means the game logic
never needs to know where the data lives.
"""

import json
import os
import sys

from core.constants import LEADERBOARD_FILENAME, LEADERBOARD_LIMIT, MODES

# Save next to the project folder, regardless of the current working directory.
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)  # running as .exe: use the .exe's folder
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DATA_PATH = os.path.join(PROJECT_ROOT, LEADERBOARD_FILENAME)


def _empty_data():
    """Create a fresh, valid save-data dictionary."""
    return {
        "leaderboards": {mode: [] for mode in MODES},
        "best_scores": {mode: 0 for mode in MODES},
    }


def _resolve_path(path):
    """Use an explicit path (used by the tests) or the default save file."""
    return path or DEFAULT_DATA_PATH


def _clean_record(record, mode="Classic"):
    """Turn one loaded JSON item into a valid record, or None.

    A hand-edited or damaged save file can hold anything, so every field is
    checked here.  After this function the rest of the game can rely on
    ``score`` being an int and on the three text fields being strings.
    """
    if not isinstance(record, dict):
        return None
    try:
        score = max(0, int(record.get("score", 0)))
    except (TypeError, ValueError):
        return None
    return {
        "player_name": str(record.get("player_name", "Player")),
        "score": score,
        "mode": mode,
        "date": str(record.get("date", "")),
    }


def load_local_leaderboards(path=None):
    """Pseudocode Module 6 - load the saved leaderboard and best score.

    Missing files or slightly damaged JSON never crash the game: the loader
    falls back to a clean, empty data structure.  The returned dictionary is a
    normal Python value, so any front end can use it directly.
    """
    data = _empty_data()
    save_path = _resolve_path(path)

    try:
        with open(save_path, "r", encoding="utf-8") as file:
            loaded = json.load(file)
    except (OSError, ValueError):
        return data

    if not isinstance(loaded, dict):
        return data

    # --- Leaderboards ------------------------------------------------------
    loaded_boards = loaded.get("leaderboards", {})
    if isinstance(loaded_boards, dict):
        for mode in MODES:
            records = loaded_boards.get(mode, [])
            if isinstance(records, list):
                data["leaderboards"][mode] = [
                    clean_record
                    for clean_record in (_clean_record(item) for item in records)
                    if clean_record is not None
                ][:LEADERBOARD_LIMIT]

    # --- Best scores -------------------------------------------------------
    loaded_best = loaded.get("best_scores", {})
    if isinstance(loaded_best, dict):
        for mode in MODES:
            try:
                data["best_scores"][mode] = max(0, int(loaded_best.get(mode, 0)))
            except (TypeError, ValueError):
                data["best_scores"][mode] = 0

    # Make sure a best score is never lower than a saved leaderboard score.
    for mode in MODES:
        for record in data["leaderboards"][mode]:
            data["best_scores"][mode] = max(
                data["best_scores"][mode], record["score"]
            )

    return data


def _write_data(data, path):
    """Write the save dictionary as readable, indented JSON.

    A read-only folder or a locked file must never crash a game in progress,
    so write errors are ignored.  Returns True on success.
    """
    save_path = _resolve_path(path)
    try:
        folder = os.path.dirname(save_path)
        if folder:
            os.makedirs(folder, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    except OSError:
        return False
    return True


def save_score(state, path=None, timestamp=None):
    """Pseudocode Module 6 - add one score record and save everything.

    Guarded by ``state.score_saved`` so a round can be saved only once, even
    if more than one check tries to end the game.
    Returns the new record, or None if the score was already saved.

    The core never reads a wall clock.  ``timestamp`` may be supplied by the
    caller (tests) or by the UI through ``state.save_timestamp``; when neither
    is available the record simply has an empty date.
    """
    if state.score_saved:
        return None

    # The UI uses the default project save file; the tests point a state at a
    # temporary file through state.data_path.
    target_path = path or state.data_path or None
    data = load_local_leaderboards(target_path)
    mode = state.mode if state.mode in MODES else "Classic"

    if timestamp is None:
        timestamp = getattr(state, "save_timestamp", "") or ""

    record = {
        "player_name": str(state.player_name),
        "score": max(0, int(state.score)),
        "mode": mode,
        "date": str(timestamp),
    }

    data["leaderboards"][mode].append(record)
    # Highest score first; equal scores are ordered by date, earliest first.
    data["leaderboards"][mode].sort(key=lambda item: (-item["score"], item["date"]))
    data["leaderboards"][mode] = data["leaderboards"][mode][:LEADERBOARD_LIMIT]

    data["best_scores"][mode] = max(
        data["best_scores"].get(mode, 0), state.score
    )

    _write_data(data, target_path)
    state.score_saved = True
    return record


def save_progress(state, path=None):
    """Persist the best score without adding a leaderboard record.

    Called when the player leaves a round that is still in progress, so
    quitting to the menu does not lose a new best score.
    """
    target_path = path or state.data_path or None
    data = load_local_leaderboards(target_path)
    mode = state.mode if state.mode in MODES else "Classic"

    data["best_scores"][mode] = max(data["best_scores"].get(mode, 0), state.score)

    _write_data(data, target_path)
    return data


def get_leaderboard(data, mode):
    """Return a copy of one mode's leaderboard records."""
    return list(data.get("leaderboards", {}).get(mode, []))


def best_score_for_mode(data, mode):
    """Return the saved best score for a mode (0 when unknown)."""
    return int(data.get("best_scores", {}).get(mode, 0))

