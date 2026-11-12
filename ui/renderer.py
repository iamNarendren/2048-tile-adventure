"""
Pygame drawing helpers (Pseudocode Module 10).

This module owns the 12-colour palette, fonts, the board, the HUD, the mode
panel and the hint panel.  The core only stores colour *names*; ``get_tile_color`` here
converts a name to an RGB tuple.
"""

import math

import pygame

from core.constants import (
    TARGET_TILE,
    get_tile_color as core_tile_color_name,
)
from ui.animations import clamp, ease_out_cubic, pop_scale, spawn_scale


# ---------------------------------------------------------------------------
# Window layout
# ---------------------------------------------------------------------------
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 900

BOARD_RECT = pygame.Rect(45, 185, 610, 610)
BOARD_PADDING = 14
CELL_GAP = 14
CELL_SIZE = 135

SCORE_RECT = pygame.Rect(45, 70, 165, 78)
BEST_RECT = pygame.Rect(222, 70, 165, 78)
MOVES_RECT = pygame.Rect(399, 70, 165, 78)
RESTART_RECT = pygame.Rect(580, 80, 92, 38)
MENU_RECT = pygame.Rect(682, 80, 92, 38)
SOUND_RECT = pygame.Rect(784, 80, 82, 38)

MODE_RECT = pygame.Rect(685, 185, 185, 140)
HINT_PANEL_RECT = pygame.Rect(685, 340, 185, 455)
HINT_BUTTON_RECT = pygame.Rect(705, 727, 145, 48)

# ---------------------------------------------------------------------------
# Palette - the 12 tile colours named in the pseudocode plus UI colours.
# ---------------------------------------------------------------------------
PALETTE = {
    "Empty Cell Color": (54, 60, 82),
    "Lavender": (201, 182, 245),
    "Sky Blue": (143, 211, 244),
    "Turquoise": (79, 209, 197),
    "Mint Green": (154, 230, 180),
    "Golden Yellow": (246, 224, 94),
    "Orange": (246, 173, 85),
    "Coral Pink": (252, 129, 129),
    "Violet": (183, 148, 244),
    "Electric Blue": (99, 179, 237),
    "Deep Purple": (128, 90, 213),
    "Glowing Gold": (255, 215, 0),
}

BACKGROUNDS = {
    "Classic": ((17, 19, 34), (44, 52, 90)),
    "Menu": ((20, 16, 38), (58, 34, 90)),
}

MODE_ACCENTS = {
    "Classic": (246, 224, 94),
    "Menu": (183, 148, 244),
}

TEXT_LIGHT = (240, 242, 252)
TEXT_MUTED = (170, 178, 200)
TEXT_DARK = (28, 30, 44)

_GRADIENT_CACHE = {}
_FONT_CACHE = {}


# ---------------------------------------------------------------------------
# Small colour and font helpers
# ---------------------------------------------------------------------------
def lighten(color, amount):
    """Return a lighter RGB colour."""
    return tuple(min(255, int(channel) + amount) for channel in color[:3])


def darken(color, amount):
    """Return a darker RGB colour."""
    return tuple(max(0, int(channel) - amount) for channel in color[:3])


def blend(color_a, color_b, t):
    """Linearly interpolate two RGB colours."""
    t = clamp(t)
    return tuple(
        int(color_a[index] + (color_b[index] - color_a[index]) * t)
        for index in range(3)
    )


def text_color_for(background):
    """Pick a readable text colour for a tile fill."""
    red, green, blue = background[:3]
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    return TEXT_DARK if luminance > 145 else (255, 255, 255)


def get_font(size, bold=False):
    """Return a cached system font, with a safe fallback."""
    key = (size, bold)
    if key not in _FONT_CACHE:
        try:
            font = pygame.font.SysFont("segoeui,arial,dejavusans", size, bold=bold)
        except Exception:
            font = pygame.font.Font(None, size)
        _FONT_CACHE[key] = font
    return _FONT_CACHE[key]


def draw_text(
    surface,
    text,
    size,
    color,
    center=None,
    topleft=None,
    midtop=None,
    bold=False,
    alpha=255,
):
    """Render one line of text and return its rect."""
    font = get_font(size, bold)
    rendered = font.render(str(text), True, color)
    if alpha < 255:
        rendered.set_alpha(alpha)

    if center is not None:
        rect = rendered.get_rect(center=center)
    elif midtop is not None:
        rect = rendered.get_rect(midtop=midtop)
    else:
        rect = rendered.get_rect(topleft=topleft or (0, 0))

    surface.blit(rendered, rect)
    return rect


