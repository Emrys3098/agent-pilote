"""Tests sans modèle : un faux LLM scripté rejoue des réponses déterministes."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agentpilote.agent import run_agent
from agentpilote.llm import LLM
from agentpilote.pilote import Pilote, Step, parse_plan
from agentpilote.router import Router
from agentpilote.sandbox import Sandbox
from agentpilote.tools import Toolbox


def call(name: str, **args) -> dict:
    return {"id": f"c-{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


class FakeLLM(LLM):
    """Rejoue une liste de réponses ; une fonction peut aussi construire la réponse."""

    def __init__(self, name: str, script: list):
        super().__init__("http://fake", name)
        self.script = list(script)
        self.seen: list[list[dict]] = []

    def chat(self, messages, tools=None):
        self.seen.append(list(messages))
        self.usage.calls += 1
        item = self.script.pop(0)
        return item(messages) if callable(item) else item


def tool_msg(*calls) -> dict:
    return {"role": "assistant", "content": "", "tool_calls": list(calls)}


class TempDir(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="agentpilote-test-"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class TestPlanParsing(unittest.TestCase):
    def test_plan_inside_think_and_fences(self):
        text = '<think>je réfléchis {pas du json}</think>\n```json\n{"steps":[{"title":"A","goal":"g","check":"true"}]}\n```'
        steps = parse_plan(text)
        self.assertEqual([s.title for s in steps], ["A"])

    def test_garbage_gives_empty_plan(self):
        self.assertEqual(parse_plan("pas de plan ici"), [])


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.router = Router(FakeLLM("rapide", []), FakeLLM("profond", []))

    def test_default_fast(self):
        self.assertEqual(self.router.route("bonjour").llm.name, "rapide")

    def test_tags(self):
        r = self.router.route("!!deep calcule 2+2")
        self.assertEqual((r.llm.name, r.text), ("profond", "calcule 2+2"))
        self.assertEqual(self.router.route("!!fast pourquoi ?").llm.name, "rapide")

    def test_keyword_and_length(self):
        self.assertEqual(self.router.route("Pourquoi le ciel est bleu ?").llm.name, "profond")
        self.assertEqual(self.router.route("x" * 2000).llm.name, "profond")


class TestToolbox(TempDir):
    def test_path_escape_refused(self):
        tb = Toolbox(self.dir, Sandbox(self.dir))
        self.assertIn("refusé", tb.call("write_file", {"path": "../evil.txt", "content": "x"}))
        self.assertFalse((self.dir.parent / "evil.txt").exists())

    def test_write_read_list(self):
        tb = Toolbox(self.dir, Sandbox(self.dir))
        tb.call("write_file", {"path": "a/b.txt", "content": "salut"})
        self.assertEqual(tb.call("read_file", {"path": "a/b.txt"}), "salut")
        self.assertIn("a/b.txt", tb.call("list_files", {}))


@unittest.skipUnless(shutil.which("bwrap"), "bwrap absent")
class TestSandbox(TempDir):
    def test_no_network_and_readonly_system(self):
        sb = Sandbox(self.dir)
        self.assertFalse(sb.run("python3 -c \"import socket; socket.create_connection(('1.1.1.1', 53), 2)\"").ok)
        self.assertFalse(sb.run("touch /usr/agentpilote-test").ok)
        self.assertTrue(sb.run("echo ok > fichier && cat fichier").ok)

    def test_home_is_hidden(self):
        sb = Sandbox(self.dir)
        res = sb.run(f"ls {Path.home()}")
        self.assertNotIn(".bashrc", res.output)


class TestAgentLoop(TempDir):
    def test_nudge_then_finish(self):
        llm = FakeLLM("m", [
            {"role": "assistant", "content": "Je vais le faire."},
            tool_msg(call("write_file", path="x.txt", content="1")),
            tool_msg(call("finish", summary="x.txt créé")),
        ])
        res = run_agent(llm, "sys", "tâche", Toolbox(self.dir, Sandbox(self.dir)))
        self.assertTrue(res.finished)
        self.assertEqual(res.summary, "x.txt créé")
        self.assertTrue((self.dir / "x.txt").exists())


class TestPilote(TempDir):
    def test_full_project_with_retry_and_escalation(self):
        good_module = "def add(a, b):\n    return a + b\n"
        bad_module = "def add(a, b):\n    return a - b\n"
        test_file = ("import unittest\nfrom mod import add\n\n"
                     "class T(unittest.TestCase):\n    def test_add(self):\n"
                     "        self.assertEqual(add(2, 3), 5)\n")
        plan = {"role": "assistant", "content": json.dumps({"steps": [
            {"title": "Tests", "goal": "écrire test_mod.py", "check": "test -f test_mod.py"},
            {"title": "Module", "goal": "écrire mod.py", "check": "python3 -m unittest -q"},
        ]})}
        fast = FakeLLM("rapide", [
            plan,
            # étape 1
            tool_msg(call("write_file", path="test_mod.py", content=test_file)),
            tool_msg(call("finish", summary="tests écrits")),
            # étape 2, tentatives 1 et 2 : module faux
            tool_msg(call("write_file", path="mod.py", content=bad_module)),
            tool_msg(call("finish", summary="module écrit")),
            tool_msg(call("write_file", path="mod.py", content=bad_module)),
            tool_msg(call("finish", summary="module corrigé ?")),
        ])

        def deep_fix(messages):
            # le modèle profond reçoit l'erreur du contrôle et la passation de l'étape 1
            task = messages[1]["content"]
            assert "tests écrits" in task and "FAILED" in task, task
            return tool_msg(call("write_file", path="mod.py", content=good_module))

        deep = FakeLLM("profond", [deep_fix, tool_msg(call("finish", summary="addition corrigée"))])
        pilote = Pilote(Router(fast, deep), self.dir, max_attempts=3, escalate_after=2, verbose=False)
        report = pilote.run("Une fonction add testée.")

        self.assertTrue(report.success)
        s1, s2 = report.steps
        self.assertEqual((s1.status, s1.attempts, s1.model), ("réussie", 1, "rapide"))
        self.assertEqual((s2.status, s2.attempts, s2.model), ("réussie", 3, "profond"))
        self.assertIn("addition corrigée", (self.dir / "PASSATION.md").read_text())
        self.assertIn("succès", (self.dir / "RAPPORT.md").read_text())

    def test_fresh_context_per_step(self):
        steps = [Step("A", "a", "true"), Step("B", "b", "true")]
        fast = FakeLLM("rapide", [
            tool_msg(call("finish", summary="résumé A")),
            tool_msg(call("finish", summary="résumé B")),
        ])
        Pilote(Router(fast), self.dir, verbose=False).run("spec", steps=steps)
        second_step_context = fast.seen[1]
        self.assertEqual(len(second_step_context), 2)  # système + tâche : aucun historique de l'étape A
        self.assertIn("résumé A", second_step_context[1]["content"])

    def test_model_timeout_is_a_failed_attempt_not_a_crash(self):
        def blocked(_messages):
            raise RuntimeError("pas de réponse du modèle après 900 s")
        steps = [Step("A", "a", "test -f a.txt")]
        fast = FakeLLM("rapide", [
            blocked,
            tool_msg(call("write_file", path="a.txt", content="ok")),
            tool_msg(call("finish", summary="a.txt créé")),
        ])
        report = Pilote(Router(fast), self.dir, max_attempts=2, verbose=False).run("spec", steps=steps)
        self.assertTrue(report.success)
        self.assertEqual(report.steps[0].attempts, 2)
        self.assertIn("interrompue", fast.seen[1][1]["content"])  # la 2e tentative sait pourquoi

    def test_stops_on_failed_step(self):
        steps = [Step("A", "a", "false"), Step("B", "b", "true")]
        fast = FakeLLM("rapide", [tool_msg(call("finish", summary="?"))] * 2)
        report = Pilote(Router(fast), self.dir, max_attempts=2, verbose=False).run("spec", steps=steps)
        self.assertFalse(report.success)
        self.assertEqual([s.status for s in report.steps], ["échouée", "à faire"])


if __name__ == "__main__":
    unittest.main()
