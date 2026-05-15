"""Ollama REST API client for local LLM inference."""

from __future__ import annotations

import httpx

from ..config import LLMConfig

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": str}


class OllamaClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def chat(self, history: list[Message]) -> str:
        """Send conversation history to Ollama and return the assistant reply."""
        messages: list[Message] = [
            {"role": "system", "content": self.config.system_prompt},
            *history,
        ]
        try:
            response = httpx.post(
                f"{self.config.host}/api/chat",
                json={
                    "model": self.config.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.config.temperature,
                        "num_predict": self.config.max_tokens,
                    },
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()["message"]["content"].strip()
        except httpx.ConnectError:
            return (
                "I can't reach my brain right now — is Ollama running? "
                f"Try: ollama serve, then: ollama pull {self.config.model}"
            )
        except Exception as exc:
            return f"Something went wrong talking to Ollama: {exc}"

    def is_model_available(self) -> bool:
        """Check whether the configured model exists in Ollama."""
        try:
            r = httpx.get(f"{self.config.host}/api/tags", timeout=5.0)
            names = [m["name"] for m in r.json().get("models", [])]
            return any(self.config.model in n for n in names)
        except Exception:
            return False
