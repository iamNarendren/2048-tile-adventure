"""
The robot companion drawing (Pseudocode Module 7, section 4).

Everything is made from Pygame shapes: no image files are required.  The
robot bobs, blinks, shows a thinking bubble and displays the three-click
progress as dots.
"""

import math

import pygame

from ui import renderer


def _draw_bubble(surface, rect, color, now):
    """Draw the 'Thinking...' speech bubble above the robot."""
    bubble = pygame.Rect(rect.x - 6, rect.y - 64, rect.width + 12, 46)
    renderer.draw_panel(
        surface,
        bubble,
        (244, 247, 255),
        radius=13,
        border=renderer.lighten(color, 30),
    )

    # Tail pointing down at the robot.
    tail = [
        (bubble.centerx - 9, bubble.bottom - 1),
        (bubble.centerx + 9, bubble.bottom - 1),
        (bubble.centerx, bubble.bottom + 12),
    ]
    pygame.draw.polygon(surface, (244, 247, 255), tail)

    dots = "." * (1 + int(now * 4) % 3)
    renderer.draw_text(
        surface,
        "Thinking" + dots,
        13,
        (34, 38, 52),
        center=(bubble.centerx, bubble.centery),
        bold=True,
    )


def draw_robot_companion(
    surface,
    rect,
    color,
    now,
    clicks=0,
    thinking=False,
    ai_active=False,
):
    """Draw the robot at ``rect`` using a tier colour (RGB tuple)."""
    bob = math.sin(now * 2.2) * 4.0
    body_rect = rect.move(0, int(bob))

    # Soft glow behind the robot.
    glow = pygame.Surface((rect.width + 60, rect.height + 60), pygame.SRCALPHA)
    pygame.draw.ellipse(
        glow,
        (*color, 36 if not ai_active else 60),
        glow.get_rect(),
    )
    surface.blit(glow, (rect.x - 30, body_rect.y - 24))

    # Ground shadow (does not bob).
    pygame.draw.ellipse(
        surface,
        (10, 12, 20),
        pygame.Rect(rect.x + 22, rect.bottom - 6, rect.width - 44, 18),
    )

    center_x = body_rect.centerx

    # Antenna.
    antenna_top = body_rect.y + 18
    pygame.draw.line(
        surface,
        renderer.darken(color, 40),
        (center_x, body_rect.y + 34),
        (center_x, antenna_top - 14),
        3,
    )
    pulse = 0.5 + 0.5 * math.sin(now * 4.0)
    pygame.draw.circle(surface, renderer.lighten(color, 50), (center_x, antenna_top - 16), 8)
    pygame.draw.circle(surface, (255, 255, 255), (center_x, antenna_top - 16), int(2 + pulse * 3))

    # Arms.
    arm_width, arm_height = 16, 58
    left_arm = pygame.Rect(body_rect.x - 8, body_rect.y + 62, arm_width, arm_height)
    right_arm = pygame.Rect(body_rect.right - 8, body_rect.y + 62, arm_width, arm_height)
    for arm in (left_arm, right_arm):
        pygame.draw.rect(surface, renderer.darken(color, 25), arm, border_radius=8)
        pygame.draw.rect(surface, renderer.lighten(color, 15), arm, 2, border_radius=8)

    # Body.
    body = pygame.Rect(body_rect.x + 12, body_rect.y + 30, body_rect.width - 24, 118)
    renderer.draw_panel(
        surface,
        body,
        color,
        radius=26,
        border=renderer.lighten(color, 45),
    )

    # Face screen.
    face = pygame.Rect(body.x + 16, body.y + 18, body.width - 32, 58)
    pygame.draw.rect(surface, (22, 26, 38), face, border_radius=16)
    pygame.draw.rect(surface, renderer.lighten(color, 60), face, 2, border_radius=16)

    # Blink for a fraction of a second every few seconds.
    blink_phase = (now + 1.1) % 3.8
    blinking = blink_phase < 0.13
    eye_y = face.centery - 6
    eye_offset = 20

    if blinking:
        for direction in (-1, 1):
            pygame.draw.line(
                surface,
                (140, 240, 230),
                (face.centerx + direction * eye_offset - 8, eye_y),
                (face.centerx + direction * eye_offset + 8, eye_y),
                3,
            )
    else:
        for direction in (-1, 1):
            eye_center = (face.centerx + direction * eye_offset, eye_y)
            pygame.draw.circle(surface, (170, 250, 240), eye_center, 9)
            pygame.draw.circle(surface, (20, 30, 40), eye_center, 4)

    # Smile.
    mouth = pygame.Rect(face.centerx - 16, face.centery + 6, 32, 18)
    pygame.draw.arc(surface, (120, 235, 210), mouth, math.pi, 2 * math.pi, 3)

    # Chest core.
    core_center = (body.centerx, body.bottom - 26)
    pygame.draw.circle(surface, renderer.darken(color, 45), core_center, 13)
    pygame.draw.circle(surface, renderer.lighten(color, 70), core_center, 8)
    pygame.draw.circle(
        surface,
        (255, 255, 255),
        core_center,
        int(3 + pulse * 2),
    )

    # Wheels.
    for offset in (-32, 32):
        wheel = (body.centerx + offset, body.bottom + 8)
        pygame.draw.circle(surface, (20, 23, 34), wheel, 14)
        pygame.draw.circle(surface, (70, 78, 100), wheel, 8)
        pygame.draw.circle(surface, renderer.lighten(color, 20), wheel, 3)

    # Three-click progress dots.
    dot_y = rect.bottom + 18
    for index in range(3):
        dot_x = rect.centerx + (index - 1) * 22
        pygame.draw.circle(surface, (60, 68, 88), (dot_x, dot_y), 6)
        if index < min(3, clicks):
            pygame.draw.circle(surface, renderer.lighten(color, 20), (dot_x, dot_y), 6)
            pygame.draw.circle(surface, (255, 255, 255), (dot_x, dot_y), 2)

    if thinking:
        _draw_bubble(surface, body_rect, color, now)
