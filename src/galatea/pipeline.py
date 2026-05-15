"""Main pipeline: listen → transcribe → LLM → speak, in a background thread."""

from __future__ import annotations

import os
import time

from .audio.capture import AudioCapture
from .audio.playback import play_mp3
from .config import Config
from .llm.ollama import OllamaClient
from .state import AppState
from .stt.engine import STTEngine
from .tts.engine import TTSEngine

Message = dict[str, str]
MAX_HISTORY = 20   # messages to keep in context window


class Pipeline:
    def __init__(self, config: Config, state: AppState) -> None:
        self.state = state
        self.capture = AudioCapture(config.audio)
        self.stt = STTEngine(config.stt)
        self.llm = OllamaClient(config.llm)
        self.tts = TTSEngine(config.tts)
        self.history: list[Message] = []

    def run(self) -> None:
        print("[pipeline] Loading STT model…")
        self.stt.load()

        if not self.llm.is_model_available():
            print(
                f"[pipeline] Warning: model '{self.llm.config.model}' not found in Ollama.\n"
                f"           Pull it with: ollama pull {self.llm.config.model}"
            )

        print("[pipeline] Ready. Start speaking!")

        while self.state.running:
            try:
                self._cycle()
            except KeyboardInterrupt:
                break
            except Exception as exc:
                print(f"[pipeline] Unhandled error: {exc}")
                self.state.status = "error"
                time.sleep(2)
                self.state.status = "idle"

    def _cycle(self) -> None:
        # If mic is muted, park in standby and return quickly
        if not self.state.mic_enabled:
            self.state.status = "standby"
            time.sleep(0.2)
            return

        # 1 ─ Listen
        self.state.status = "listening"
        audio = self.capture.listen_for_speech(
            # Abort cleanly if app exits OR user mutes mid-listen
            running_check=lambda: self.state.running and self.state.mic_enabled,
        )

        if audio is None or not self.state.running:
            # Mic was disabled mid-listen — show standby rather than idle
            self.state.status = "standby" if not self.state.mic_enabled else "idle"
            return

        # 2 ─ Transcribe
        self.state.status = "processing"
        text = self.stt.transcribe(audio)
        text = text.strip()

        if not text:
            self.state.status = "idle"
            time.sleep(0.3)
            return

        print(f"[you] {text}")
        self.state.user_text = text

        # 3 ─ LLM
        self.state.status = "thinking"
        self.history.append({"role": "user", "content": text})
        response = self.llm.chat(self.history)
        self.history.append({"role": "assistant", "content": response})

        # Keep history bounded
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        print(f"[galatea] {response}")
        self.state.ai_text = response

        # 4 ─ TTS + playback
        self.state.status = "speaking"
        audio_path = self.tts.synthesize(response)
        try:
            play_mp3(
                audio_path,
                amplitude_callback=lambda a: setattr(self.state, "amplitude", a),
                running_check=lambda: self.state.running,
            )
        finally:
            try:
                os.unlink(audio_path)
            except OSError:
                pass

        self.state.amplitude = 0.0
        self.state.status = "idle"
