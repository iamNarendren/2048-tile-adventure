"""
Secondary screens and in-game overlays (Pseudocode Modules 6 and 12).

``display_leaderboards`` draws the leaderboard screen.  The win prompt and the
game-over screen are overlays drawn on top of the board, so the player can
still see the final position.

Like ``ui/menu.py``, these functions only draw and return clickable rectangles.
``ui/app.py`` owns the behaviour, which keeps every screen easy to test and
keeps the pure-Python core free of Pygame.
"""

import math

import pygame

from core.leaderboard import best_score_for_mode, get_leaderboard
from ui import renderer


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _dim(surface, alpha=175):
    """Darken the whole window behind an overlay."""
    shade = pygame.Surface((renderer.WINDOW_WIDTH, renderer.WINDOW_HEIGHT), pygame.SRCALPHA)
    shade.fill((5, 7, 14, alpha))
    surface.blit(shade, (0, 0))


def wrap_text(text, font, max_width):
    """Split ``text`` into lines that fit inside ``max_width`` pixels."""
    words = str(text).split()
    if not words:
        return [""]

    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = current + " " + word
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _short_date(value):
    """Turn an ISO timestamp into a compact YYYY-MM-DD display string."""
    text = str(value or "")
    if "T" in text:
        text = text.split("T", 1)[0]
    return text or "-"


