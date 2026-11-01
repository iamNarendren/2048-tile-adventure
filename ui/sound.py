"""
Sound effects for 2048 Tile Adventure (Pseudocode Module 10).

No sound files are downloaded.  On first run the game synthesises small WAV
files with the standard library's ``wave``, ``struct`` and ``math`` modules.
If audio cannot be initialised (for example on a machine without a sound
device) the game keeps running silently.
"""

import math
import os
import sys
import struct


import pygame

# Project root is one level above ui/.
if getattr(sys, "frozen", False):
    PROJECT_ROOT = os.path.dirname(sys.executable)  # running as .exe: use the .exe's folder
else:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOUND_DIR = os.path.join(PROJECT_ROOT, "assets", "sounds")

SAMPLE_RATE = 22050

# Each recipe is a list of (frequency_hz, duration_seconds).  A frequency of
# 0 produces a short silence, which is useful between notes.
SOUND_RECIPES = {
    "move": [(330.0, 0.055)],
    "merge": [(440.0, 0.07), (660.0, 0.10)],
    "win": [(523.25, 0.12), (659.25, 0.12), (783.99, 0.12), (1046.50, 0.24)],
    "game_over": [(392.00, 0.16), (329.63, 0.16), (261.63, 0.32)],
    "milestone": [(880.00, 0.10), (1174.66, 0.20)],
    "achievement": [(783.99, 0.09), (987.77, 0.09), (1174.66, 0.18)],
    "click": [(600.0, 0.04)],
    "warning": [(880.0, 0.08), (659.25, 0.08), (880.0, 0.08)],
    "spread": [(196.0, 0.10), (146.83, 0.20)],
}


def _synthesize(notes, volume=0.32):
    """Turn a note recipe into 16-bit mono PCM bytes."""
    frames = bytearray()

    for frequency, duration in notes:
        sample_count = max(1, int(SAMPLE_RATE * duration))
        for index in range(sample_count):
            time = index / SAMPLE_RATE
            # Simple attack/release envelope so notes do not click.
            attack = min(1.0, index / max(1, int(SAMPLE_RATE * 0.008)))
            release = min(1.0, (sample_count - index) / max(1, int(SAMPLE_RATE * 0.05)))
            envelope = attack * release

            if frequency <= 0:
                value = 0.0
            else:
                # A little second harmonic makes the tone warmer.
                wave_value = math.sin(2 * math.pi * frequency * time)
                wave_value += 0.22 * math.sin(4 * math.pi * frequency * time)
                value = wave_value * envelope * volume

            value = max(-1.0, min(1.0, value))
            frames.extend(struct.pack("<h", int(value * 32767)))

        # Tiny gap between notes.
        frames.extend(struct.pack("<h", 0) * int(SAMPLE_RATE * 0.01))

    return bytes(frames)


def _write_wav(path, pcm_bytes):
    """Write PCM bytes as a mono 16-bit WAV file."""
    # "wave" is imported only here, because only the desktop version ever
    # creates sound files. The web version ships them ready-made.
    wave = __import__("wave")
    with wave.open(path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(pcm_bytes)


def ensure_sound_files(folder=SOUND_DIR):
    """Generate any missing WAV files and return {name: path}."""
    os.makedirs(folder, exist_ok=True)
    paths = {}

    for name, notes in SOUND_RECIPES.items():
        path = os.path.join(folder, name + ".wav")
        if not os.path.exists(path) or os.path.getsize(path) < 44:
            _write_wav(path, _synthesize(notes))
        paths[name] = path

    return paths


class SoundManager:
    """Load, play and toggle the synthesised sound effects."""

    def __init__(self, folder=SOUND_DIR):
        self.folder = folder
        self.enabled = True
        self.available = False
        self.sounds = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.available = True
        except pygame.error:
            # No audio device: the game must still work.
            self.available = False
            return

        try:
            paths = ensure_sound_files(folder)
            for name, path in paths.items():
                sound = pygame.mixer.Sound(path)
                sound.set_volume(0.45)
                self.sounds[name] = sound
        except (pygame.error, OSError):
            self.available = False
            self.sounds = {}

    def play_game_sound(self, sound_type):
        """Pseudocode Module 10 - play a named effect if sound is enabled."""
        if not self.enabled or not self.available:
            return
        sound = self.sounds.get(sound_type)
        if sound is None:
            return
        try:
            sound.play()
        except pygame.error:
            pass

    def toggle(self):
        """Turn sound on/off and return the new state."""
        self.enabled = not self.enabled
        if not self.enabled and self.available:
            try:
                pygame.mixer.stop()
            except pygame.error:
                pass
        return self.enabled
