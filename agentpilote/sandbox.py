"""Bac à sable d'exécution des commandes de l'agent.

Avec bubblewrap (bwrap, Linux) : le système est monté en lecture seule, seul le
dossier du projet est inscriptible, le réseau est coupé et /home est masqué.
Sans bwrap : repli sur un simple sous-processus confiné au dossier du projet
(moins sûr, signalé clairement).
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT = 6000


@dataclass
class RunResult:
    code: int
    output: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.code == 0 and not self.timed_out

    def short(self) -> str:
        head = "TIMEOUT" if self.timed_out else f"code={self.code}"
        return f"[{head}]\n{self.output}"


class Sandbox:
    def __init__(self, workdir: Path, timeout: float = 120.0, use_bwrap: bool | None = None):
        self.workdir = Path(workdir).resolve()
        self.timeout = timeout
        self.use_bwrap = shutil.which("bwrap") is not None if use_bwrap is None else use_bwrap

    @property
    def kind(self) -> str:
        return "bwrap (réseau coupé, système en lecture seule)" if self.use_bwrap else "sous-processus simple (bwrap absent)"

    def _argv(self, command: str) -> list[str]:
        if not self.use_bwrap:
            return ["bash", "-lc", command]
        argv = [
            "bwrap",
            "--ro-bind", "/", "/",          # tout le système en lecture seule
            "--dev", "/dev",
            "--proc", "/proc",
            "--tmpfs", "/tmp",
        ]
        home = Path.home()
        if home.exists():
            # masque les fichiers personnels ; si le projet est dans /home,
            # seul son dossier est remonté juste après
            argv += ["--tmpfs", str(home)]
        argv += [
            "--bind", str(self.workdir), str(self.workdir),
            "--chdir", str(self.workdir),
            "--unshare-all",                # réseau, PID, IPC... isolés
            "--die-with-parent",
            "--setenv", "HOME", str(self.workdir),
            # sinon un .pyc périmé peut survivre à une réécriture de même taille dans la même seconde
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "bash", "-c", command,
        ]
        return argv

    def run(self, command: str) -> RunResult:
        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                self._argv(command),
                cwd=self.workdir,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or "") + (exc.stderr or "") if isinstance(exc.stdout, str) else ""
            return RunResult(-1, _clip(out), timed_out=True)
        return RunResult(proc.returncode, _clip(proc.stdout + proc.stderr))


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    half = MAX_OUTPUT // 2
    return text[:half] + f"\n[... {len(text) - MAX_OUTPUT} caractères coupés ...]\n" + text[-half:]
