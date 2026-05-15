"""MP3 playback via pygame.mixer with a constant amplitude signal for lipsync."""

from __future__ import annotations

import time
from typing import Callable

import pygame

# Constant RMS-equivalent sent to lipsync while audio is playing.
# Enough to keep the Barbera cycle running without real per-chunk data.
_SPEAKING_AMPLITUDE = 0.05


def play_mp3(
    filepath: str,
    amplitude_callback: Callable[[float], None],
    running_check: Callable[[], bool] = lambda: True,
) -> None:
    """Play an MP3 file, pulsing amplitude_callback(0.05) while it plays.

    Stops early if running_check() returns False.
    Always calls amplitude_callback(0.0) when done.
    """
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    pygame.mixer.music.load(filepath)
    pygame.mixer.music.play()

    try:
        while pygame.mixer.music.get_busy() and running_check():
            amplitude_callback(_SPEAKING_AMPLITUDE)
            time.sleep(0.04)   # ~25 Hz poll — fine-grained enough for lipsync
    finally:
        pygame.mixer.music.stop()
        amplitude_callback(0.0)