def _fill_rounded(surface, rect, color, radius=16):
    """Draw a rounded rectangle, supporting RGBA colours."""
    if len(color) == 4:
        temp = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(temp, color, temp.get_rect(), border_radius=radius)
        surface.blit(temp, rect.topleft)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)


def draw_panel(surface, rect, fill, radius=16, border=None, shadow=True):
    """Draw a rounded panel with an optional border and drop shadow."""
    if shadow:
        _fill_rounded(
            surface,
            pygame.Rect(rect.x, rect.y + 5, rect.width, rect.height),
            (8, 10, 18, 110),
            radius,
        )
    _fill_rounded(surface, rect, fill, radius)
    if border is not None:
        pygame.draw.rect(surface, border, rect, 2, border_radius=radius)


def draw_button(surface, rect, label, mouse_pos, accent, size=18, enabled=True):
    """Draw a hover-aware button and return True when hovered."""
    hovered = enabled and rect.collidepoint(mouse_pos)

    if not enabled:
        fill = (88, 94, 112)
        text_color = (200, 204, 216)
    else:
        fill = lighten(accent, 24) if hovered else accent
        text_color = text_color_for(fill)

    draw_panel(
        surface,
        rect,
        fill,
        radius=12,
        border=lighten(fill, 40) if hovered else darken(fill, 20),
    )
    draw_text(surface, label, size, text_color, center=rect.center, bold=True)
    return hovered


# ---------------------------------------------------------------------------
# Background (Module 10 / section 4)
# ---------------------------------------------------------------------------
def _build_gradient(mode):
    """Create (and cache) the vertical gradient with soft accent glows."""
    top, bottom = BACKGROUNDS.get(mode, BACKGROUNDS["Classic"])
    accent = MODE_ACCENTS.get(mode, MODE_ACCENTS["Classic"])

    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    for y in range(WINDOW_HEIGHT):
        color = blend(top, bottom, y / max(1, WINDOW_HEIGHT - 1))
        pygame.draw.line(surface, color, (0, y), (WINDOW_WIDTH, y))

    glow = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*accent, 26), (140, 170), 260)
    pygame.draw.circle(glow, (*lighten(accent, 60), 16), (790, 720), 320)
    pygame.draw.circle(glow, (255, 255, 255, 8), (450, 450), 420)
    surface.blit(glow, (0, 0))
    return surface


def draw_background(surface, mode="Classic"):
    """Draw the themed gradient background for a mode."""
    if mode not in _GRADIENT_CACHE:
        _GRADIENT_CACHE[mode] = _build_gradient(mode)
    surface.blit(_GRADIENT_CACHE[mode], (0, 0))


# ---------------------------------------------------------------------------
# Tiles and board
# ---------------------------------------------------------------------------
def get_tile_color(tile_value):
    """Pseudocode Module 10 - convert a tile value to an RGB colour."""
    return PALETTE[core_tile_color_name(tile_value)]


def _cell_rect(row, col):
    """Return the pixel rectangle of one board cell."""
    x = BOARD_RECT.x + BOARD_PADDING + col * (CELL_SIZE + CELL_GAP)
    y = BOARD_RECT.y + BOARD_PADDING + row * (CELL_SIZE + CELL_GAP)
    return pygame.Rect(x, y, CELL_SIZE, CELL_SIZE)


def _tile_font_size(value):
    """Shrink the font for 3 and 4 digit numbers."""
    digits = len(str(value))
    if digits <= 2:
        return 54
    if digits == 3:
        return 46
    if digits == 4:
        return 38
    return 31


def _alpha_rect(surface, rect, color, radius=14):
    """Draw an RGBA rounded rectangle onto the main surface."""
    temp = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(temp, color, temp.get_rect(), border_radius=radius)
    surface.blit(temp, rect.topleft)


