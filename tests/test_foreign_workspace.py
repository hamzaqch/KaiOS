"""The hook wrapper must work from ANY workspace, not only the KaiOS checkout.

Regression for the first field report: in a work repo scaffolded by
Init-Workspace.ps1 the wrapper ran ``python -m kaios.hooks`` with no way to
import ``kaios``, wrote the ModuleNotFoundError to stderr, and the chat harness
treated the erroring hook as a denial of every command.

Falsifier: from a temp workspace with no ``kaios`` package, with only
``KAIOS_REPO`` pointing at the checkout, a force-push payload must come back as
a real ``deny`` on stdout with zero bytes on stderr. Skipped when no PowerShell
host is available.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WRAPPER = REPO / ".github" / "hooks" / "kaios.ps1"


def _powershell() -> str | None:
    for name in ("pwsh", "powershell"):
        found = shutil.which(name)
        if found:
            return found
    home_pwsh = Path.home() / ".local" / "pwsh" / "pwsh"
    if home_pwsh.exists():
        return str(home_pwsh)
    return None


class ForeignWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ps = _powershell()
        if not self.ps:
            self.skipTest("no PowerShell host available")
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = self.tmp / "work-repo"
        (self.workspace / ".github" / "hooks").mkdir(parents=True)
        shutil.copy2(WRAPPER, self.workspace / ".github" / "hooks" / "kaios.ps1")
        self.home = self.tmp / "kaios-home"
        self.home.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, payload: dict, env_extra: dict) -> tuple[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in ("KAIOS_REPO", "PYTHONPATH")}
        env["KAIOS_HOME"] = str(self.home)
        env["HOME"] = str(self.tmp)
        env.update(env_extra)
        proc = subprocess.run(
            [self.ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(self.workspace / ".github" / "hooks" / "kaios.ps1"), "PreToolUse"],
            input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
            cwd=str(self.workspace), env=env, timeout=60,
        )
        self.assertEqual(proc.returncode, 0)
        return proc.stdout, proc.stderr

    def test_deny_reaches_the_runner_via_kaios_repo(self) -> None:
        out, err = self._run(
            {"hook_event_name": "PreToolUse", "tool_name": "runCommands",
             "tool_input": {"command": "git push --force origin main"}},
            {"KAIOS_REPO": str(REPO)},
        )
        decision = json.loads(out)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_deny_reaches_the_runner_via_home_lib(self) -> None:
        lib = self.home / "lib" / "kaios"
        shutil.copytree(REPO / "kaios", lib, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        out, err = self._run(
            {"hook_event_name": "PreToolUse", "tool_name": "runCommands",
             "tool_input": {"command": "git push --force origin main"}},
            {},
        )
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_missing_package_logs_and_never_writes_stderr(self) -> None:
        out, err = self._run({"hook_event_name": "PreToolUse"}, {})
        self.assertEqual(json.loads(out), {"continue": True})
        self.assertEqual(err, "")
        log = self.home / "MEMORY" / "OBSERVABILITY" / "hook-errors.log"
        self.assertTrue(log.exists())
        self.assertIn("kaios package not found", log.read_text(encoding="utf-8"))

    def test_kill_switch(self) -> None:
        out, err = self._run(
            {"hook_event_name": "PreToolUse", "tool_name": "runCommands",
             "tool_input": {"command": "git push --force origin main"}},
            {"KAIOS_REPO": str(REPO), "KAIOS_HOOKS_DISABLED": "1"},
        )
        self.assertEqual(json.loads(out), {"continue": True})
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
