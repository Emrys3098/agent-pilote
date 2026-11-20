"""Client minimal pour toute API compatible OpenAI (Ollama, llama.cpp, vLLM, Halogen...).

Aucune dépendance externe : uniquement la bibliothèque standard.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0

    def add(self, other: "Usage") -> None:
        self.calls += other.calls
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.seconds += other.seconds

    @property
    def tokens_per_second(self) -> float:
        return self.completion_tokens / self.seconds if self.seconds else 0.0


@dataclass
class LLM:
    """Un modèle servi localement derrière une API /v1/chat/completions."""

    base_url: str
    model: str
    api_key: str = "local"
    timeout: float = 900.0
    temperature: float = 0.2
    usage: Usage = field(default_factory=Usage)

    @property
    def name(self) -> str:
        return self.model

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        """Renvoie le message de l'assistant (dict OpenAI : content, tool_calls...)."""
        body: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "stream": False,
        }
        if tools:
            body["tools"] = tools
        req = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.load(resp)
        except TimeoutError as exc:
            self.usage.add(Usage(1, 0, 0, time.monotonic() - t0))
            raise RuntimeError(f"pas de réponse du modèle après {self.timeout:.0f} s") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Modèle injoignable sur {self.base_url} ({exc}). "
                "Le serveur local (ex. `ollama serve`) est-il lancé ?"
            ) from exc
        dt = time.monotonic() - t0
        u = data.get("usage") or {}
        self.usage.add(Usage(1, u.get("prompt_tokens", 0), u.get("completion_tokens", 0), dt))
        return data["choices"][0]["message"]
