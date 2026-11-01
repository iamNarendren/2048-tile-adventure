"""
Local JSON storage for leaderboards, best scores and achievements
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
        "achievements": [],
        "stats": {
            "games_played": 0,
            "total_score": 0,
            "total_merges": 0,
            "largest_tile": 0,
        },
    }


def _resolve_path(path):
    """Use an explicit path (tests/web) or the default project save file."""
    return path or DEFAULT_DATA_PATH
WEB_STORAGE_KEY = "tile_adventure_2048_save"


def _read_text(path):
    """Read the saved JSON text (file on desktop, browser storage on the web)."""
    if sys.platform == "emscripten":
        import platform  # only exists inside the Pygbag web runtime

        value = platform.window.localStorage.getItem(WEB_STORAGE_KEY)
        if value is None:
            raise OSError("no saved data yet")
        return str(value)

    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _write_text(path, text):
    """Write the saved JSON text (file on desktop, browser storage on the web)."""
    if sys.platform == "emscripten":
        import platform

        try:
            platform.window.localStorage.setItem(WEB_STORAGE_KEY, text)
        except Exception as error:
            raise OSError(str(error))
        return

    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(text)


def load_local_leaderboards(path=None):
    """Pseudocode Module 6 - load Classic, Survival and Infection data.

    Missing files or slightly damaged JSON never crash the game: the loader
    falls back to a clean, empty data structure.  The returned dictionary is a
    normal Python value, so the Streamlit version can use it directly.
    """
    data = _empty_data()
    save_path = _resolve_path(path)

    try:
        loaded = json.loads(_read_text(save_path))
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
                    record for record in records if isinstance(record, dict)
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
            try:
                data["best_scores"][mode] = max(
                    data["best_scores"][mode], int(record.get("score", 0))
                )
            except (TypeError, ValueError):
                continue

    # --- Achievements ------------------------------------------------------
    loaded_achievements = loaded.get("achievements", [])
    if isinstance(loaded_achievements, list):
        data["achievements"] = [
            name for name in loaded_achievements if isinstance(name, str)
        ]

    # --- Lifetime statistics ----------------------------------------------
    loaded_stats = loaded.get("stats", {})
    if isinstance(loaded_stats, dict):
        for key in data["stats"]:
            try:
                data["stats"][key] = max(0, int(loaded_stats.get(key, 0)))
            except (TypeError, ValueError):
                data["stats"][key] = 0

    return data


def _write_data(data, path):
    """Write the save dictionary as readable, indented JSON.

    A read-only folder or a locked file must never crash a game in progress,
    so write errors are ignored.  Returns True on success.
    """
    save_path = _resolve_path(path)
    try:
        _write_text(save_path, json.dumps(data, indent=2, ensure_ascii=False))
    except OSError:
        return False
    return True

def save_score(state, path=None, timestamp=None):
    """Pseudocode Module 6 - add one score record and save everything.

    Guarded by ``state.score_saved`` so a round can be saved only once, even
    though Survival, Infection and check_game_status can all end the game.
    Returns the new record, or None if the score was already saved.

    The core never reads a wall clock.  ``timestamp`` may be supplied by the
    caller (tests) or by the UI through ``state.save_timestamp``; when neither
    is available the record simply has an empty date.
    """
    if state.score_saved:
        return None

    # The UI normally uses the default project save file; tests and the web
    # front-end can point a state at another file via state.data_path.
    target_path = path or state.data_path or None
    data = load_local_leaderboards(target_path)
    mode = state.mode if state.mode in MODES else "Classic"

    if timestamp is None:
        timestamp = getattr(state, "save_timestamp", "") or ""

    record = {
        "player_name": state.player_name,
        "score": int(state.score),
        "mode": mode,
        "date": timestamp,
    }

    data["leaderboards"][mode].append(record)
    # Highest score first; the ISO date breaks ties with the newest first.
    data["leaderboards"][mode].sort(
        key=lambda item: (-int(item.get("score", 0)), str(item.get("date", "")))
    )
    data["leaderboards"][mode] = data["leaderboards"][mode][:LEADERBOARD_LIMIT]

    data["best_scores"][mode] = max(
        data["best_scores"].get(mode, 0), state.score
    )

    stats = data["stats"]
    stats["games_played"] += 1
    stats["total_score"] += int(state.score)
    stats["total_merges"] += int(state.merge_count)
    stats["largest_tile"] = max(stats["largest_tile"], int(state.largest_tile))

    # Persist achievements unlocked during this session (lifetime view).
    for name in state.achievements:
        if name not in data["achievements"]:
            data["achievements"].append(name)

    _write_data(data, target_path)
    state.score_saved = True
    return record


def save_progress(state, path=None):
    """Persist best scores and achievements without adding a score record.

    Called when an achievement unlocks mid-game, so quitting to the menu does
    not lose the unlock.  It never increments ``games_played``.
    """
    target_path = path or state.data_path or None
    data = load_local_leaderboards(target_path)
    mode = state.mode if state.mode in MODES else "Classic"

    data["best_scores"][mode] = max(data["best_scores"].get(mode, 0), state.score)
    data["stats"]["largest_tile"] = max(
        data["stats"]["largest_tile"], int(state.largest_tile)
    )

    for name in state.achievements:
        if name not in data["achievements"]:
            data["achievements"].append(name)

    _write_data(data, target_path)
    return data


def get_leaderboard(data, mode):
    """Return a copy of one mode's leaderboard records."""
    return list(data.get("leaderboards", {}).get(mode, []))


def best_score_for_mode(data, mode):
    """Return the saved best score for a mode (0 when unknown)."""
    return int(data.get("best_scores", {}).get(mode, 0))


def lifetime_stats(data):
    """Summarise the save file for the Achievements progress bars."""
    best_scores = data.get("best_scores", {})
    return {
        "best_score": max([int(value) for value in best_scores.values()] or [0]),
        "largest_tile": int(data.get("stats", {}).get("largest_tile", 0)),
        "merges": int(data.get("stats", {}).get("total_merges", 0)),
        "games_played": int(data.get("stats", {}).get("games_played", 0)),
    }
