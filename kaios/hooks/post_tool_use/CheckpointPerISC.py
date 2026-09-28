"""Rule: when an ISA write closes a claim, that claim gets its own commit, so the
evidence for it always has something to point at.

Falsifier: closing a claim in a git repo leaving no new commit, or this hook
raising outside a repo or when ``git`` is absent.
"""

from __future__ import annotations

import shutil
import subprocess

from .. import claims
from .. import util

#: Longest claim text carried into the commit subject.
SUBJECT_LIMIT = 60
_TIMEOUT = 20


def _git(repo, arguments: list) -> tuple:
    """Run one git command with an argument array. Never uses a shell."""
    executable = shutil.which("git")
    if executable is None:
        return False, "git is not on PATH"
    try:
        completed = subprocess.run(  # noqa: S603 - argument array, no shell
            [executable] + [str(item) for item in arguments],
            cwd=str(repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout or "").strip()
    return True, (completed.stdout or "").strip()


def run(event: dict, ctx) -> dict | None:
    target = claims.isa_target(event)
    if target is None:
        return None
    if ctx.repo is None or not (ctx.repo / ".git").exists():
        return None
    try:
        target.resolve().relative_to(ctx.repo.resolve())
    except (OSError, ValueError):
        return None

    _, fresh = claims.newly_checked(ctx, target)
    if not fresh:
        return None
    if shutil.which("git") is None:
        return None

    added, note = _git(ctx.repo, ["add", "--", str(target)])
    if not added:
        return None

    made: list = []
    for claim in fresh:
        subject = "%s closed: %s" % (claim.id, util.clip(claim.text, SUBJECT_LIMIT))
        ok, note = _git(ctx.repo, ["commit", "-m", subject, "--", str(target)])
        if ok:
            made.append(claim.id)
            continue
        if "nothing to commit" in (note or "").lower():
            break
    if not made:
        return None
    return util.context("🔖 Checkpoint: committed %s." % ", ".join(made))
