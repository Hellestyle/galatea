"""Galatea entry point."""

from __future__ import annotations

import argparse
import threading

from .config import Config
from .pipeline import Pipeline
from .state import AppState


def main() -> None:
    parser = argparse.ArgumentParser(description="Galatea — desktop AI companion")
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Run in headless console mode (no pygame window)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the Ollama model (e.g. llama3.2:3b, phi3:mini)",
    )
    parser.add_argument(
        "--whisper-model",
        default=None,
        help="Override the Whisper model (e.g. tiny, base, small)",
    )
    args = parser.parse_args()

    config = Config()
    if args.model:
        config.llm.model = args.model
    if args.whisper_model:
        config.stt.model = args.whisper_model

    state = AppState()
    pipeline = Pipeline(config, state)

    if args.no_gui:
        _run_console(pipeline, state)
    else:
        _run_gui(pipeline, config, state)


def _run_gui(pipeline: Pipeline, config: "Config", state: AppState) -> None:
    from .character.window import CharacterWindow

    thread = threading.Thread(target=pipeline.run, daemon=True, name="pipeline")
    thread.start()

    window = CharacterWindow(config.character, state)
    try:
        window.run()
    except KeyboardInterrupt:
        pass
    finally:
        state.running = False


def _run_console(pipeline: Pipeline, state: AppState) -> None:
    print("Galatea — console mode. Ctrl+C to quit.")
    try:
        pipeline.run()
    except KeyboardInterrupt:
        state.running = False
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
