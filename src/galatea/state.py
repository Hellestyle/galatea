import threading
from typing import Literal

Status = Literal["idle", "listening", "processing", "thinking", "speaking", "error"]


class AppState:
    """Thread-safe shared state between the pipeline and the render window."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._status: Status = "idle"
        self._amplitude: float = 0.0
        self._user_text: str = ""
        self._ai_text: str = ""
        self._running: bool = True

    # ── status ──────────────────────────────────────────────────────────────
    @property
    def status(self) -> Status:
        with self._lock:
            return self._status

    @status.setter
    def status(self, value: Status) -> None:
        with self._lock:
            self._status = value

    # ── amplitude (0–1 float, drives lipsync) ───────────────────────────────
    @property
    def amplitude(self) -> float:
        with self._lock:
            return self._amplitude

    @amplitude.setter
    def amplitude(self, value: float) -> None:
        with self._lock:
            self._amplitude = float(value)

    # ── conversation text ────────────────────────────────────────────────────
    @property
    def user_text(self) -> str:
        with self._lock:
            return self._user_text

    @user_text.setter
    def user_text(self, value: str) -> None:
        with self._lock:
            self._user_text = value

    @property
    def ai_text(self) -> str:
        with self._lock:
            return self._ai_text

    @ai_text.setter
    def ai_text(self, value: str) -> None:
        with self._lock:
            self._ai_text = value

    # ── lifecycle ────────────────────────────────────────────────────────────
    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @running.setter
    def running(self, value: bool) -> None:
        with self._lock:
            self._running = value
