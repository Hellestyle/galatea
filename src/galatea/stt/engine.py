"""Speech-to-text using faster-whisper (local, offline)."""

from __future__ import annotations

import numpy as np

from ..config import STTConfig


class STTEngine:
    def __init__(self, config: STTConfig) -> None:
        self.config = config
        self._model = None

    def load(self) -> None:
        """Pre-load the Whisper model (downloads ~74 MB on first run)."""
        if self._model is None:
            print(f"[stt] Loading Whisper model '{self.config.model}' — may download on first run…")
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self.config.model,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
            print("[stt] Model ready.")

    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe float32 mono audio (16 kHz) to text."""
        self.load()
        segments, _info = self._model.transcribe(  # type: ignore[union-attr]
            audio,
            beam_size=self.config.beam_size,
            language=self.config.language,
            vad_filter=True,          # built-in VAD post-filter to drop noise segments
            vad_parameters={"min_silence_duration_ms": 300},
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
