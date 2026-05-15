"""Text-to-speech using edge-tts (Microsoft neural voices, free, requires internet)."""

from __future__ import annotations

import asyncio
import tempfile

import edge_tts

from ..config import TTSConfig


class TTSEngine:
    def __init__(self, config: TTSConfig) -> None:
        self.config = config

    def synthesize(self, text: str) -> str:
        """Convert text to speech, write to a temp MP3 file, return the path.

        Caller is responsible for deleting the file after playback.
        Requires an internet connection (uses Microsoft's free neural TTS).
        """
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        asyncio.run(self._synthesize_async(text, tmp.name))
        return tmp.name

    async def _synthesize_async(self, text: str, path: str) -> None:
        communicate = edge_tts.Communicate(
            text,
            self.config.voice,
            rate=self.config.rate,
            volume=self.config.volume,
            pitch=self.config.pitch,
        )
        await communicate.save(path)
