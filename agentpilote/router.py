"""Orchestrateur : choisit le modèle adapté à chaque demande.

Sur la station complète, le modèle rapide est Qwen3.8-Flash-Next (125B) et les
paliers « profonds » sont DeepSeek-R1 70B puis GPT-OSS 120B. Ici, n'importe quels
modèles compatibles OpenAI peuvent être branchés par variables d'environnement.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .llm import LLM

DEEP_TAG = "!!deep"
FAST_TAG = "!!fast"
DEEP_KEYWORDS = ("démontre", "prouve", "architecture", "pourquoi", "analyse en profondeur",
                 "prove", "why", "root cause", "cause racine")
DEEP_CHAR_THRESHOLD = 1500


@dataclass
class Route:
    llm: LLM
    reason: str
    text: str  # message nettoyé des balises de routage


class Router:
    def __init__(self, fast: LLM, deep: LLM | None = None):
        self.fast = fast
        self.deep = deep or fast

    @classmethod
    def from_env(cls) -> "Router":
        base = os.environ.get("AP_BASE_URL", "http://localhost:11434/v1")
        key = os.environ.get("AP_API_KEY", "local")
        fast = LLM(base, os.environ.get("AP_MODEL", "qwen3:30b-a3b"), key)
        deep_model = os.environ.get("AP_DEEP_MODEL")
        deep = LLM(os.environ.get("AP_DEEP_BASE_URL", base), deep_model, key) if deep_model else None
        return cls(fast, deep)

    def route(self, text: str) -> Route:
        stripped = text.strip()
        if stripped.startswith(FAST_TAG):
            return Route(self.fast, "forcé rapide (!!fast)", stripped[len(FAST_TAG):].strip())
        if stripped.startswith(DEEP_TAG):
            return Route(self.deep, "forcé profond (!!deep)", stripped[len(DEEP_TAG):].strip())
        low = stripped.lower()
        if len(stripped) > DEEP_CHAR_THRESHOLD:
            return Route(self.deep, "demande longue", stripped)
        if any(k in low for k in DEEP_KEYWORDS):
            return Route(self.deep, "mot-clé de réflexion", stripped)
        return Route(self.fast, "par défaut", stripped)

    def escalate(self) -> LLM:
        """Palier supérieur, utilisé par Pilote après des échecs répétés."""
        return self.deep
