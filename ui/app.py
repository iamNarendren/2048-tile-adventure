"""
The Pygame application shell for 2048 Tile Adventure (Pseudocode Modules 10-12).

This module connects the pure-Python core to the screens:

* it owns the Pygame window, the main loop, mouse/keyboard input and the
  screen stack (menu, name entry, game, leaderboards, achievements);
* it turns the events returned by the core into animations, sounds and toasts;
* it supplies ``now`` (game seconds) to the Survival clock, so the core never
  reads a clock itself.

Run the game with ``python main.py`` or ``python -m ui.app``.
"""

import random
from datetime import datetime
import asyncio
import pygame

from core import events
from core.board import move_tiles
from core.constants import (
    PLAYER_NAME_MAX_LENGTH,
    ROBOT_THINKING_TIME,
    SCREEN_FADE_DURATION,
)
from core.game_flow import (
    clean_player_name,
    initialize_game,
    resolve_win_choice,
    start_new_game,
)
from core.leaderboard import load_local_leaderboards, save_progress
from core.modes.survival import update_survival_clock
from core.robot import handle_robot_click
from ui import menu, renderer, robot_view, screens
from ui.animations import AnimationManager
from ui.sound import SoundManager


# ---------------------------------------------------------------------------
# Input tables
# ---------------------------------------------------------------------------
MOVE_KEYS = {
    pygame.K_LEFT: "LEFT",
    pygame.K_a: "LEFT",
    pygame.K_RIGHT: "RIGHT",
    pygame.K_d: "RIGHT",
    pygame.K_UP: "UP",
    pygame.K_w: "UP",
    pygame.K_DOWN: "DOWN",
    pygame.K_s: "DOWN",
}

MENU_KEYS = {
    pygame.K_1: "Classic",
    pygame.K_2: "Survival",
    pygame.K_3: "Infection",
    pygame.K_4: "Leaderboard",
    pygame.K_5: "Achievements",
    pygame.K_6: "Quit",
}