# ---------------------------------------------------------------------------
# Leaderboards (Module 6)
# ---------------------------------------------------------------------------
def display_leaderboards(surface, data, mouse_pos, now, player_name=None):
    """Pseudocode Module 6 - draw the local leaderboard.

    Returns the Back button so the app can route clicks.  ``player_name`` is
    optional and only used to highlight the current player's rows.
    """
    mode = "Classic"
    renderer.draw_background(surface, mode)
    accent = renderer.MODE_ACCENTS["Classic"]

    renderer.draw_text(
        surface,
        "LEADERBOARD",
        42,
        (255, 215, 0),
        center=(renderer.WINDOW_WIDTH // 2, 72),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "Local records, best runs first",
        15,
        renderer.TEXT_MUTED,
        center=(renderer.WINDOW_WIDTH // 2, 110),
    )

    # --- Table panel -------------------------------------------------------
    panel = pygame.Rect(90, 160, 720, 600)
    renderer.draw_panel(
        surface,
        panel,
        (22, 26, 42, 220),
        radius=20,
        border=(*accent, 90),
    )

    best = best_score_for_mode(data, mode)
    renderer.draw_text(
        surface,
        "BEST",
        11,
        renderer.TEXT_MUTED,
        topleft=(panel.x + 24, panel.y + 18),
        bold=True,
    )
    renderer.draw_text(
        surface,
        best,
        24,
        accent,
        topleft=(panel.x + 24, panel.y + 32),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "%s RECORDS" % mode.upper(),
        13,
        accent,
        topleft=(panel.right - 220, panel.y + 28),
        bold=True,
    )

    header_y = panel.y + 76
    pygame.draw.line(
        surface,
        (255, 255, 255, 34),
        (panel.x + 22, header_y + 24),
        (panel.right - 22, header_y + 24),
        1,
    )
    columns = (
        ("#", panel.x + 28, 40),
        ("PLAYER", panel.x + 82, 300),
        ("SCORE", panel.x + 430, 140),
        ("DATE", panel.x + 574, 120),
    )
    for label, x, _width in columns:
        renderer.draw_text(
            surface,
            label,
            12,
            renderer.TEXT_MUTED,
            topleft=(x, header_y),
            bold=True,
        )

    records = get_leaderboard(data, mode)
    if not records:
        renderer.draw_text(
            surface,
            "No scores yet. Be the first!",
            20,
            renderer.TEXT_LIGHT,
            center=(panel.centerx, panel.centery + 20),
            bold=True,
        )
        renderer.draw_text(
            surface,
            "Play a round to fill this board.",
            14,
            renderer.TEXT_MUTED,
            center=(panel.centerx, panel.centery + 52),
        )
    else:
        row_y = header_y + 36
        row_height = 43
        for index, record in enumerate(records[:10]):
            y = row_y + index * row_height
            if index % 2 == 0:
                stripe = pygame.Rect(panel.x + 18, y - 6, panel.width - 36, row_height - 4)
                renderer._alpha_rect(surface, stripe, (255, 255, 255, 10), 8)

            # Highlight the current player's rows without hiding the rank.
            player = str(record.get("player_name", "Player"))[:16]
            is_me = bool(player_name) and player == player_name

            rank_color = (255, 215, 0) if index == 0 else renderer.TEXT_MUTED
            renderer.draw_text(
                surface,
                str(index + 1),
                15,
                rank_color,
                topleft=(panel.x + 28, y),
                bold=index == 0,
            )
            renderer.draw_text(
                surface,
                player,
                16,
                renderer.TEXT_LIGHT,
                topleft=(panel.x + 82, y - 1),
                bold=is_me,
            )
            renderer.draw_text(
                surface,
                int(record.get("score", 0)),
                17,
                accent,
                topleft=(panel.x + 430, y - 1),
                bold=True,
            )
            renderer.draw_text(
                surface,
                _short_date(record.get("date")),
                13,
                renderer.TEXT_MUTED,
                topleft=(panel.x + 574, y + 1),
            )

    # --- Navigation --------------------------------------------------------
    back_rect = pygame.Rect(90, 794, 150, 48)
    renderer.draw_button(
        surface,
        back_rect,
        "BACK",
        mouse_pos,
        (183, 148, 244),
        size=15,
    )
    renderer.draw_text(
        surface,
        "The top 10 scores are kept   |   ESC to go back",
        13,
        renderer.TEXT_MUTED,
        topleft=(270, 810),
    )

    return {"back": back_rect}


# ---------------------------------------------------------------------------
# Win overlay (Module 12)
# ---------------------------------------------------------------------------
def draw_win_overlay(surface, state, mouse_pos, now):
    """Draw the "You reached 2048" prompt with Keep Playing / End Game."""
    _dim(surface, 185)

    panel = pygame.Rect(210, 280, 480, 320)
    renderer.draw_panel(
        surface,
        panel,
        (26, 30, 46),
        radius=24,
        border=(255, 215, 0),
    )

    pulse = 0.5 + 0.5 * math.sin(now * 3.4)
    glow = pygame.Rect(panel.x + 80, panel.y + 22, panel.width - 160, 92)
    renderer._alpha_rect(surface, glow, (255, 215, 0, int(18 + pulse * 22)), 20)

    renderer.draw_text(
        surface,
        "2048!",
        66,
        (255, 215, 0),
        center=(panel.centerx, panel.y + 74),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "You reached the target tile!",
        18,
        renderer.TEXT_LIGHT,
        center=(panel.centerx, panel.y + 128),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "Keep going for a higher score, or end the adventure here.",
        13,
        renderer.TEXT_MUTED,
        center=(panel.centerx, panel.y + 158),
    )

    score_panel = pygame.Rect(panel.x + 90, panel.y + 178, panel.width - 180, 38)
    renderer.draw_panel(
        surface,
        score_panel,
        (255, 255, 255, 12),
        radius=10,
        border=(255, 255, 255, 26),
        shadow=False,
    )
    renderer.draw_text(
        surface,
        "Score %d   |   Moves %d" % (state.score, state.move_count),
        15,
        (246, 224, 94),
        center=score_panel.center,
        bold=True,
    )

    keep_rect = pygame.Rect(panel.x + 34, panel.bottom - 66, 196, 50)
    end_rect = pygame.Rect(panel.right - 230, panel.bottom - 66, 196, 50)
    renderer.draw_button(
        surface,
        keep_rect,
        "KEEP PLAYING",
        mouse_pos,
        (104, 211, 145),
        size=15,
    )
    renderer.draw_button(
        surface,
        end_rect,
        "END GAME",
        mouse_pos,
        (252, 129, 129),
        size=15,
    )

    renderer.draw_text(
        surface,
        "K keep playing   |   E end game",
        12,
        renderer.TEXT_MUTED,
        center=(panel.centerx, panel.bottom + 20),
    )

    return {"keep": keep_rect, "end": end_rect}


# ---------------------------------------------------------------------------
# Game over screen (Module 12)
# ---------------------------------------------------------------------------
def display_game_over(surface, state, mouse_pos, now):
    """Draw the final score with Replay / Main Menu / Leaderboard buttons."""
    _dim(surface, 195)

    panel = pygame.Rect(180, 230, 540, 450)
    renderer.draw_panel(
        surface,
        panel,
        (25, 28, 44),
        radius=24,
        border=(252, 129, 129),
    )

    renderer.draw_text(
        surface,
        "GAME OVER",
        52,
        (252, 129, 129),
        center=(panel.centerx, panel.y + 58),
        bold=True,
    )

    reason_font = renderer.get_font(15)
    reason_lines = wrap_text(state.game_over_reason or "The round is over.", reason_font, panel.width - 90)
    reason_y = panel.y + 100
    for line in reason_lines[:2]:
        renderer.draw_text(
            surface,
            line,
            15,
            renderer.TEXT_MUTED,
            center=(panel.centerx, reason_y),
        )
        reason_y += 22

    # Final score panel.
    score_box = pygame.Rect(panel.x + 60, panel.y + 156, panel.width - 120, 86)
    renderer.draw_panel(
        surface,
        score_box,
        (255, 255, 255, 12),
        radius=14,
        border=(255, 255, 255, 28),
        shadow=False,
    )
    renderer.draw_text(
        surface,
        "FINAL SCORE",
        11,
        renderer.TEXT_MUTED,
        center=(score_box.centerx, score_box.y + 18),
        bold=True,
    )
    renderer.draw_text(
        surface,
        state.score,
        38,
        (255, 215, 0),
        center=(score_box.centerx, score_box.y + 54),
        bold=True,
    )

    details = "Moves: %d      Best: %d" % (
        state.move_count,
        state.best_score,
    )
    renderer.draw_text(
        surface,
        details,
        14,
        renderer.TEXT_LIGHT,
        center=(panel.centerx, panel.y + 270),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "Your score was saved to the leaderboard.",
        12,
        renderer.TEXT_MUTED,
        center=(panel.centerx, panel.y + 294),
    )

    replay_rect = pygame.Rect(panel.x + 30, panel.bottom - 120, 150, 52)
    menu_rect = pygame.Rect(panel.x + 195, panel.bottom - 120, 150, 52)
    board_rect = pygame.Rect(panel.x + 360, panel.bottom - 120, 150, 52)

    renderer.draw_button(
        surface,
        replay_rect,
        "REPLAY",
        mouse_pos,
        (246, 224, 94),
        size=15,
    )
    renderer.draw_button(
        surface,
        menu_rect,
        "MAIN MENU",
        mouse_pos,
        (183, 148, 244),
        size=15,
    )
    renderer.draw_button(
        surface,
        board_rect,
        "LEADERBOARD",
        mouse_pos,
        (143, 211, 244),
        size=13,
    )

    renderer.draw_text(
        surface,
        "R replay   |   M menu   |   L leaderboard",
        12,
        renderer.TEXT_MUTED,
        center=(panel.centerx, panel.bottom + 20),
    )

    return {"replay": replay_rect, "menu": menu_rect, "leaderboard": board_rect}
