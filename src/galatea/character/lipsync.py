"""Barbera-style lipsync: alternates a small set of mouth frames during speech."""

from __future__ import annotations

import time
from enum import Enum


class MouthState(Enum):
    CLOSED = 0        # resting / silence
    SLIGHTLY_OPEN = 1 # transition frame
    OPEN = 2          # normal speech
    WIDE_OPEN = 3     # emphasis / loud audio


# Barbera cycle: close → slightly → open → slightly → … (loops)
_CYCLE = [
    MouthState.CLOSED,
    MouthState.SLIGHTLY_OPEN,
    MouthState.OPEN,
    MouthState.SLIGHTLY_OPEN,
]

# Amplitude above this triggers WIDE_OPEN instead of OPEN
_LOUD_THRESHOLD = 0.08


class Lipsync:
    def __init__(self, anim_fps: float = 9.0) -> None:
        self._frame_duration = 1.0 / anim_fps
        self._last_flip = 0.0
        self._idx = 0

    def update(self, speaking: bool, amplitude: float = 0.0) -> MouthState:
        if not speaking:
            return MouthState.CLOSED

        now = time.monotonic()
        if now - self._last_flip >= self._frame_duration:
            self._idx = (self._idx + 1) % len(_CYCLE)
            self._last_flip = now

        state = _CYCLE[self._idx]
        if state == MouthState.OPEN and amplitude > _LOUD_THRESHOLD:
            return MouthState.WIDE_OPEN
        return state