class GameApp:
    """Owns the window, the current screen and all front-end state."""

    def __init__(self, seed=None, data_path=None):
        pygame.init()

        self.screen = pygame.display.set_mode(
            (renderer.WINDOW_WIDTH, renderer.WINDOW_HEIGHT)
        )
        pygame.display.set_caption("2048 Tile Adventure")
        self.clock = pygame.time.Clock()

        self.sound = SoundManager()
        self.rng = random.Random(seed)
        self.data_path = data_path

        # --- Screen state -------------------------------------------------
        self.screen_name = "menu"
        self.running = True
        self.mouse_pos = (0, 0)
        self._rects = {}
        self._rects_screen = None

        # --- Player and game ----------------------------------------------
        self.player_name = "Player"
        self.selected_mode = "Classic"
        self.name_text = ""
        self.state = None

        # --- Time and animation -------------------------------------------
        self.ui_time = 0.0                 # smooth UI seconds, never paused
        self.game_time = 0.0               # game seconds, paused by overlays
        self.animations = AnimationManager()
        self.display_score = 0.0

        # --- Move/robot scheduling ----------------------------------------
        self.pending_direction = None
        self.deferred_robot_click = False
        self.robot_thinking_until = 0.0

        # --- Leaderboards --------------------------------------------------
        self.leaderboard_data = load_local_leaderboards(self.data_path)
        self.leaderboard_mode = "Classic"
        self.leaderboard_return = "menu"

        # --- Fade transition ----------------------------------------------
        self.fade_alpha = 0.0
        self.fade_state = None            # None | "out" | "in"
        self.fade_action = None

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------
    def _play(self, name):
        """Play a named sound effect if audio is available."""
        self.sound.play_game_sound(name)

    def _is_robot_thinking(self):
        """True while the third robot click waits for its bubble animation."""
        return self.deferred_robot_click and self.ui_time < self.robot_thinking_until

    def _start_text_input(self):
        """Ask the OS for text input while the name screen is open."""
        try:
            pygame.key.start_text_input()
        except (AttributeError, pygame.error):
            pass

    def _stop_text_input(self):
        """Stop text input when leaving the name screen."""
        try:
            pygame.key.stop_text_input()
        except (AttributeError, pygame.error):
            pass

    def _reset_round_ui(self):
        """Reset UI-only values after a new round starts."""
        self.game_time = 0.0
        self.animations.reset()
        self.display_score = 0.0
        self.pending_direction = None
        self.deferred_robot_click = False
        self.robot_thinking_until = 0.0
        self._stamp_state()

    def _stamp_state(self):
        """Give the state a wall-clock date without the core reading a clock."""
        if self.state is not None:
            self.state.save_timestamp = datetime.now().isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # Fade transitions
    # ------------------------------------------------------------------
    def _fade_to(self, action):
        """Fade to black, run ``action``, then fade back in."""
        if self.fade_state is not None:
            return
        self.fade_state = "out"
        self.fade_action = action

    def _update_fade(self, dt):
        """Advance the fade-out/fade-in state machine."""
        if self.fade_state == "out":
            self.fade_alpha += dt * (255.0 / SCREEN_FADE_DURATION)
            if self.fade_alpha >= 255.0:
                self.fade_alpha = 255.0
                action = self.fade_action
                self.fade_action = None
                if action is not None:
                    action()
                self.fade_state = "in"
        elif self.fade_state == "in":
            self.fade_alpha -= dt * (255.0 / SCREEN_FADE_DURATION)
            if self.fade_alpha <= 0.0:
                self.fade_alpha = 0.0
                self.fade_state = None

    # ------------------------------------------------------------------
    # Screen actions (run at the black point of a fade)
    # ------------------------------------------------------------------
    def _show_menu(self):
        """Return to the main menu, keeping mid-game progress safe."""
        if self.state is not None and not self.state.game_over:
            # Best scores and achievements survive even if the player quits.
            save_progress(self.state)
        self._stop_text_input()
        self.screen_name = "menu"
        self.pending_direction = None
        self.deferred_robot_click = False
        self.robot_thinking_until = 0.0

    def _show_name_entry(self, mode):
        """Open the player-name screen for a chosen mode."""
        self.selected_mode = mode
        self.name_text = ""
        self.screen_name = "name"
        self._start_text_input()

    def _start_selected_game(self):
        """Create a fresh state for the selected mode and start playing."""
        self.player_name = clean_player_name(self.name_text)
        self.state = initialize_game(
            self.player_name,
            self.selected_mode,
            now=0.0,
            rng=self.rng,
            data_path=self.data_path,
        )
        self._reset_round_ui()
        self._stop_text_input()
        self.screen_name = "game"

    def _restart_game(self):
        """Restart the current mode without losing session achievements."""
        if self.state is None:
            return
        start_new_game(self.state, now=0.0, rng=self.rng)
        self._reset_round_ui()
        self.screen_name = "game"

    def _open_leaderboard(self, return_to="menu"):
        """Load fresh save data and show the leaderboard screen."""
        self.leaderboard_data = load_local_leaderboards(self.data_path)
        self.leaderboard_mode = self.state.mode if self.state is not None else "Classic"
        self.leaderboard_return = return_to
        self.screen_name = "leaderboard"

    def _leave_leaderboard(self):
        """Go back to wherever the leaderboard was opened from."""
        if (
            self.leaderboard_return == "game_over"
            and self.state is not None
            and self.state.game_over
        ):
            self.screen_name = "game"
        else:
            self.screen_name = "menu"

    def _open_achievements(self):
        """Load fresh save data and show the achievements screen."""
        self.leaderboard_data = load_local_leaderboards(self.data_path)
        self.screen_name = "achievements"

    def _toggle_sound(self):
        """Toggle sound effects; play a click when turning them back on."""
        enabled = self.sound.toggle()
        if enabled:
            self._play("click")

    # ------------------------------------------------------------------
    # Core event -> UI reactions
    # ------------------------------------------------------------------
    def _process_events(self, result_events, now):
        """Turn the core's event list into animation, audio and toasts."""
        if not result_events:
            return

        kinds = [event.kind for event in result_events]

        if events.MOVED in kinds and self.state is not None:
            move_result = self.state.last_move
            if move_result is not None:
                self.animations.play_move_animation(move_result, now)
                if move_result.merges:
                    self.animations.play_merge_animation(move_result.merges, now)
                if self.state.last_spawn is not None:
                    self.animations.play_spawn_animation(self.state.last_spawn, now)

            if events.MERGED in kinds:
                self._play("merge")
            else:
                self._play("move")

        for event in result_events:
            kind = event.kind
            data = event.data

            if kind == events.ACHIEVEMENT_UNLOCKED:
                name = data.get("name", "Achievement")
                self.animations.add_toast("Achievement: %s" % name, renderer.SUCCESS, now)
                self._play("achievement")

            elif kind == events.MILESTONE_REACHED:
                score = data.get("score", 0)
                self.animations.add_toast(
                    "Milestone: %s points" % score, (246, 224, 94), now
                )
                self._play("milestone")

            elif kind == events.INFECTION_SPREAD:
                cells = list(data.get("cells") or ())
                if cells:
                    self.animations.play_infection_spread(cells, now)
                    self._play("spread")

            elif kind == events.BLOCK_STARTED:
                line = str(data.get("line", "line")).title()
                index = int(data.get("index", 0)) + 1
                self.animations.add_toast(
                    "%s %d frozen for 3s!" % (line, index),
                    renderer.WARNING,
                    now,
                )
                self._play("warning")

            elif kind == events.WON:
                self.pending_direction = None
                self.deferred_robot_click = False
                self.robot_thinking_until = 0.0
                self._play("win")

            elif kind == events.GAME_OVER:
                self.pending_direction = None
                self.deferred_robot_click = False
                self.robot_thinking_until = 0.0
                self._play("game_over")

        self.animations.update(now)

    # ------------------------------------------------------------------
    # Moves and robot clicks
    # ------------------------------------------------------------------
    def _can_accept_move(self):
        """True when a normal board move is currently allowed."""
        if self.state is None or self.screen_name != "game":
            return False
        if self.state.game_over or self.state.win_prompt_pending:
            return False
        return True

    def _play_move(self, direction):
        """Ask the core for one move and process the returned events."""
        self._stamp_state()
        result = move_tiles(
            self.state,
            direction,
            rng=self.rng,
            now=self.game_time,
        )
        self._process_events(result, self.ui_time)

    def _request_move(self, direction):
        """Queue a move while the previous animation is still playing."""
        if not self._can_accept_move():
            return
        if self._is_robot_thinking():
            return
        if self.animations.is_animating(self.ui_time):
            self.pending_direction = direction
            return
        self.pending_direction = None
        self._play_move(direction)

    def _click_robot(self):
        """Count robot clicks and defer the third one for the bubble."""
        if not self._can_accept_move() or self._is_robot_thinking():
            return
        if self.animations.is_animating(self.ui_time) or self.pending_direction:
            return

        if self.state.robot_click_count == 2:
            # Show "Thinking..." for a moment, then forward the real third
            # click to the core so handle_robot_click still sees three clicks.
            self.deferred_robot_click = True
            self.robot_thinking_until = self.ui_time + ROBOT_THINKING_TIME
            self._play("click")
            return

        self._stamp_state()
        result = handle_robot_click(self.state, now=self.game_time, rng=self.rng)
        self._play("click")
        self._process_events(result, self.ui_time)
    def _choose_win(self, keep_playing):
        """Apply the Keep Playing / End Game choice."""
        if self.state is None or not self.state.win_prompt_pending:
            return
        self._stamp_state()
        result = resolve_win_choice(
            self.state,
            keep_playing=keep_playing,
            now=self.game_time,
        )
        self._process_events(result, self.ui_time)

    # ------------------------------------------------------------------
    # Frame update
    # ------------------------------------------------------------------
    def update(self, dt):
        """Advance UI time, transitions, the Survival clock and queued input."""
        self.ui_time += dt
        self._update_fade(dt)
        self.animations.update(self.ui_time)

        if self.state is not None:
            difference = self.state.score - self.display_score
            if abs(difference) < 0.5:
                self.display_score = float(self.state.score)
            else:
                self.display_score += difference * min(1.0, dt * 9.0)

        if self.screen_name != "game" or self.state is None:
            return

        paused = self.state.game_over or self.state.win_prompt_pending

        if not paused:
            self.game_time += dt

            if self.state.mode == "Survival":
                clock_events = update_survival_clock(
                    self.state, self.game_time, rng=self.rng
                )
                self._process_events(clock_events, self.ui_time)

        # The Survival clock may have just ended the round.
        if self.state.game_over or self.state.win_prompt_pending:
            return

        # Fire the deferred third robot click once the bubble has been shown.
        if self.deferred_robot_click and self.ui_time >= self.robot_thinking_until:
            self.deferred_robot_click = False
            self.robot_thinking_until = 0.0
            result = handle_robot_click(
                self.state, now=self.game_time, rng=self.rng
            )
            self._process_events(result, self.ui_time)

        # Play a queued move once the previous animation has finished.
        if (
            self.pending_direction is not None
            and not self.animations.is_animating(self.ui_time)
            and not self._is_robot_thinking()
        ):
            direction = self.pending_direction
            self.pending_direction = None
            self._play_move(direction)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_game(self, surface, now):
        """Draw the board screen and return its clickable rectangles."""
        state = self.state
        renderer.draw_background(surface, state.mode)
        renderer.draw_title(surface, state)
        renderer.draw_score_and_best_score(surface, state, self.display_score)
        hud = renderer.draw_hud_buttons(surface, self.mouse_pos, self.sound.enabled)

        renderer.draw_board(surface, state, self.animations, now, self.game_time)
        renderer.draw_mode_information(surface, state, self.game_time, now)

        # Robot companion panel.
        accent = renderer.MODE_ACCENTS.get(state.mode, renderer.MODE_ACCENTS["Classic"])
        renderer.draw_panel(
            surface,
            renderer.ROBOT_PANEL_RECT,
            (255, 255, 255, 14),
            radius=16,
            border=(*accent, 70),
        )
        if not self._is_robot_thinking():
            # The speech bubble occupies the top of the panel while thinking.
            renderer.draw_text(
                surface,
                "ROBOT COMPANION",
                12,
                accent,
                topleft=(
                    renderer.ROBOT_PANEL_RECT.x + 16,
                    renderer.ROBOT_PANEL_RECT.y + 12,
                ),
                bold=True,
            )
        robot_color = renderer.ROBOT_COLORS.get(
            state.robot_color, renderer.ROBOT_COLORS["Blue"]
        )
        robot_view.draw_robot_companion(
            surface,
            renderer.ROBOT_RECT,
            robot_color,
            now,
            clicks=state.robot_click_count,
            thinking=self._is_robot_thinking(),
            ai_active=state.ai_solver_active,
        )
        renderer.draw_text(
            surface,
            "3 clicks = smart move",
            11,
            renderer.TEXT_MUTED,
            center=(
                renderer.ROBOT_PANEL_RECT.centerx,
                renderer.ROBOT_PANEL_RECT.bottom - 18,
            ),
        )

        renderer.draw_ai_panel(
            surface,
            state,
            state.robot_click_count,
            self._is_robot_thinking(),
            now,
        )
        renderer.draw_toasts(surface, self.animations, now)

        result = {"hud": hud, "robot": renderer.ROBOT_RECT}
        if state.win_prompt_pending:
            result["win"] = screens.draw_win_overlay(
                surface, state, self.mouse_pos, now
            )
        elif state.game_over:
            result["over"] = screens.display_game_over(
                surface, state, self.mouse_pos, now
            )
        return result

    def draw(self, now=None):
        """Draw the current screen and remember its clickable rectangles."""
        if now is None:
            now = self.ui_time

        surface = self.screen

        if self.screen_name == "menu":
            rects = menu.show_main_menu(
                surface,
                self.player_name,
                self.mouse_pos,
                self.sound.enabled,
                now,
            )
        elif self.screen_name == "name":
            rects = menu.enter_player_name(
                surface,
                self.name_text,
                self.mouse_pos,
                now,
                mode=self.selected_mode,
            )
        elif self.screen_name == "game" and self.state is not None:
            rects = self._draw_game(surface, now)
        elif self.screen_name == "leaderboard":
            rects = screens.display_leaderboards(
                surface,
                self.leaderboard_data,
                self.leaderboard_mode,
                self.mouse_pos,
                now,
                player_name=self.player_name,
            )
        elif self.screen_name == "achievements":
            rects = screens.display_achievements(
                surface,
                self.leaderboard_data,
                self.state,
                self.mouse_pos,
                now,
            )
        else:
            # Defensive fallback: never leave a black window on screen.
            rects = menu.show_main_menu(
                surface,
                self.player_name,
                self.mouse_pos,
                self.sound.enabled,
                now,
            )

        self._rects = rects
        self._rects_screen = self.screen_name
        renderer.draw_fade(surface, self.fade_alpha)
        return rects

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_text(self, text):
        """Append typed characters on the name screen (max 12 chars)."""
        if self.screen_name != "name" or self.fade_state is not None:
            return
        printable = "".join(character for character in text if character.isprintable())
        if not printable:
            return
        remaining = PLAYER_NAME_MAX_LENGTH - len(self.name_text)
        if remaining > 0:
            self.name_text += printable[:remaining]

    def handle_key(self, key):
        """Route one key press to the current screen."""
        if self.fade_state is not None:
            return

        if self.screen_name == "menu":
            if key in (pygame.K_q, pygame.K_ESCAPE):
                self.running = False
            elif key == pygame.K_f:
                self._toggle_sound()
            elif key in MENU_KEYS:
                self._activate_menu_item(MENU_KEYS[key])
            return

        if self.screen_name == "name":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._fade_to(self._start_selected_game)
            elif key == pygame.K_ESCAPE:
                self._fade_to(self._show_menu)
            elif key == pygame.K_BACKSPACE:
                self.name_text = self.name_text[:-1]
            return

        if self.screen_name == "game":
            if self.state is None:
                return

            if self.state.win_prompt_pending:
                if key in (pygame.K_k, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._choose_win(True)
                elif key == pygame.K_e:
                    self._choose_win(False)
                return

            if self.state.game_over:
                if key == pygame.K_r:
                    self._fade_to(self._restart_game)
                elif key in (pygame.K_m, pygame.K_ESCAPE):
                    self._fade_to(self._show_menu)
                elif key == pygame.K_l:
                    self._fade_to(lambda: self._open_leaderboard("game_over"))
                return

            if key in MOVE_KEYS:
                self._request_move(MOVE_KEYS[key])
            elif key == pygame.K_r:
                self._fade_to(self._restart_game)
            elif key in (pygame.K_m, pygame.K_ESCAPE):
                self._fade_to(self._show_menu)
            elif key == pygame.K_f:
                self._toggle_sound()
            return

        if self.screen_name == "leaderboard":
            if key == pygame.K_ESCAPE:
                self._fade_to(self._leave_leaderboard)
            elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
                self.leaderboard_mode = ("Classic", "Survival", "Infection")[key - pygame.K_1]
                self._play("click")
            elif key == pygame.K_LEFT:
                self._cycle_leaderboard(-1)
            elif key == pygame.K_RIGHT:
                self._cycle_leaderboard(1)
            return

        if self.screen_name == "achievements":
            if key in (pygame.K_ESCAPE, pygame.K_m):
                self._fade_to(self._show_menu)
            return

    def _cycle_leaderboard(self, step):
        """Move the leaderboard tab selection left or right."""
        modes = ("Classic", "Survival", "Infection")
        index = modes.index(self.leaderboard_mode)
        self.leaderboard_mode = modes[(index + step) % len(modes)]
        self._play("click")

    def _activate_menu_item(self, item):
        """Handle one of the six main-menu choices."""
        if item in ("Classic", "Survival", "Infection"):
            self._fade_to(lambda mode=item: self._show_name_entry(mode))
        elif item == "Leaderboard":
            self._fade_to(lambda: self._open_leaderboard("menu"))
        elif item == "Achievements":
            self._fade_to(self._open_achievements)
        elif item == "Quit":
            self.running = False

    def handle_click(self, position):
        """Route one left-click to the current screen's buttons."""
        if self.fade_state is not None:
            return

        if self._rects_screen != self.screen_name or not self._rects:
            self.draw(self.ui_time)
        rects = self._rects

        if self.screen_name == "menu":
            for key, _label, _color in menu.MENU_ITEMS:
                rect = rects.get(key)
                if rect is not None and rect.collidepoint(position):
                    self._play("click")
                    self._activate_menu_item(key)
                    return
            if rects.get("sound") and rects["sound"].collidepoint(position):
                self._toggle_sound()
            return

        if self.screen_name == "name":
            if rects.get("start") and rects["start"].collidepoint(position):
                self._play("click")
                self._fade_to(self._start_selected_game)
            elif rects.get("back") and rects["back"].collidepoint(position):
                self._play("click")
                self._fade_to(self._show_menu)
            return

        if self.screen_name == "game" and self.state is not None:
            if self.state.win_prompt_pending:
                win = rects.get("win", {})
                if win.get("keep") and win["keep"].collidepoint(position):
                    self._play("click")
                    self._choose_win(True)
                elif win.get("end") and win["end"].collidepoint(position):
                    self._play("click")
                    self._choose_win(False)
                return

            if self.state.game_over:
                over = rects.get("over", {})
                if over.get("replay") and over["replay"].collidepoint(position):
                    self._play("click")
                    self._fade_to(self._restart_game)
                elif over.get("menu") and over["menu"].collidepoint(position):
                    self._play("click")
                    self._fade_to(self._show_menu)
                elif over.get("leaderboard") and over["leaderboard"].collidepoint(position):
                    self._play("click")
                    self._fade_to(lambda: self._open_leaderboard("game_over"))
                return

            hud = rects.get("hud", {})
            if hud.get("restart") and hud["restart"].collidepoint(position):
                self._play("click")
                self._fade_to(self._restart_game)
                return
            if hud.get("menu") and hud["menu"].collidepoint(position):
                self._play("click")
                self._fade_to(self._show_menu)
                return
            if hud.get("sound") and hud["sound"].collidepoint(position):
                self._toggle_sound()
                return
            if rects.get("robot") and rects["robot"].collidepoint(position):
                self._click_robot()
            return

        if self.screen_name == "leaderboard":
            if rects.get("back") and rects["back"].collidepoint(position):
                self._play("click")
                self._fade_to(self._leave_leaderboard)
                return
            for mode, rect in rects.get("tabs", {}).items():
                if rect.collidepoint(position):
                    if mode != self.leaderboard_mode:
                        self.leaderboard_mode = mode
                        self._play("click")
                    return

        if self.screen_name == "achievements":
            if rects.get("back") and rects["back"].collidepoint(position):
                self._play("click")
                self._fade_to(self._show_menu)

    def handle_event(self, event):
        """Handle one Pygame event."""
        if event.type == pygame.QUIT:
            self.running = False

        elif event.type == pygame.KEYDOWN:
            self.handle_key(event.key)

        elif event.type == pygame.TEXTINPUT:
            self.handle_text(event.text)

        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.mouse_pos = event.pos
            self.handle_click(event.pos)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------
    async def run(self):
        """Run the Pygame loop until the player quits."""
        while self.running:
            # Cap dt so a dragged window cannot make tiles jump.
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self.mouse_pos = pygame.mouse.get_pos()

            self.update(dt)
            self.draw()
            for event in pygame.event.get():
                self.handle_event(event)
            pygame.display.flip()

            # Give control back to the browser every frame (needed for the web
            # version; does nothing noticeable on desktop).
            await asyncio.sleep(0)

    def shutdown(self):
        """Release Pygame resources (safe to call more than once)."""
        self._stop_text_input()
        pygame.quit()


async def main_game_loop():
    """Pseudocode Module 12 - create the app, run it and clean up."""
    app = GameApp()
    try:
        await app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
    return 0


if __name__ == "__main__":
    asyncio.run(main_game_loop())

