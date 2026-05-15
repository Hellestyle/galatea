from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_FILE  = _PROJECT_ROOT / "galatea.toml"


@dataclass
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration: float = 0.1          # seconds per VAD chunk
    silence_threshold: float = 0.018     # RMS energy threshold for speech
    silence_duration: float = 1.5        # seconds of silence to end recording
    max_recording_duration: float = 30.0 # hard limit


@dataclass
class STTConfig:
    model: str = "tiny.en"    # tiny.en is English-only but faster; use "tiny" for multilingual
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    language: str = "en"


@dataclass
class LLMConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.2:1b"
    system_prompt: str = (
        "You are Galatea, a friendly and thoughtful desktop AI companion. "
        "Keep your responses concise and conversational — one to three sentences. "
        "Be warm, curious, and helpful."
    )
    max_tokens: int = 300
    temperature: float = 0.75


@dataclass
class TTSConfig:
    # edge-tts voice name — run `edge-tts --list-voices | grep Female` to browse
    voice: str = "en-US-JennyNeural"
    rate: str = "+0%"    # e.g. "+10%" faster, "-10%" slower
    volume: str = "+0%"
    pitch: str = "+0Hz"


@dataclass
class CharacterConfig:
    window_width: int = 600
    window_height: int = 800
    # Camera framing for the 3D model
    camera_distance_factor: float = 2.4    # distance = model_radius × this
    camera_height_offset: float = 0.18     # shifts focus upward (portrait framing)
    camera_fov: float = 40.0
    # Animation names in the GLB — change if your export uses different names
    anim_idle: str = "idle"
    anim_talk: str = "talk"


@dataclass
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    character: CharacterConfig = field(default_factory=CharacterConfig)


def load_config() -> Config:
    """Load Config from galatea.toml, falling back to built-in defaults."""
    config = Config()

    if not _CONFIG_FILE.exists():
        return config

    with open(_CONFIG_FILE, "rb") as f:
        data = tomllib.load(f)

    _overlay(data.get("audio", {}),     config.audio)
    _overlay(data.get("stt", {}),       config.stt)
    _overlay(data.get("llm", {}),       config.llm)
    _overlay(data.get("tts", {}),       config.tts)
    _overlay(data.get("character", {}), config.character)

    return config


def _overlay(toml_section: dict, obj: object) -> None:
    """Copy recognised keys from a TOML section onto a dataclass instance."""
    for key, value in toml_section.items():
        if hasattr(obj, key):
            setattr(obj, key, value)
        else:
            print(f"[config] Unknown key '{key}' in galatea.toml — ignored")
