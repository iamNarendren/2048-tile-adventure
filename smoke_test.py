"""
Headless smoke test for 2048 Tile Adventure.

This script does not replace the unit tests: it drives the real Pygame screens
with the dummy video/audio drivers and saves a screenshot at every important
step.  Run it from the project folder::

    python smoke_test.py

It exercises:
  * all three main-menu options and the menu sound button,
  * the name-entry screen,
  * the Classic round: moves, HUD Restart / Menu / Sound,
  * the HINT button and the H key (including the toggle),
  * the win prompt (Keep Playing and End Game),
  * the game-over screen and its three buttons,
  * the leaderboard screen.

Screenshots are written to ``smoke_screenshots/``.
"""

import os
import sys
import tempfile

# The dummy drivers must be selected before pygame is imported.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from core.constants import DIRECTIONS  # noqa: E402
from core.game_flow import check_game_status  # noqa: E402
from ui.app import GameApp  # noqa: E402

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(PROJECT_ROOT, "smoke_screenshots")
STEP = 1.0 / 60.0

DIRECTION_KEYS = (pygame.K_LEFT, pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN)


class SmokeFailure(AssertionError):
    """Raised when an expected screen or state does not appear."""


def check(condition, message):
    """Assert with a clear smoke-test message."""
    if not condition:
        raise SmokeFailure(message)
    print("  ok  - %s" % message)


def pump(app, seconds=0.6, screenshot=None):
    """Run the app for a number of frames without a real event loop."""
    frames = max(1, int(seconds / STEP))
    for _ in range(frames):
        app.update(STEP)
        app.draw()
    if screenshot is not None:
        save_screenshot(app, screenshot)


