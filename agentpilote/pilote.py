"""Pilote : mène un projet long, étape par étape, sans surveillance.

Principes (repris de la station complète) :
1. Planifier : le modèle découpe le cahier des charges en étapes vérifiables.
2. Contexte neuf à chaque étape : le modèle ne reçoit que le cahier des charges,
   le plan, la passation écrite des étapes précédentes et son étape. Le contexte
   ne gonfle jamais, même sur des centaines d'étapes.
3. Bac à sable : toutes les commandes tournent sans réseau, système en lecture seule.
4. Vérifier avant d'avancer : chaque étape a une commande de contrôle ; tant
   qu'elle échoue, l'étape est reprise avec l'erreur, puis confiée au modèle
   « profond » si l'échec persiste.
5. Passation écrite (PASSATION.md) et rapport final chronométré (RAPPORT.md).
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .agent import run_agent
from .router import Router
from .sandbox import Sandbox
from .tools import Toolbox

PLAN_PROMPT = """Tu es le planificateur d'un agent de développement autonome.
Découpe le cahier des charges en {min_steps} à {max_steps} étapes courtes, chacune réalisable
en quelques fichiers. Chaque étape a une commande shell de contrôle `check` qui réussit
(code 0) seulement si l'étape est vraiment faite (par ex. `python3 -m unittest -q`).
Le projet est en Python 3, bibliothèque standard uniquement, sans réseau.
Réponds UNIQUEMENT avec ce JSON :
{{"steps": [{{"title": "...", "goal": "...", "check": "..."}}]}}"""

STEP_SYSTEM = """Tu es un agent de développement autonome qui travaille dans un dossier de projet.
Règles :
- Utilise les outils : list_files, read_file, write_file, run, finish.
- Fais UNIQUEMENT l'étape demandée, sans casser ce que les étapes précédentes ont fait.
- Vérifie ton travail avec `run` (lance la commande de contrôle) avant d'appeler `finish`.
- `finish` prend un résumé court et factuel : fichiers créés, choix faits, points d'attention.
- Pas de réseau ; Python 3 et bibliothèque standard seulement.{extra}"""


@dataclass
class Step:
    title: str
    goal: str
    check: str
    status: str = "à faire"
    attempts: int = 0
    model: str = ""
    seconds: float = 0.0
    summary: str = ""
    last_check: str = ""


@dataclass
class Report:
    spec: str
    steps: list[Step] = field(default_factory=list)
    seconds: float = 0.0
    sandbox: str = ""
    success: bool = False


class Pilote:
    def __init__(self, router: Router, workdir: Path, max_attempts: int = 3, max_turns: int = 25,
                 escalate_after: int = 2, verbose: bool = True, extra_rules: str = ""):
        self.router = router
        self.workdir = Path(workdir).resolve()
        self.sandbox = Sandbox(self.workdir)
        self.toolbox = Toolbox(self.workdir, self.sandbox)
        self.max_attempts = max_attempts
        self.max_turns = max_turns
        self.escalate_after = escalate_after
        self.verbose = verbose
        self.extra_rules = extra_rules
        self.ntfy = os.environ.get("AP_NTFY_URL")  # optionnel : notification sur téléphone

    # ------------------------------------------------------------------ utils
    def say(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    def notify(self, msg: str) -> None:
        if not self.ntfy:
            return
        try:
            urllib.request.urlopen(urllib.request.Request(self.ntfy, data=msg.encode()), timeout=5)
        except OSError:
            pass

    # --------------------------------------------------------------- planning
    def plan(self, spec: str, min_steps: int = 2, max_steps: int = 6) -> list[Step]:
        llm = self.router.fast
        msg = llm.chat([
            {"role": "system", "content": PLAN_PROMPT.format(min_steps=min_steps, max_steps=max_steps)},
            {"role": "user", "content": spec},
        ])
        steps = parse_plan(msg.get("content") or "")
        if not steps:
            raise RuntimeError("Le modèle n'a pas produit de plan JSON exploitable.")
        return steps[:max_steps]

    # ------------------------------------------------------------------- run
    def run(self, spec: str, steps: list[Step] | None = None) -> Report:
        t0 = time.monotonic()
        self.workdir.mkdir(parents=True, exist_ok=True)
        report = Report(spec=spec, sandbox=self.sandbox.kind)
        self.say(f"Pilote — dossier : {self.workdir}\nBac à sable : {self.sandbox.kind}")
        if steps is None:
            self.say("Planification…")
            steps = self.plan(spec)
        report.steps = steps
        (self.workdir / "PLAN.json").write_text(json.dumps([asdict(s) for s in steps], ensure_ascii=False, indent=2))
        for i, s in enumerate(steps, 1):
            self.say(f"  {i}. {s.title}   [contrôle : {s.check}]")

        for i, step in enumerate(steps, 1):
            self.say(f"\n=== Étape {i}/{len(steps)} : {step.title}")
            self.run_step(spec, steps, i - 1)
            self.notify(f"Pilote — étape {i}/{len(steps)} {step.status} : {step.title}")
            if step.status != "réussie":
                self.say(f"Arrêt : l'étape {i} n'a pas pu être validée.")
                break

        report.seconds = time.monotonic() - t0
        report.success = all(s.status == "réussie" for s in steps)
        (self.workdir / "RAPPORT.md").write_text(render_report(report, self.router))
        self.say(f"\n{'SUCCÈS' if report.success else 'ÉCHEC'} en {report.seconds:.0f} s — rapport : {self.workdir / 'RAPPORT.md'}")
        self.notify(f"Pilote terminé : {'succès' if report.success else 'échec'} en {report.seconds:.0f} s")
        return report

    def run_step(self, spec: str, steps: list[Step], idx: int) -> None:
        step = steps[idx]
        t0 = time.monotonic()
        feedback = ""
        for attempt in range(1, self.max_attempts + 1):
            step.attempts = attempt
            llm = self.router.escalate() if attempt > self.escalate_after else self.router.fast
            step.model = llm.name
            self.say(f"-- tentative {attempt} (modèle : {llm.name})")
            task = self.build_task(spec, steps, idx, feedback)
            system = STEP_SYSTEM.format(extra=("\n" + self.extra_rules) if self.extra_rules else "")
            try:
                result = run_agent(llm, system, task, self.toolbox, self.max_turns, on_event=self.say)
            except RuntimeError as exc:
                # modèle bloqué (réponse trop longue) ou injoignable : tentative ratée, pas plantage du projet
                self.say(f"   modèle en échec : {exc}")
                feedback = (f"La tentative précédente a été interrompue ({exc}). "
                            "Avance par petites actions courtes et vérifie avec `run`.")
                continue
            check = self.sandbox.run(step.check)
            step.last_check = check.short()[-1500:]
            if check.ok:
                step.status, step.summary = "réussie", result.summary or "(pas de résumé)"
                self.say(f"   contrôle OK ✓")
                self.append_handoff(idx + 1, step)
                break
            self.say(f"   contrôle en échec ✗ ({check.short().splitlines()[0]})")
            feedback = (f"La tentative précédente a échoué au contrôle `{step.check}` :\n"
                        f"{check.short()[-2500:]}\nCorrige le problème.")
        else:
            step.status = "échouée"
        step.seconds = time.monotonic() - t0

    def build_task(self, spec: str, steps: list[Step], idx: int, feedback: str) -> str:
        plan = "\n".join(f"{n}. [{'x' if s.status == 'réussie' else ' '}] {s.title}"
                         for n, s in enumerate(steps, 1))
        handoff_path = self.workdir / "PASSATION.md"
        handoff = handoff_path.read_text()[-4000:] if handoff_path.exists() else "(première étape)"
        step = steps[idx]
        return (f"# Cahier des charges\n{spec}\n\n# Plan\n{plan}\n\n"
                f"# Passation des étapes précédentes\n{handoff}\n\n"
                f"# Ton étape ({idx + 1}/{len(steps)}) : {step.title}\n{step.goal}\n\n"
                f"Contrôle qui doit réussir : `{step.check}`\n"
                + (f"\n# Attention\n{feedback}\n" if feedback else ""))

    def append_handoff(self, n: int, step: Step) -> None:
        with (self.workdir / "PASSATION.md").open("a") as f:
            f.write(f"## Étape {n} — {step.title}\n{step.summary.strip()}\n\n")


# ---------------------------------------------------------------------- helpers
def parse_plan(text: str) -> list[Step]:
    """Extrait le JSON du plan, même entouré de texte, de balises <think> ou de ```."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    candidates = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            data = json.loads(c)
        except json.JSONDecodeError:
            continue
        raw = data.get("steps") if isinstance(data, dict) else None
        if isinstance(raw, list):
            steps = [Step(str(s.get("title", f"Étape {i}")), str(s.get("goal", "")),
                          str(s.get("check", "true")))
                     for i, s in enumerate(raw, 1) if isinstance(s, dict)]
            if steps:
                return steps
    return []


def render_report(report: Report, router: Router) -> str:
    usage = router.fast.usage
    lines = [
        "# Rapport Pilote", "",
        f"- Résultat : **{'succès' if report.success else 'échec'}**",
        f"- Durée totale : {report.seconds:.0f} s",
        f"- Bac à sable : {report.sandbox}",
        f"- Modèle rapide : {router.fast.name} ({usage.calls} appels, "
        f"{usage.completion_tokens} jetons générés, {usage.tokens_per_second:.1f} jetons/s)",
    ]
    if router.deep is not router.fast:
        d = router.deep.usage
        lines.append(f"- Modèle profond : {router.deep.name} ({d.calls} appels)")
    lines += ["", "| # | Étape | Statut | Tentatives | Modèle | Durée |", "|---|---|---|---|---|---|"]
    for i, s in enumerate(report.steps, 1):
        lines.append(f"| {i} | {s.title} | {s.status} | {s.attempts} | {s.model} | {s.seconds:.0f} s |")
    lines += ["", "## Résumés de passation", ""]
    for i, s in enumerate(report.steps, 1):
        if s.summary:
            lines += [f"**{i}. {s.title}** — {s.summary}", ""]
    return "\n".join(lines) + "\n"
