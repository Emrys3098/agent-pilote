"""Boucle d'agent : comprendre → agir (outils) → vérifier → décider (finish)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .tools import SCHEMAS, Toolbox


@dataclass
class AgentResult:
    finished: bool
    summary: str
    turns: int
    log: list[str] = field(default_factory=list)


NUDGE = ("Tu n'as appelé aucun outil. Continue le travail avec les outils, "
         "puis appelle `finish` avec un résumé quand l'étape est vraiment faite et vérifiée.")


def run_agent(llm, system: str, task: str, toolbox: Toolbox, max_turns: int = 25,
              on_event=None) -> AgentResult:
    """Fait travailler le modèle sur `task` jusqu'à `finish` ou `max_turns`."""
    messages: list[dict] = [{"role": "system", "content": system}, {"role": "user", "content": task}]
    log: list[str] = []
    nudged = 0

    def event(msg: str) -> None:
        log.append(msg)
        if on_event:
            on_event(msg)

    for turn in range(1, max_turns + 1):
        msg = llm.chat(messages, tools=SCHEMAS)
        calls = msg.get("tool_calls") or []
        assistant = {"role": "assistant", "content": msg.get("content") or ""}
        if calls:
            assistant["tool_calls"] = calls
        messages.append(assistant)
        if not calls:
            if nudged >= 2:
                return AgentResult(False, (msg.get("content") or "").strip(), turn, log)
            nudged += 1
            messages.append({"role": "user", "content": NUDGE})
            continue
        for call in calls:
            fn = call.get("function", {})
            name, args = fn.get("name", ""), fn.get("arguments", "{}")
            if name == "finish":
                try:
                    summary = (args if isinstance(args, dict) else json.loads(args or "{}")).get("summary", "")
                except json.JSONDecodeError:
                    summary = str(args)
                event(f"  ✓ finish : {summary[:160]}")
                return AgentResult(True, summary, turn, log)
            result = toolbox.call(name, args)
            event(f"  · {name} {_preview(args)} → {result.splitlines()[0][:100] if result else ''}")
            messages.append({"role": "tool", "tool_call_id": call.get("id", name), "name": name,
                             "content": result})
    return AgentResult(False, "nombre maximal de tours atteint", max_turns, log)


def _preview(args) -> str:
    s = args if isinstance(args, str) else str(args)
    s = s.replace("\n", " ")
    return s[:80] + ("…" if len(s) > 80 else "")