def save_screenshot(app, name):
    """Save the current window to the screenshots folder."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, name)
    pygame.image.save(app.screen, path)
    print("  shot - %s" % os.path.relpath(path, PROJECT_ROOT))


def click(app, rect, settle=0.7):
    """Click the centre of a rectangle and let transitions finish."""
    check(rect is not None, "expected a clickable rectangle")
    app.handle_click(rect.center)
    pump(app, settle)


def click_named(app, key, settle=0.7):
    """Draw once, then click a named top-level rectangle."""
    rects = app.draw()
    click(app, rects.get(key), settle)


def make_moves(app, count, screenshot_last=None):
    """Play until ``count`` successful moves happen (or the game ends)."""
    made = 0
    attempts = 0
    index = 0
    while made < count and attempts < 120:
        if app.state.game_over or app.state.win_prompt_pending:
            break
        before = app.state.move_count
        app.handle_key(DIRECTION_KEYS[index % len(DIRECTION_KEYS)])
        index += 1
        attempts += 1

        if app.state.move_count > before:
            made += 1
        pump(app, 0.32)

    if screenshot_last is not None:
        app.draw()
        save_screenshot(app, screenshot_last)
    return made


def force_winning_move(app):
    """Put two 1024 tiles on the board and merge them to reach 2048."""
    state = app.state
    state.game_over = False
    state.game_over_reason = ""
    state.win_prompt_pending = False
    state.won = False
    state.board = [
        [1024, 1024, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
    ]
    state.refresh_largest_tile()
    app.pending_direction = None
    app.handle_key(pygame.K_LEFT)
    pump(app, 0.55)


def force_dead_board(app):
    """Fill the board with a pattern that has no legal move left.

    The round is then ended by the same core check the real game uses after
    every move, so the game-over screen is reached exactly as in play.
    """
    state = app.state
    state.board = [
        [2, 4, 2, 4],
        [4, 2, 4, 2],
        [2, 4, 2, 4],
        [4, 2, 4, 2],
    ]
    state.refresh_largest_tile()
    app.pending_direction = None
    app._process_events(check_game_status(state), app.ui_time)
    pump(app, 0.5)


def main():
    print("2048 Tile Adventure - headless smoke test")
    print("Pygame", pygame.version.ver)

    data_path = os.path.join(
        tempfile.gettempdir(), "tile_adventure_smoke_%d.json" % os.getpid()
    )
    if os.path.exists(data_path):
        os.remove(data_path)

    app = GameApp(seed=1234, data_path=data_path)

    try:
        # ------------------------------------------------------------------
        # 1. Main menu
        # ------------------------------------------------------------------
        print("\n[1] Main menu")
        pump(app, 0.2, "01_main_menu.png")
        check(app.screen_name == "menu", "main menu is visible")

        # Sound toggle button on the menu.
        before = app.sound.enabled
        click_named(app, "sound", settle=0.05)
        check(app.sound.enabled != before, "menu sound button toggles audio")
        click_named(app, "sound", settle=0.05)
        check(app.sound.enabled == before, "sound button toggles back")

        # ------------------------------------------------------------------
        # 2. Name entry and the start of a round
        # ------------------------------------------------------------------
        print("\n[2] Name entry")
        click_named(app, "Classic")
        check(app.screen_name == "name", "Play Classic opens the name screen")
        app.handle_text("Ada")
        pump(app, 0.15, "02_name_entry.png")
        app.handle_key(pygame.K_RETURN)
        pump(app, 0.8, "03_classic_game.png")
        check(app.screen_name == "game", "the round started")
        check(app.state.player_name == "Ada", "typed name is used")
        check(
            sum(1 for row in app.state.board for value in row if value) == 2,
            "the board starts with two tiles",
        )

        # ------------------------------------------------------------------
        # 3. HUD buttons and moves
        # ------------------------------------------------------------------
        print("\n[3] HUD and moves")
        before = app.sound.enabled
        click(app, app.draw()["hud"]["sound"], settle=0.05)
        check(app.sound.enabled != before, "HUD sound button toggles audio")
        click(app, app.draw()["hud"]["sound"], settle=0.05)
        check(app.sound.enabled == before, "HUD sound button toggles back")

        made = make_moves(app, 4, "04_after_moves.png")
        check(made >= 1, "the board accepts arrow/WASD moves")
        moves_before = app.state.move_count
        click(app, app.draw()["hud"]["restart"], settle=0.8)
        check(app.state.move_count == 0, "HUD Restart resets the round")
        check(moves_before > 0, "restart happened after real moves")

        # ------------------------------------------------------------------
        # 4. The HINT button
        # ------------------------------------------------------------------
        print("\n[4] Hint")
        make_moves(app, 2)
        check(app.hint_direction is None, "no hint is shown before asking")
        click(app, app.draw()["hint"], settle=0.05)
        check(
            app.hint_direction in DIRECTIONS,
            "HINT button shows one of the four directions",
        )
        hinted = app.hint_direction
        moves_before = app.state.move_count
        app.draw()
        save_screenshot(app, "05_hint_shown.png")
        check(
            app.state.move_count == moves_before,
            "the hint does not play the move itself",
        )

        click(app, app.draw()["hint"], settle=0.05)
        check(app.hint_direction is None, "clicking HINT again hides the hint")

        app.handle_key(pygame.K_h)
        pump(app, 0.05)
        check(app.hint_direction in DIRECTIONS, "the H key also shows a hint")

        # Making the suggested move clears the hint.
        app.handle_key(
            {
                "LEFT": pygame.K_LEFT,
                "RIGHT": pygame.K_RIGHT,
                "UP": pygame.K_UP,
                "DOWN": pygame.K_DOWN,
            }[app.hint_direction]
        )
        pump(app, 0.45, "06_after_hint_move.png")
        check(app.hint_direction is None, "a successful move clears the hint")
        check(hinted in DIRECTIONS, "the first hint was a real direction")

        # ------------------------------------------------------------------
        # 5. Win prompt
        # ------------------------------------------------------------------
        print("\n[5] Win prompt")
        force_winning_move(app)
        check(app.state.win_prompt_pending, "2048 tile opens the win prompt")
        app.draw()
        save_screenshot(app, "07_win_overlay.png")
        check(app.hint_direction is None, "the hint is hidden by the win prompt")
        app.handle_key(pygame.K_h)
        check(app.hint_direction is None, "HINT is ignored while the prompt is open")

        win_rects = app._rects["win"]
        click(app, win_rects["keep"], settle=0.4)
        check(not app.state.win_prompt_pending, "Keep Playing closes the prompt")
        check(app.state.game_over is False, "Keep Playing continues the round")
        pump(app, 0.2, "08_win_keep_playing.png")

        # Restart, win again, then End Game.
        click(app, app.draw()["hud"]["restart"], settle=0.8)
        force_winning_move(app)
        check(app.state.win_prompt_pending, "win prompt appears again after restart")
        click(app, app._rects["win"]["end"], settle=0.5)
        check(app.state.game_over, "End Game ends the round")
        check(app.state.score_saved, "score saved once at game over")
        app.draw()
        save_screenshot(app, "09_game_over.png")

        # ------------------------------------------------------------------
        # 6. Game-over buttons and the leaderboard
        # ------------------------------------------------------------------
        print("\n[6] Game over and leaderboard")
        click(app, app._rects["over"]["leaderboard"], settle=0.8)
        check(app.screen_name == "leaderboard", "game-over Leaderboard opens")
        app.draw()
        save_screenshot(app, "10_leaderboard_from_game_over.png")
        click(app, app.draw()["back"], settle=0.8)
        check(app.screen_name == "game", "leaderboard returns to game over")
        check(app.state.game_over, "game-over screen is still shown")

        click(app, app._rects["over"]["replay"], settle=0.8)
        check(app.screen_name == "game", "Replay starts a new round")
        check(app.state.game_over is False, "Replay clears game over")

        # A dead board must end the round by itself.
        force_dead_board(app)
        check(app.state.game_over, "a board with no moves ends the round")
        check("No more moves" in app.state.game_over_reason, "no-moves reason is set")
        app.draw()
        save_screenshot(app, "11_no_moves_game_over.png")
        click(app, app._rects["over"]["menu"], settle=0.8)
        check(app.screen_name == "menu", "game over returns to the main menu")

        click_named(app, "Leaderboard")
        check(app.screen_name == "leaderboard", "Leaderboard opens from the menu")
        app.draw()
        save_screenshot(app, "12_leaderboard.png")
        app.handle_key(pygame.K_ESCAPE)
        pump(app, 0.8)
        check(app.screen_name == "menu", "ESC leaves the leaderboard")

        # ------------------------------------------------------------------
        # 7. Quit
        # ------------------------------------------------------------------
        print("\n[7] Quit")
        click_named(app, "Quit", settle=0.05)
        check(app.running is False, "Quit menu option stops the app")

        print("\nAll smoke checks passed.")
        print("Screenshots: %s" % SCREENSHOT_DIR)

        # Show that the smoke run really wrote leaderboard records.
        from core.leaderboard import load_local_leaderboards

        data = load_local_leaderboards(data_path)
        print("Saved records:", len(data["leaderboards"]["Classic"]))
        print("Best score:", data["best_scores"]["Classic"])

    finally:
        app.shutdown()
        if os.path.exists(data_path):
            try:
                os.remove(data_path)
            except OSError:
                pass


if __name__ == "__main__":
    try:
        main()
    except SmokeFailure as error:
        print("\nSMOKE TEST FAILED: %s" % error)
        sys.exit(1)
