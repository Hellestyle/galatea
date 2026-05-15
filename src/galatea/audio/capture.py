"""Microphone capture with simple energy-based Voice Activity Detection."""

from __future__ import annotations

import queue
from typing import Callable

import numpy as np
import sounddevice as sd

from ..config import AudioConfig


class AudioCapture:
    def __init__(self, config: AudioConfig) -> None:
        self.config = config
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=500)

    def _callback(self, indata: np.ndarray, frames: int, time, status) -> None:  # noqa: ANN001
        if status:
            print(f"[audio] {status}")
        try:
            self._queue.put_nowait(indata.copy())
        except queue.Full:
            pass  # drop oldest implicitly — queue was full

    def listen_for_speech(
        self,
        running_check: Callable[[], bool] = lambda: True,
    ) -> np.ndarray | None:
        """Block until speech is detected, record until silence, return float32 mono array.

        Returns None if running_check() goes False before speech starts.
        """
        cfg = self.config
        chunk_samples = int(cfg.sample_rate * cfg.chunk_duration)
        silence_chunks_needed = int(cfg.silence_duration / cfg.chunk_duration)
        max_chunks = int(cfg.max_recording_duration / cfg.chunk_duration)

        # Clear stale data
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        frames_recorded: list[np.ndarray] = []
        silence_count = 0
        speech_started = False

        with sd.InputStream(
            samplerate=cfg.sample_rate,
            channels=cfg.channels,
            dtype="float32",
            blocksize=chunk_samples,
            callback=self._callback,
        ):
            while running_check():
                try:
                    chunk = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue

                rms = float(np.sqrt(np.mean(chunk ** 2)))
                is_speech = rms > cfg.silence_threshold

                if is_speech:
                    if not speech_started:
                        speech_started = True
                    silence_count = 0
                    frames_recorded.append(chunk)
                elif speech_started:
                    frames_recorded.append(chunk)
                    silence_count += 1
                    if silence_count >= silence_chunks_needed:
                        break

                if speech_started and len(frames_recorded) >= max_chunks:
                    break

        if not frames_recorded:
            return None

        return np.concatenate(frames_recorded, axis=0).flatten()
