# Galatea

A desktop AI companion you can talk to. Speak into your mic, and Galatea listens, thinks, and talks back — with a live animated face.

```
Mic → Whisper STT → Ollama LLM → espeak-ng TTS → Pygame character window
                                                           ↑
                                                  Barbera lipsync
```

---

## Phase 1 status

- [x] Voice activity detection (energy-based)
- [x] Speech-to-text (faster-whisper `tiny.en`, offline)
- [x] LLM via Ollama REST API (any model)
- [x] Text-to-speech (pyttsx3 / espeak-ng, offline)
- [x] Pygame character window — animated face drawn with primitives
- [x] Barbera-style lipsync (3-frame mouth cycle driven by audio amplitude)
- [x] Blink animation, status indicator, conversation transcript

---

## Requirements

### System packages

```bash
sudo apt install espeak-ng libportaudio2 libsndfile1
```

### Ollama

Install from <https://ollama.com/>, then pull a small model:

```bash
ollama pull llama3.2:1b   # ~1 GB, fast on CPU
# or
ollama pull phi3:mini      # similar size, good quality
```

### Python

Requires Python 3.12+. Install with [uv](https://github.com/astral-sh/uv):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Setup

```bash
cd galatea
uv sync
```

The first run will download the Whisper `tiny.en` model (~74 MB, one time).

---

## Running

```bash
# GUI mode (default)
uv run galatea

# Console mode (no window)
uv run galatea --no-gui

# Use a different LLM model
uv run galatea --model phi3:mini

# Use a larger Whisper model for better accuracy
uv run galatea --whisper-model base
```

Close the window or press **ESC** / **Ctrl+C** to quit.

---

## Configuration

Edit `src/galatea/config.py` to tune:

| Section | Key | Default | Notes |
|---------|-----|---------|-------|
| `audio` | `silence_threshold` | `0.018` | Raise if mic picks up room noise |
| `audio` | `silence_duration` | `1.5 s` | How long silence ends a recording |
| `stt` | `model` | `tiny.en` | `base.en` is ~4× slower but more accurate |
| `llm` | `model` | `llama3.2:1b` | Any Ollama model |
| `llm` | `system_prompt` | … | Personality prompt |
| `tts` | `rate` | `165` | Words-per-minute for espeak |

---

## Project layout

```
src/galatea/
├── main.py          entry point + CLI
├── state.py         thread-safe shared state
├── config.py        dataclass configuration
├── pipeline.py      listen → STT → LLM → TTS orchestration
├── audio/
│   ├── capture.py   mic + VAD
│   └── playback.py  WAV playback with amplitude reporting
├── stt/
│   └── engine.py    faster-whisper wrapper
├── llm/
│   └── ollama.py    Ollama REST client
├── tts/
│   └── engine.py    pyttsx3 / espeak-ng TTS
└── character/
    ├── lipsync.py   Barbera mouth state machine
    └── window.py    pygame window + character renderer
```

---

## Upgrading TTS quality (Phase 2)

`pyttsx3 / espeak-ng` sounds robotic. Options to swap in later:

- **edge-tts** (`pip install edge-tts`) — Microsoft neural voices, free, requires internet
- **piper** — high-quality offline TTS, needs model download
- **kokoro-onnx** — very high quality, fully local Python package

The `TTSEngine` in `tts/engine.py` is isolated; swapping backends only requires changing that file.
