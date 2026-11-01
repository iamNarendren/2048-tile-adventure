"""
Animation state for the Pygame front-end (Pseudocode Module 10).

The core reports *what* happened (a MoveResult with tile movements, merges and
a SpawnResult).  This module stores *when* it happened so the renderer can
interpolate positions and scales.  It never changes game rules.
"""

import math
from dataclasses import dataclass

from core.constants import (
    MERGE_ANIMATION_DURATION,
    MOVE_ANIMATION_DURATION,
    SPAWN_ANIMATION_DURATION,
)


def clamp(value, low=0.0, high=1.0):
    """Keep a number inside a range."""
    return max(low, min(high, value))


def ease_out_cubic(t):
    """Fast start, gentle finish (nice for sliding tiles)."""
    t = clamp(t)
    return 1.0 - (1.0 - t) ** 3


def ease_out_back(t):
    """A small overshoot, used for the spawn "pop"."""
    t = clamp(t)
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def pop_scale(progress):
    """Scale a merged tile: 1.0 -> 1.16 -> 1.0."""
    return 1.0 + 0.16 * math.sin(math.pi * clamp(progress))


def spawn_scale(progress):
    """Scale a newly spawned tile from small to full size."""
    return 0.35 + 0.65 * ease_out_back(progress)


@dataclass
class Toast:
    """A short message that slides in from the right."""

    text: str
    color: tuple
    created: float
    duration: float = 2.6

    def age(self, now):
        return now - self.created

    def is_alive(self, now):
        return self.age(now) < self.duration


class AnimationManager:
    """Holds the current move animation plus achievement/milestone toasts."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Forget every animation (used when a new game starts)."""
        self.move_result = None
        self.moves = []
        self.merges = []
        self.spawn = None

        self.move_start = 0.0
        self.merge_start = 0.0
        self.spawn_start = 0.0

        self.spread_cells = []
        self.spread_start = -99.0

        self.toasts = []

    # ------------------------------------------------------------------
    # Pseudocode Module 10 animation starters
    # ------------------------------------------------------------------
    def play_move_animation(self, move_result, now):
        """Start the tile-sliding animation for a successful move."""
        self.move_result = move_result
        self.moves = list(move_result.moves)
        self.merges = []
        self.spawn = None
        self.move_start = now

    def play_merge_animation(self, merges, now):
        """Remember which cells should pop after the slide finishes."""
        self.merges = list(merges)
        self.merge_start = now

    def play_spawn_animation(self, spawn, now):
        """Start the scale-in animation for the newly spawned tile."""
        self.spawn = spawn
        self.spawn_start = now

    def play_infection_spread(self, cells, now):
        """Start the expanding green rings for newly infected cells."""
        self.spread_cells = list(cells)
        self.spread_start = now

    # ------------------------------------------------------------------
    # Progress helpers used by the renderer
    # ------------------------------------------------------------------
    def slide_progress(self, now):
        if self.move_result is None:
            return 1.0
        return clamp((now - self.move_start) / MOVE_ANIMATION_DURATION)

    def merge_progress(self, now):
        start = self.merge_start + MOVE_ANIMATION_DURATION
        return clamp((now - start) / MERGE_ANIMATION_DURATION)

    def spawn_progress(self, now):
        start = self.spawn_start + MOVE_ANIMATION_DURATION
        return clamp((now - start) / SPAWN_ANIMATION_DURATION)

    def is_animating(self, now):
        """True while tiles are still sliding, popping or spawning."""
        if self.move_result is None:
            return False

        duration = MOVE_ANIMATION_DURATION
        if self.merges:
            duration = max(duration, MOVE_ANIMATION_DURATION + MERGE_ANIMATION_DURATION)
        if self.spawn is not None:
            duration = max(duration, MOVE_ANIMATION_DURATION + SPAWN_ANIMATION_DURATION)
        return now < self.move_start + duration

    def spread_progress(self, now):
        return clamp((now - self.spread_start) / 0.5)

    def is_spreading(self, now):
        return 0.0 <= (now - self.spread_start) < 0.5

    # ------------------------------------------------------------------
    # Toasts
    # ------------------------------------------------------------------
    def add_toast(self, text, color, now):
        """Queue a short notification, keeping at most four on screen."""
        self.toasts.append(Toast(text=text, color=color, created=now))
        if len(self.toasts) > 4:
            self.toasts = self.toasts[-4:]

    def update(self, now):
        """Remove expired toasts (called once per frame)."""
        self.toasts = [toast for toast in self.toasts if toast.is_alive(now)]
