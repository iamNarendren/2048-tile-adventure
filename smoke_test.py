"""
Headless smoke test for 2048 Tile Adventure.

This script does not replace the unit tests: it drives the real Pygame screens
with the dummy video/audio drivers and saves a screenshot at every important
step.  Run it from the project folder::

    python smoke_test.py

It exercises:
  * all six main-menu options,
  * the name-entry screen,
  * all three game modes (Classic, Survival, Infection),
  * HUD Restart / Menu / Sound buttons,
  * the robot's three-click AI hint,
  * the win prompt (Keep Playing and End Game),
  * the game-over screen and its three buttons,
  * leaderboard tabs and the achievements screen.

Screenshots are written to ``smoke_screenshots/``.
"""

import os
import sys
import tempfile

# The dummy drivers must be selected before pygame is imported.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from core.constants import SURVIVAL_TOTAL_TIME  # noqa: E402
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


def start_mode(app, mode, player_name, settle=0.8):
    """Menu -> name entry -> game for one mode."""
    click_named(app, mode)
    check(app.screen_name == "name", "name screen opened for %s" % mode)
    app.handle_text(player_name)
    app.handle_key(pygame.K_RETURN)
    pump(app, settle)
    check(app.screen_name == "game", "%s game started" % mode)
    check(app.state.mode == mode, "state mode is %s" % mode)
    check(app.state.player_name == player_name[:12], "player name was applied")


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
            if made == count:
                break
        else:
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
    state.infected_tiles = set()
    state.refresh_largest_tile()
    app.pending_direction = None
    app.handle_key(pygame.K_LEFT)
    pump(app, 0.55)


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
        # 2. Classic: name entry, HUD, moves, robot, win prompt, game over
        # ------------------------------------------------------------------
        print("\n[2] Classic mode")
        click_named(app, "Classic")
        check(app.screen_name == "name", "Classic opens the name screen")
        app.handle_text("Ada")
        pump(app, 0.15, "02_name_entry.png")
        app.handle_key(pygame.K_RETURN)
        pump(app, 0.8, "03_classic_game.png")
        check(app.screen_name == "game", "Classic game started")
        check(app.state.player_name == "Ada", "typed name is used")

        # HUD sound toggle.
        before = app.sound.enabled
        click(app, app.draw()["hud"]["sound"], settle=0.05)
        check(app.sound.enabled != before, "HUD sound button toggles audio")
        click(app, app.draw()["hud"]["sound"], settle=0.05)
        check(app.sound.enabled == before, "HUD sound button toggles back")

        # HUD restart.
        made = make_moves(app, 4, "04_classic_after_moves.png")
        check(made >= 1, "Classic accepts arrow/WASD moves")
        moves_before = app.state.move_count
        click(app, app.draw()["hud"]["restart"], settle=0.8)
        check(app.state.move_count == 0, "HUD Restart resets the round")
        check(moves_before > 0, "restart happened after real moves")

        # Robot: two clicks, then the deferred third click.
        make_moves(app, 3)
        rects = app.draw()
        click(app, rects["robot"], settle=0.02)
        click(app, app.draw()["robot"], settle=0.02)
        check(app.state.robot_click_count == 2, "robot counted two clicks")
        click(app, app.draw()["robot"], settle=0.02)
        check(app.deferred_robot_click, "third robot click is deferred")
        app.draw()
        save_screenshot(app, "05_robot_thinking.png")
        pump(app, 0.85, "06_robot_solved.png")
        check(app.state.robot_click_count == 0, "robot click counter reset")
        check(app.state.ai_solver_active is False, "AI solver finished")

        # Win prompt -> Keep Playing.
        force_winning_move(app)
        check(app.state.win_prompt_pending, "2048 tile opens the win prompt")
        app.draw()
        save_screenshot(app, "07_win_overlay.png")
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

        # Game-over -> Leaderboard -> back -> Replay -> Menu.
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

        # HUD Menu -> main menu.
        click(app, app.draw()["hud"]["menu"], settle=0.8)
        check(app.screen_name == "menu", "HUD Menu returns to the main menu")

        # ------------------------------------------------------------------
        # 3. Survival: clock, temporary block, timeout
        # ------------------------------------------------------------------
        print("\n[3] Survival mode")
        start_mode(app, "Survival", "Survivor")
        pump(app, 0.2, "11_survival_game.png")

        # Bring the next scheduled block forward instead of waiting 10s.
        elapsed = app.game_time - app.state.survival_start_time
        app.state.survival_next_block_time = elapsed + 0.05
        pump(app, 0.3)
        check(app.state.survival_block_active, "Survival starts a temporary block")
        app.draw()
        save_screenshot(app, "12_survival_block.png")

        pump(app, 3.2)
        check(not app.state.survival_block_active, "Survival block expires")

        # Jump to the end of the 60-second round.
        app.state.survival_start_time = app.game_time - (SURVIVAL_TOTAL_TIME - 0.1)
        pump(app, 0.4)
        check(app.state.game_over, "Survival clock ends the round")
        check("Time is up" in app.state.game_over_reason, "time-up reason is set")
        app.draw()
        save_screenshot(app, "13_survival_game_over.png")
        click(app, app._rects["over"]["menu"], settle=0.8)
        check(app.screen_name == "menu", "Survival returns to the main menu")

        # ------------------------------------------------------------------
        # 4. Infection: spread after three moves, all-infected game over
        # ------------------------------------------------------------------
        print("\n[4] Infection mode")
        start_mode(app, "Infection", "Medic")
        pump(app, 0.2, "14_infection_game.png")
        check(len(app.state.infected_tiles) == 1, "Infection starts with one marker")

        made = 0
        attempts = 0
        index = 0
        while made < 3 and attempts < 60 and not app.state.game_over:
            before = app.state.move_count
            app.handle_key(DIRECTION_KEYS[index % len(DIRECTION_KEYS)])
            index += 1
            attempts += 1
            if app.state.move_count > before:
                made += 1
                if made == 3:
                    break
            pump(app, 0.32)

        check(made == 3, "Infection accepted three successful moves")
        check(app.state.infection_move_counter == 0, "spread counter reset after 3 moves")
        app.draw()
        save_screenshot(app, "15_infection_spread.png")

        # Infect every occupied tile and run the core status check.
        app.state.infected_tiles = set(app.state.occupied_cells())
        result = check_game_status(app.state)
        app._process_events(result, app.ui_time)
        pump(app, 0.3)
        check(app.state.game_over, "all-infected board ends the game")
        check("infected" in app.state.game_over_reason.lower(), "infection reason is set")
        app.draw()
        save_screenshot(app, "16_infection_game_over.png")
        click(app, app._rects["over"]["menu"], settle=0.8)
        check(app.screen_name == "menu", "Infection returns to the main menu")

        # ------------------------------------------------------------------
        # 5. Leaderboard (all tabs) and Achievements
        # ------------------------------------------------------------------
        print("\n[5] Leaderboard and achievements")
        click_named(app, "Leaderboard")
        check(app.screen_name == "leaderboard", "Leaderboard opens from the menu")
        app.draw()
        save_screenshot(app, "17_leaderboard_classic.png")

        rects = app.draw()
        click(app, rects["tabs"]["Survival"], settle=0.15)
        check(app.leaderboard_mode == "Survival", "Survival leaderboard tab works")
        app.draw()
        save_screenshot(app, "18_leaderboard_survival.png")

        rects = app.draw()
        click(app, rects["tabs"]["Infection"], settle=0.15)
        check(app.leaderboard_mode == "Infection", "Infection leaderboard tab works")
        app.draw()
        save_screenshot(app, "19_leaderboard_infection.png")

        click(app, app.draw()["back"], settle=0.8)
        check(app.screen_name == "menu", "leaderboard Back returns to the menu")

        click_named(app, "Achievements")
        check(app.screen_name == "achievements", "Achievements screen opens")
        app.draw()
        save_screenshot(app, "20_achievements.png")
        click(app, app.draw()["back"], settle=0.8)
        check(app.screen_name == "menu", "achievements Back returns to the menu")

        # ------------------------------------------------------------------
        # 6. Quit
        # ------------------------------------------------------------------
        print("\n[6] Quit")
        click_named(app, "Quit", settle=0.05)
        check(app.running is False, "Quit menu option stops the app")

        print("\nAll smoke checks passed.")
        print("Screenshots: %s" % SCREENSHOT_DIR)

        # Show that the smoke run really wrote leaderboard records.
        from core.leaderboard import load_local_leaderboards

        data = load_local_leaderboards(data_path)
        counts = {
            mode: len(records) for mode, records in data["leaderboards"].items()
        }
        print("Saved records:", counts)
        print("Lifetime stats:", data["stats"])

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
