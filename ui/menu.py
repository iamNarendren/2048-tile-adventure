"""
Main menu and player-name screens (Pseudocode Modules 1 and 2).

These functions only draw the screens and return their clickable rectangles;
``ui/app.py`` owns the actual button behaviour and screen switching.
"""

import pygame

from ui import renderer, robot_view


MENU_ITEMS = (
    ("Classic", "Classic", (246, 224, 94)),
    ("Survival", "Survival", (79, 209, 197)),
    ("Infection", "Infection", (154, 230, 180)),
    ("Leaderboard", "Leaderboard", (143, 211, 244)),
    ("Achievements", "Achievements", (183, 148, 244)),
    ("Quit", "Quit", (252, 129, 129)),
)


def _menu_button_rects():
    """Return the six menu button rectangles."""
    rects = {}
    width, height, gap = 340, 58, 14
    x = (renderer.WINDOW_WIDTH - width) // 2
    y = 300
    for key, _label, _color in MENU_ITEMS:
        rects[key] = pygame.Rect(x, y, width, height)
        y += height + gap
    return rects


def show_main_menu(surface, player_name, mouse_pos, sound_on, now):
    """Pseudocode Module 2 - draw the main menu and return its buttons."""
    renderer.draw_background(surface, "Menu")

    # Title with a soft drop shadow.
    renderer.draw_text(
        surface,
        "2048",
        110,
        (10, 10, 20),
        center=(renderer.WINDOW_WIDTH // 2, 128),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "2048",
        110,
        (255, 215, 0),
        center=(renderer.WINDOW_WIDTH // 2, 122),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "TILE ADVENTURE",
        34,
        (231, 220, 255),
        center=(renderer.WINDOW_WIDTH // 2, 208),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "Slide. Merge. Survive.",
        17,
        renderer.TEXT_MUTED,
        center=(renderer.WINDOW_WIDTH // 2, 244),
    )

    rects = _menu_button_rects()
    for key, label, color in MENU_ITEMS:
        renderer.draw_button(
            surface,
            rects[key],
            label,
            mouse_pos,
            color,
            size=22,
        )

    # Mascot and speech bubble on the right.
    bubble = pygame.Rect(684, 258, 176, 52)
    renderer.draw_panel(
        surface,
        bubble,
        (244, 247, 255),
        radius=14,
        border=(183, 148, 244),
    )
    tail = [
        (bubble.centerx - 9, bubble.bottom - 1),
        (bubble.centerx + 9, bubble.bottom - 1),
        (bubble.centerx, bubble.bottom + 12),
    ]
    pygame.draw.polygon(surface, (244, 247, 255), tail)
    renderer.draw_text(
        surface,
        "Pick a mode!",
        15,
        (40, 38, 58),
        center=bubble.center,
        bold=True,
    )
    robot_view.draw_robot_companion(
        surface,
        pygame.Rect(700, 350, 150, 168),
        (183, 148, 244),
        now,
        clicks=0,
    )

    # Footer.
    renderer.draw_text(
        surface,
        "Player: %s" % player_name,
        16,
        (231, 220, 255),
        topleft=(45, 842),
        bold=True,
    )
    renderer.draw_text(
        surface,
        "Arrows / WASD to move   R restart   M menu   F sound",
        13,
        renderer.TEXT_MUTED,
        topleft=(45, 870),
    )

    sound_rect = pygame.Rect(742, 828, 118, 40)
    sound_color = (154, 230, 180) if sound_on else (252, 129, 129)
    renderer.draw_button(
        surface,
        sound_rect,
        "SFX ON" if sound_on else "SFX OFF",
        mouse_pos,
        sound_color,
        size=14,
    )

    result = dict(rects)
    result["sound"] = sound_rect
    return result


def enter_player_name(surface, text, mouse_pos, now, mode=None):
    """Pseudocode Module 1 - draw the player-name text input screen.

    Returns the input box, the Start button and a Back button.  The app
    enforces the 12-character limit and calls ``core.game_flow.clean_player_name``
    when the player presses Enter.
    """
    renderer.draw_background(surface, "Menu")

    renderer.draw_text(
        surface,
        "2048 TILE ADVENTURE",
        44,
        (255, 215, 0),
        center=(renderer.WINDOW_WIDTH // 2, 120),
        bold=True,
    )

    back_rect = pygame.Rect(45, 40, 120, 44)
    renderer.draw_button(
        surface,
        back_rect,
        "BACK",
        mouse_pos,
        (183, 148, 244),
        size=14,
    )
    renderer.draw_text(
        surface,
        "Enter your player name:",
        22,
        renderer.TEXT_LIGHT,
        center=(renderer.WINDOW_WIDTH // 2, 320),
        bold=True,
    )

    if mode:
        accent = renderer.MODE_ACCENTS.get(mode, renderer.MODE_ACCENTS["Classic"])
        renderer.draw_text(
            surface,
            "MODE: %s" % mode.upper(),
            14,
            accent,
            center=(renderer.WINDOW_WIDTH // 2, 270),
            bold=True,
        )

    panel = pygame.Rect(190, 370, 520, 290)
    renderer.draw_panel(
        surface,
        panel,
        (255, 255, 255, 14),
        radius=20,
        border=(183, 148, 244, 120),
    )

    input_rect = pygame.Rect(240, 410, 420, 72)
    renderer.draw_panel(
        surface,
        input_rect,
        (22, 26, 42),
        radius=14,
        border=(183, 148, 244),
    )

    font = renderer.get_font(32, bold=True)
    shown_text = text if text else "Player"
    text_color = renderer.TEXT_LIGHT if text else renderer.TEXT_MUTED
    rendered = font.render(shown_text, True, text_color)
    text_pos = (input_rect.x + 20, input_rect.centery - rendered.get_height() // 2)
    surface.blit(rendered, text_pos)

    # Blinking caret after the real text (not after the placeholder).
    if text and int(now * 2) % 2 == 0:
        caret_x = text_pos[0] + font.size(text)[0] + 3
        pygame.draw.line(
            surface,
            (255, 215, 0),
            (caret_x, input_rect.y + 16),
            (caret_x, input_rect.bottom - 16),
            2,
        )

    renderer.draw_text(
        surface,
        "Max 12 characters. Empty names become 'Player'.",
        13,
        renderer.TEXT_MUTED,
        center=(panel.centerx, input_rect.bottom + 26),
    )

    start_rect = pygame.Rect(330, 540, 240, 58)
    renderer.draw_button(
        surface,
        start_rect,
        "START ADVENTURE",
        mouse_pos,
        (246, 224, 94),
        size=17,
    )

    renderer.draw_text(
        surface,
        "Press ENTER to begin   |   ESC to go back",
        14,
        (231, 220, 255),
        center=(panel.centerx, panel.bottom + 28),
        bold=True,
    )

    return {"input": input_rect, "start": start_rect, "back": back_rect}
