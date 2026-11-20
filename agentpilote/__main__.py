"""Ligne de commande.

  python3 -m agentpilote demo                 # projet d'exemple (calculatrice RPN)
  python3 -m agentpilote run SPEC.md -o DIR   # n'importe quel cahier des charges
  python3 -m agentpilote chat "message"       # une demande routée vers le bon modèle, avec outils
  python3 -m agentpilote check                # vérifie que le modèle local répond
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import run_agent
from .pilote import STEP_SYSTEM, Pilote
from .router import Router
from .sandbox import Sandbox
from .tools import Toolbox

HERE = Path(__file__).resolve().parent.parent
DEMO_SPEC = HERE / "examples" / "calculatrice-rpn" / "SPEC.md"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="agentpilote", description="Agent IA local : orchestrateur + Pilote")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("demo", help="lance le projet d'exemple")
    d.add_argument("-o", "--out", default="demo_output")
    r = sub.add_parser("run", help="mène un projet à partir d'un cahier des charges")
    r.add_argument("spec")
    r.add_argument("-o", "--out", required=True)
    c = sub.add_parser("chat", help="une demande, routée par l'orchestrateur")
    c.add_argument("message")
    c.add_argument("-o", "--out", default="chat_workspace")
    sub.add_parser("check", help="teste la connexion au modèle")
    for p in (d, r):
        p.add_argument("--attempts", type=int, default=3)
        p.add_argument("--turns", type=int, default=25)
    args = ap.parse_args(argv)

    router = Router.from_env()

    if args.cmd == "check":
        msg = router.fast.chat([{"role": "user", "content": "Réponds juste : OK"}])
        print(f"{router.fast.name} → {(msg.get('content') or '').strip()[:200]}")
        return 0

    if args.cmd == "chat":
        route = router.route(args.message)
        print(f"[orchestrateur] modèle : {route.llm.name} ({route.reason})")
        out = Path(args.out)
        toolbox = Toolbox(out, Sandbox(out))
        res = run_agent(route.llm, STEP_SYSTEM.format(extra=""), route.text, toolbox, on_event=print)
        print("\n" + res.summary)
        return 0

    spec_path = DEMO_SPEC if args.cmd == "demo" else Path(args.spec)
    spec = spec_path.read_text()
    pilote = Pilote(router, Path(args.out), max_attempts=args.attempts, max_turns=args.turns)
    report = pilote.run(spec)
    return 0 if report.success else 1


if __name__ == "__main__":
    sys.exit(main())
