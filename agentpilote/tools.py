"""Outils donnés à l'agent (format « function calling » OpenAI).

Les mêmes outils pourraient être exposés en MCP ; ici ils sont appelés
directement pour que la démo n'ait aucune dépendance.
"""
from __future__ import annotations

import json
from pathlib import Path

from .sandbox import Sandbox

MAX_READ = 12000


def _fn(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


SCHEMAS = [
    _fn("list_files", "Liste les fichiers du projet (récursif).",
        {"path": {"type": "string", "description": "Sous-dossier, '.' par défaut"}}, []),
    _fn("read_file", "Lit un fichier texte du projet.",
        {"path": {"type": "string"}}, ["path"]),
    _fn("write_file", "Crée ou remplace entièrement un fichier du projet.",
        {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    _fn("run", "Exécute une commande shell dans le bac à sable du projet (pas de réseau).",
        {"command": {"type": "string"}}, ["command"]),
    _fn("finish", "Déclare l'étape terminée. Donne un résumé court pour l'étape suivante.",
        {"summary": {"type": "string"}}, ["summary"]),
]


class Toolbox:
    def __init__(self, workdir: Path, sandbox: Sandbox):
        self.root = Path(workdir).resolve()
        self.sandbox = sandbox
        self.written: list[str] = []

    def _safe(self, rel: str) -> Path:
        p = (self.root / (rel or ".")).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"chemin hors du projet refusé : {rel}")
        return p

    # --- outils -------------------------------------------------------------
    def list_files(self, path: str = ".") -> str:
        base = self._safe(path)
        if not base.exists():
            return "(dossier inexistant)"
        files = sorted(
            str(f.relative_to(self.root)) for f in base.rglob("*")
            if f.is_file() and "__pycache__" not in f.parts and not f.name.startswith(".")
        )
        return "\n".join(files) or "(vide)"

    def read_file(self, path: str) -> str:
        p = self._safe(path)
        if not p.is_file():
            return f"ERREUR : {path} n'existe pas"
        text = p.read_text(errors="replace")
        return text if len(text) <= MAX_READ else text[:MAX_READ] + "\n[... tronqué ...]"

    def write_file(self, path: str, content: str) -> str:
        p = self._safe(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        self.written.append(path)
        return f"OK : {path} écrit ({len(content)} caractères)"

    def run(self, command: str) -> str:
        return self.sandbox.run(command).short()

    # --- répartiteur --------------------------------------------------------
    def call(self, name: str, raw_args: str | dict) -> str:
        try:
            args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")
        except json.JSONDecodeError as exc:
            return f"ERREUR : arguments JSON invalides ({exc})"
        fn = {"list_files": self.list_files, "read_file": self.read_file,
              "write_file": self.write_file, "run": self.run}.get(name)
        if fn is None:
            return f"ERREUR : outil inconnu {name}"
        try:
            return fn(**args)
        except (TypeError, ValueError, OSError) as exc:
            return f"ERREUR : {exc}"
