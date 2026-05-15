# Galatea

A desktop AI companion you can talk to. Speak into your mic — Galatea listens, thinks, and responds with a live animated 3D character.

```
Mic → Whisper STT → Ollama LLM → edge-tts → Panda3D character window
                                                      ↑
                                            idle / talk animations
```

---

## Requirements

### System packages (Arch Linux)

```bash
sudo pacman -S portaudio
```

### System packages (Ubuntu/Debian)

```bash
sudo apt install libportaudio2 libsndfile1
```

### Ollama

Install from <https://ollama.com/>, then pull a model:

```bash
ollama pull llama3.2:1b   # ~1 GB, fast on CPU
# or
ollama pull llama3.2:3b   # better quality, still runs on CPU
# or
ollama pull phi3:mini      # good alternative
```

### Python

Requires Python 3.12+. Install [uv](https://github.com/astral-sh/uv) if you haven't:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Setup

```bash
cd galatea
uv sync
```

The first run will download the Whisper `tiny.en` model (~74 MB, one time only).

---

## Running

```bash
uv run galatea
```

Close the window or press **ESC** / **Ctrl+C** to quit.

**CLI overrides** (take precedence over `galatea.toml`):

```bash
# Use a different LLM model for this session
uv run galatea --model phi3:mini

# Use a more accurate Whisper model for this session
uv run galatea --whisper-model base.en

# Run without a window (console only)
uv run galatea --no-gui
```

---

## Configuration

All settings live in **`galatea.toml`** at the project root. The file is heavily commented — open it in any text editor.

Key things to change:

| Section | Key | What it does |
|---------|-----|-------------|
| `[llm]` | `model` | Ollama model to use (e.g. `llama3.2:3b`, `phi3:mini`) |
| `[llm]` | `host` | Ollama server URL — change if Ollama runs on another machine |
| `[llm]` | `system_prompt` | Galatea's personality / instructions |
| `[tts]` | `voice` | Microsoft neural voice (see list below) |
| `[tts]` | `rate` | Speaking speed: `"+10%"` faster, `"-10%"` slower |
| `[stt]` | `model` | Whisper model: `tiny.en` / `base.en` / `small.en` |
| `[audio]` | `silence_threshold` | Raise if mic triggers on background noise |
| `[character]` | `window_width/height` | Window size in pixels |

### Browsing TTS voices

```bash
uv run python -c "
import asyncio, edge_tts
voices = asyncio.run(edge_tts.list_voices())
for v in voices:
    if v['Locale'].startswith('en-'):
        print(v['ShortName'], '-', v['Gender'])
"
```

---

## Adding a 3D character

Galatea supports any Mixamo character with idle and talk animations.

### 1 — Get a character from Mixamo

1. Go to <https://www.mixamo.com> and sign in (free Adobe account).
2. Pick a character you like and click **Use this character**.
3. Find the **Idle** animation, set FPS to 60, download as **FBX for Unity** — tick **With Skin**.
4. Find the **Talking** animation, download the same way — this time **Without Skin**.

### 2 — Convert to GLB with Blender

Install [Blender](https://www.blender.org/download/) (3.6 or newer), then run:

```bash
blender --background --python scripts/blender_convert.py -- /path/to/idle.fbx /path/to/talk.fbx
```

This produces:

```
assets/character/
├── idle.glb    ← mesh + idle animation
└── talk.glb    ← talk animation
```

### 3 — Run Galatea

```bash
uv run galatea
```

If no GLB files are present, Galatea shows a placeholder sphere so the rest of the app still works.

---

## Project layout

```
galatea.toml             ← your configuration (edit this)
scripts/
└── blender_convert.py   Mixamo FBX → GLB converter
assets/character/
├── idle.glb             character mesh + idle animation  (git-ignored, you provide)
└── talk.glb             talking animation                (git-ignored, you provide)
src/galatea/
├── main.py              entry point + CLI flags
├── state.py             thread-safe shared state
├── config.py            dataclass definitions + TOML loader
├── pipeline.py          listen → STT → LLM → TTS loop
├── audio/
│   ├── capture.py       mic + voice activity detection
│   └── playback.py      MP3 playback via pygame
├── stt/
│   └── engine.py        faster-whisper wrapper
├── llm/
│   └── ollama.py        Ollama REST client
├── tts/
│   └── engine.py        edge-tts (Microsoft neural voices)
└── character/
    └── window.py        Panda3D window, 3D model, animations
```

---

## Development cheatsheet

Everything runs through [uv](https://github.com/astral-sh/uv) — you never need to activate the virtualenv manually just to run or install things.

### Day-to-day commands

```bash
uv run galatea          # run the app (uv handles the venv automatically)
uv sync                 # install / sync all dependencies from pyproject.toml
uv add <package>        # add a new dependency and update pyproject.toml
uv remove <package>     # remove a dependency
```

### If you want a plain shell inside the venv

```bash
source .venv/bin/activate   # activate
python ...                  # now `python` points at the project's interpreter
deactivate                  # leave the venv
```

### If the venv is broken or missing

```bash
rm -rf .venv        # delete it entirely
uv sync             # uv recreates it and reinstalls everything
```

### If Python itself is missing or the wrong version

```bash
uv python install 3.12   # download and install Python 3.12 via uv
uv sync                  # then rebuild the venv
```

### Useful one-liners

```bash
# List all installed packages in the venv
uv pip list

# Run a quick Python snippet in the project environment
uv run python -c "from galatea.config import load_config; print(load_config())"

# Browse available edge-tts voices
uv run python -c "
import asyncio, edge_tts
voices = asyncio.run(edge_tts.list_voices())
for v in voices:
    if v['Locale'].startswith('en-'):
        print(v['ShortName'], '-', v['Gender'])
"
```

---

## Troubleshooting

**"No module named sounddevice"** — run `uv sync` to install dependencies.

**Galatea triggers on background noise** — raise `silence_threshold` in `galatea.toml` (try `0.03`).

**Whisper mishears you** — switch to a larger model: set `model = "base.en"` in `[stt]`.

**Ollama connection refused** — make sure Ollama is running (`ollama serve`) and that `host` in `galatea.toml` matches.

**3D model shows as placeholder sphere** — check that `assets/character/idle.glb` exists. Run the Blender converter (step 2 above).

**High CPU / GPU usage** — Panda3D is already capped at 30 fps with 2× MSAA. If it's still heavy, reduce `window_width`/`window_height` in `galatea.toml`.
