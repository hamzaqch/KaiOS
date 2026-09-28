"""The hook wrapper must work from ANY workspace, not only the KaiOS checkout.

Regression for the first field report: in a work repo scaffolded by
Init-Workspace.ps1 the wrapper ran ``python -m kaios.hooks`` with no way to
import ``kaios``, wrote the ModuleNotFoundError to stderr, and the chat harness
treated the erroring hook as a denial of every command.

Falsifier: from a temp workspace with no ``kaios`` package, with only
``KAIOS_REPO`` pointing at the checkout, a force-push payload must come back as
a real ``deny`` on stdout with zero bytes on stderr.

Both wrappers are held to that contract. ``kaios.ps1`` is what Windows runs, and
``kaios.sh`` is what the Copilot CLI engine runs on a non-Windows host; each case
skips when its host is unavailable.
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

# The framework lives under .github, so this file is two levels below the
# checkout root: <repo>/.github/tests/<this file>.
REPO = Path(__file__).resolve().parents[2]
FRAMEWORK = REPO / ".github"
PACKAGE = FRAMEWORK / "kaios"
WRAPPER = FRAMEWORK / "hooks" / "kaios.ps1"
SHELL_WRAPPER = FRAMEWORK / "hooks" / "kaios.sh"


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

    def _run(self, payload: dict, env_extra: dict, event: str = "PreToolUse") -> tuple[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in ("KAIOS_REPO", "PYTHONPATH")}
        env["KAIOS_HOME"] = str(self.home)
        env["HOME"] = str(self.tmp)
        env.update(env_extra)
        proc = subprocess.run(
            [self.ps, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
             str(self.workspace / ".github" / "hooks" / "kaios.ps1"), event],
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

    def test_kaios_repo_may_name_the_framework_directory(self) -> None:
        """KAIOS_REPO is accepted as the checkout root or as its .github directory."""
        out, err = self._run(
            {"hook_event_name": "PreToolUse", "tool_name": "runCommands",
             "tool_input": {"command": "git push --force origin main"}},
            {"KAIOS_REPO": str(FRAMEWORK)},
        )
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_a_copilot_cli_payload_and_event_name_deny(self) -> None:
        """The wrapper is handed the camelCase event name the CLI engine uses."""
        out, err = self._run(
            {"toolName": "bash", "toolArgs": {"command": "git push --force origin main"}},
            {"KAIOS_REPO": str(REPO)},
            event="preToolUse",
        )
        decision = json.loads(out)
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_deny_reaches_the_runner_via_home_lib(self) -> None:
        lib = self.home / "lib" / "kaios"
        shutil.copytree(PACKAGE, lib, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        out, err = self._run(
            {"hook_event_name": "PreToolUse", "tool_name": "runCommands",
             "tool_input": {"command": "git push --force origin main"}},
            {},
        )
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_deny_reaches_the_runner_from_beside_the_wrapper(self) -> None:
        """The whole framework in one folder: no KAIOS_REPO, no KAIOS_HOME lib.

        A work repo scaffolded by Init-Workspace.ps1 carries .github/kaios beside
        .github/hooks, so the wrapper's own parent directory IS the import root.
        """
        shutil.copytree(
            PACKAGE,
            self.workspace / ".github" / "kaios",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
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


class ShellWrapperTests(unittest.TestCase):
    """The POSIX wrapper holds the same contract as the PowerShell one.

    The Copilot CLI engine runs the ``bash`` command line of a registry entry on
    a non-Windows host, and it fails a preToolUse hook CLOSED: an error, a crash
    or a non-zero exit denies the tool call. So the two things asserted here are
    the two that matter — a real decision on stdout, and nothing on stderr.
    """

    def setUp(self) -> None:
        self.sh = shutil.which("sh")
        if not self.sh:
            self.skipTest("no POSIX shell available")
        self.tmp = Path(tempfile.mkdtemp())
        self.workspace = self.tmp / "work-repo"
        (self.workspace / ".github" / "hooks").mkdir(parents=True)
        shutil.copy2(SHELL_WRAPPER, self.workspace / ".github" / "hooks" / "kaios.sh")
        self.home = self.tmp / "kaios-home"
        self.home.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, payload: dict, env_extra: dict, event: str = "preToolUse") -> tuple[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in ("KAIOS_REPO", "PYTHONPATH")}
        env["KAIOS_HOME"] = str(self.home)
        env["HOME"] = str(self.tmp)
        env.update(env_extra)
        proc = subprocess.run(
            [self.sh, ".github/hooks/kaios.sh", event],
            input=json.dumps(payload), capture_output=True, text=True, encoding="utf-8",
            cwd=str(self.workspace), env=env, timeout=60,
        )
        self.assertEqual(proc.returncode, 0)
        return proc.stdout, proc.stderr

    def test_a_copilot_cli_payload_denies_in_both_dialects(self) -> None:
        out, err = self._run(
            {"toolName": "bash", "toolArgs": {"command": "git push --force origin main"},
             "cwd": str(self.workspace)},
            {"KAIOS_REPO": str(REPO)},
        )
        decision = json.loads(out)
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertEqual(decision["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(err, "")

    def test_kaios_repo_may_name_the_framework_directory(self) -> None:
        """KAIOS_REPO is accepted as the checkout root or as its .github directory."""
        out, err = self._run(
            {"toolName": "bash", "toolArgs": {"command": "git push --force origin main"}},
            {"KAIOS_REPO": str(FRAMEWORK)},
        )
        self.assertEqual(json.loads(out)["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_deny_reaches_the_runner_via_home_lib(self) -> None:
        lib = self.home / "lib" / "kaios"
        shutil.copytree(PACKAGE, lib, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        out, err = self._run({"toolName": "bash", "toolArgs": {"command": "rm -rf /"}}, {})
        self.assertEqual(json.loads(out)["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_deny_reaches_the_runner_from_beside_the_wrapper(self) -> None:
        """The whole framework in one folder: no KAIOS_REPO, no KAIOS_HOME lib."""
        shutil.copytree(
            PACKAGE,
            self.workspace / ".github" / "kaios",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        out, err = self._run(
            {"toolName": "bash", "toolArgs": {"command": "git push --force origin main"}}, {}
        )
        self.assertEqual(json.loads(out)["permissionDecision"], "deny")
        self.assertEqual(err, "")

    def test_missing_package_logs_and_never_writes_stderr(self) -> None:
        out, err = self._run({"toolName": "bash"}, {})
        self.assertEqual(json.loads(out), {"continue": True})
        self.assertEqual(err, "")
        log = self.home / "MEMORY" / "OBSERVABILITY" / "hook-errors.log"
        self.assertTrue(log.exists())
        self.assertIn("kaios package not found", log.read_text(encoding="utf-8"))

    def test_kill_switch(self) -> None:
        out, err = self._run(
            {"toolName": "bash", "toolArgs": {"command": "git push --force origin main"}},
            {"KAIOS_REPO": str(REPO), "KAIOS_HOOKS_DISABLED": "1"},
        )
        self.assertEqual(json.loads(out), {"continue": True})
        self.assertEqual(err, "")

    def test_an_unknown_event_name_still_answers(self) -> None:
        out, err = self._run({}, {"KAIOS_REPO": str(REPO)}, event="not-an-event")
        self.assertEqual(json.loads(out), {"continue": True})
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