def draw_tile(surface, rect, value, now=0.0, scale=1.0):
    """Draw one tile: shadow, body, highlight, number and the 2048 glow."""
    if value <= 0:
        return

    scale = max(0.2, min(1.25, scale))
    width = max(8, int(rect.width * scale))
    height = max(8, int(rect.height * scale))
    tile_rect = pygame.Rect(0, 0, width, height)
    tile_rect.center = rect.center

    fill = get_tile_color(value)
    text_color = text_color_for(fill)

    # A soft glowing halo for 2048 and above.
    if value >= TARGET_TILE:
        pulse = 0.5 + 0.5 * math.sin(now * 3.2)
        glow_rect = tile_rect.inflate(int(16 + pulse * 14), int(16 + pulse * 14))
        _alpha_rect(surface, glow_rect, (255, 215, 0, int(45 + pulse * 45)), 22)
        pygame.draw.rect(
            surface,
            (255, 232, 120),
            glow_rect,
            2,
            border_radius=22,
        )

    # Drop shadow and body.
    _fill_rounded(
        surface,
        pygame.Rect(tile_rect.x, tile_rect.y + 4, width, height),
        (10, 12, 20, 120),
        14,
    )
    pygame.draw.rect(surface, fill, tile_rect, border_radius=14)

    # A lighter band at the top gives the tile a little depth.
    highlight = pygame.Rect(tile_rect.x + 4, tile_rect.y + 4, width - 8, max(4, height // 3))
    _alpha_rect(surface, highlight, (255, 255, 255, 26), 10)
    pygame.draw.rect(surface, darken(fill, 18), tile_rect, 2, border_radius=14)

    # Number, scaled together with the tile.
    font = get_font(_tile_font_size(value), bold=True)
    rendered = font.render(str(value), True, text_color)
    if abs(scale - 1.0) > 0.01:
        new_size = (
            max(1, int(rendered.get_width() * scale)),
            max(1, int(rendered.get_height() * scale)),
        )
        rendered = pygame.transform.smoothscale(rendered, new_size)
    surface.blit(rendered, rendered.get_rect(center=tile_rect.center))


def draw_empty_cells(surface):
    """Draw the recessed empty grid cells."""
    for row in range(4):
        for col in range(4):
            rect = _cell_rect(row, col)
            pygame.draw.rect(
                surface,
                (40, 45, 64),
                rect,
                border_radius=14,
            )
            pygame.draw.rect(
                surface,
                (48, 54, 76),
                rect.inflate(-6, -6),
                2,
                border_radius=12,
            )


def _draw_static_tiles(surface, state, now, animations=None):
    """Draw the final board, optionally scaling merged/spawned tiles."""
    merge_cells = set()
    pop = 0.0
    spawn_progress = 0.0
    spawn = None

    if animations is not None:
        merge_cells = {merge.cell for merge in animations.merges}
        pop = animations.merge_progress(now)
        spawn = animations.spawn
        spawn_progress = animations.spawn_progress(now)

    for row in range(4):
        for col in range(4):
            value = state.board[row][col]
            if value == 0:
                continue

            scale = 1.0
            if (row, col) in merge_cells:
                scale = pop_scale(pop)
            if spawn is not None and spawn.cell == (row, col):
                scale = spawn_scale(spawn_progress)

            draw_tile(
                surface,
                _cell_rect(row, col),
                value,
                now=now,
                scale=scale,
            )


def _draw_sliding_tiles(surface, animations, now):
    """Draw every source tile moving towards its destination."""
    progress = ease_out_cubic(animations.slide_progress(now))

    for move in animations.moves:
        from_rect = _cell_rect(*move.from_cell)
        to_rect = _cell_rect(*move.to_cell)
        center_x = from_rect.centerx + (to_rect.centerx - from_rect.centerx) * progress
        center_y = from_rect.centery + (to_rect.centery - from_rect.centery) * progress

        moving_rect = pygame.Rect(0, 0, CELL_SIZE, CELL_SIZE)
        moving_rect.center = (int(center_x), int(center_y))
        draw_tile(surface, moving_rect, move.value, now=now)


def draw_board(surface, state, animations, now):
    """Pseudocode Module 10 - draw the board panel, empty cells and tiles."""
    draw_panel(
        surface,
        BOARD_RECT,
        (27, 31, 47),
        radius=22,
        border=(72, 80, 108),
    )
    draw_empty_cells(surface)

    if animations.is_animating(now) and animations.move_result is not None:
        if animations.slide_progress(now) < 1.0:
            _draw_sliding_tiles(surface, animations, now)
        else:
            _draw_static_tiles(surface, state, now, animations)
    else:
        _draw_static_tiles(surface, state, now)


# ---------------------------------------------------------------------------
# HUD (Modules 6, 7 and 12)
# ---------------------------------------------------------------------------
def draw_title(surface, state):
    """Draw the game title and the player/mode subtitle."""
    draw_text(
        surface,
        "2048 TILE ADVENTURE",
        27,
        (255, 215, 0),
        topleft=(45, 12),
        bold=True,
    )
    accent = MODE_ACCENTS.get(state.mode, MODE_ACCENTS["Classic"])
    draw_text(
        surface,
        "Player: %s   |   Mode: %s" % (state.player_name, state.mode),
        15,
        accent,
        topleft=(46, 44),
        bold=True,
    )


def draw_score_and_best_score(surface, state, display_score):
    """Pseudocode Module 12 - draw score, best score and move count."""
    panels = (
        (SCORE_RECT, "SCORE", int(round(display_score)), (246, 224, 94)),
        (BEST_RECT, "BEST", state.best_score, (143, 211, 244)),
        (MOVES_RECT, "MOVES", state.move_count, (183, 148, 244)),
    )

    for rect, label, value, accent in panels:
        draw_panel(
            surface,
            rect,
            (255, 255, 255, 16),
            radius=14,
            border=(255, 255, 255, 30),
        )
        draw_text(surface, label, 13, TEXT_MUTED, topleft=(rect.x + 16, rect.y + 10), bold=True)
        draw_text(surface, value, 28, accent, topleft=(rect.x + 16, rect.y + 30), bold=True)


def draw_hud_buttons(surface, mouse_pos, sound_on):
    """Draw Restart / Menu / Sound buttons and return their rects."""
    draw_button(surface, RESTART_RECT, "RESTART", mouse_pos, (143, 211, 244), size=13)
    draw_button(surface, MENU_RECT, "MENU", mouse_pos, (183, 148, 244), size=13)
    sound_color = (154, 230, 180) if sound_on else (252, 129, 129)
    draw_button(
        surface,
        SOUND_RECT,
        "SFX ON" if sound_on else "SFX OFF",
        mouse_pos,
        sound_color,
        size=13,
    )
    return {"restart": RESTART_RECT, "menu": MENU_RECT, "sound": SOUND_RECT}


def draw_mode_information(surface, state):
    """Pseudocode Module 12 - draw the mode panel: target and largest tile."""
    accent = MODE_ACCENTS.get(state.mode, MODE_ACCENTS["Classic"])
    draw_panel(
        surface,
        MODE_RECT,
        (255, 255, 255, 14),
        radius=16,
        border=(*accent, 90),
    )
    pygame.draw.rect(
        surface,
        accent,
        pygame.Rect(MODE_RECT.x + 18, MODE_RECT.y + 14, 42, 3),
        border_radius=2,
    )
    draw_text(
        surface,
        state.mode.upper(),
        15,
        accent,
        topleft=(MODE_RECT.x + 18, MODE_RECT.y + 24),
        bold=True,
    )

    draw_text(
        surface,
        "TARGET",
        11,
        TEXT_MUTED,
        topleft=(MODE_RECT.x + 18, MODE_RECT.y + 52),
        bold=True,
    )
    draw_text(
        surface,
        str(TARGET_TILE),
        34,
        (255, 215, 0),
        topleft=(MODE_RECT.x + 18, MODE_RECT.y + 66),
        bold=True,
    )
    draw_text(
        surface,
        "Largest tile: %d" % state.largest_tile,
        12,
        TEXT_MUTED,
        topleft=(MODE_RECT.x + 18, MODE_RECT.y + 112),
    )


def _draw_arrow(surface, center, direction, size, color):
    """Draw a solid arrow pointing LEFT, RIGHT, UP or DOWN.

    The arrow is defined once pointing right, as seven (x, y) points around
    the origin.  Each point is then rotated in steps of 90 degrees with the
    direction's unit vector (dx, dy) and moved to ``center``.
    """
    shaft = size * 0.26          # half thickness of the shaft
    neck = size * 0.10           # x position where the head begins
    wing = size * 0.68           # half width of the arrow head
    points = (
        (-size, -shaft),
        (neck, -shaft),
        (neck, -wing),
        (size, 0),
        (neck, wing),
        (neck, shaft),
        (-size, shaft),
    )
    dx, dy = {
        "RIGHT": (1, 0),
        "LEFT": (-1, 0),
        "UP": (0, -1),
        "DOWN": (0, 1),
    }[direction]

    rotated = [
        (int(center[0] + x * dx - y * dy), int(center[1] + x * dy + y * dx))
        for x, y in points
    ]
    pygame.draw.polygon(surface, color, rotated)


def draw_hint_panel(surface, state, hint_direction, mouse_pos, now):
    """Draw the hint panel and return the HINT button rectangle.

    ``hint_direction`` is "LEFT", "RIGHT", "UP", "DOWN" or None.  With None
    the panel explains the button; otherwise it shows the suggested move as a
    big arrow that gently pulses.
    """
    accent = MODE_ACCENTS.get(state.mode, MODE_ACCENTS["Classic"])
    panel = HINT_PANEL_RECT
    draw_panel(
        surface,
        panel,
        (255, 255, 255, 14),
        radius=16,
        border=(*accent, 70),
    )
    draw_text(
        surface,
        "HINT",
        13,
        accent,
        topleft=(panel.x + 16, panel.y + 14),
        bold=True,
    )

    # Round badge that holds either the arrow or a question mark.
    badge_center = (panel.centerx, panel.y + 140)
    pygame.draw.circle(surface, (40, 45, 64), badge_center, 70)
    pygame.draw.circle(surface, (72, 80, 108), badge_center, 70, 2)

    if hint_direction is None:
        draw_text(surface, "?", 72, TEXT_MUTED, center=badge_center, bold=True)
        draw_text(
            surface,
            "Need help?",
            16,
            TEXT_LIGHT,
            center=(panel.centerx, panel.y + 246),
            bold=True,
        )
        draw_text(
            surface,
            "Press HINT to see",
            12,
            TEXT_MUTED,
            center=(panel.centerx, panel.y + 274),
        )
        draw_text(
            surface,
            "the best next move.",
            12,
            TEXT_MUTED,
            center=(panel.centerx, panel.y + 292),
        )
    else:
        pulse = 0.5 + 0.5 * math.sin(now * 5.0)
        _draw_arrow(surface, badge_center, hint_direction, 40 + pulse * 5, accent)
        draw_text(
            surface,
            "BEST MOVE",
            11,
            TEXT_MUTED,
            center=(panel.centerx, panel.y + 240),
            bold=True,
        )
        draw_text(
            surface,
            hint_direction,
            28,
            TEXT_LIGHT,
            center=(panel.centerx, panel.y + 266),
            bold=True,
        )
        draw_text(
            surface,
            "Chosen by the AI solver",
            11,
            TEXT_MUTED,
            center=(panel.centerx, panel.y + 296),
        )

    draw_text(
        surface,
        "or press H",
        11,
        TEXT_MUTED,
        center=(panel.centerx, HINT_BUTTON_RECT.y - 16),
    )
    draw_button(surface, HINT_BUTTON_RECT, "HINT", mouse_pos, accent, size=17)
    return HINT_BUTTON_RECT


# ---------------------------------------------------------------------------
# Notifications and fade
# ---------------------------------------------------------------------------
def draw_toasts(surface, animations, now):
    """Draw milestone notifications sliding in from the right."""
    for index, toast in enumerate(animations.toasts):
        age = toast.age(now)
        slide_in = min(1.0, age / 0.25)
        offset = int((1.0 - ease_out_cubic(slide_in)) * 340)

        width, height = 300, 54
        x = WINDOW_WIDTH - width - 20 + offset
        y = 165 + index * 62

        alpha = 255
        if age > toast.duration - 0.4:
            alpha = max(0, int(255 * (toast.duration - age) / 0.4))

        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (26, 30, 46, int(alpha * 0.92)), panel.get_rect(), border_radius=12)
        pygame.draw.rect(panel, (*toast.color, alpha), pygame.Rect(0, 0, 6, height), border_radius=3)
        pygame.draw.rect(
            panel,
            (*lighten(toast.color, 20), alpha),
            panel.get_rect(),
            2,
            border_radius=12,
        )

        font = get_font(14, bold=True)
        text = toast.text
        if len(text) > 34:
            text = text[:31] + "..."
        rendered = font.render(text, True, (240, 242, 252))
        rendered.set_alpha(alpha)
        panel.blit(rendered, (18, (height - rendered.get_height()) // 2))

        surface.blit(panel, (x, y))


def draw_fade(surface, alpha):
    """Draw a black overlay for screen transitions (0-255)."""
    if alpha <= 0:
        return
    overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, int(max(0, min(255, alpha)))))
    surface.blit(overlay, (0, 0))
