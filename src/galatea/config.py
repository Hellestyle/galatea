from dataclasses import dataclass, field


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
    window_width: int = 420
    window_height: int = 580
    fps: int = 30
    mouth_anim_fps: float = 9.0   # Barbera mouth flip rate


@dataclass
class Config:
    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    character: CharacterConfig = field(default_factory=CharacterConfig)
