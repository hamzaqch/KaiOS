"""Rule: a session is told when the tree it is about to work in is missing the
hook registry or the doctrine directory, rather than discovering it mid-task.

Falsifier: a home with no doctrine copy and a repo with no registry producing no
line.
"""

from __future__ import annotations

from .. import util


def _registry(ctx):
    if ctx.repo is not None:
        candidate = ctx.repo / ".github" / "hooks" / "kaios.json"
        if candidate.is_file():
            return candidate
    return ctx.paths.hooks_json if ctx.paths.hooks_json.is_file() else None


def run(event: dict, ctx) -> dict | None:
    problems: list = []
    if _registry(ctx) is None:
        problems.append("no hook registry (.github/hooks/kaios.json)")
    doctrine = ctx.doctrine
    if not (doctrine / "ALGORITHM").is_dir():
        problems.append("no doctrine tree at %s" % util.display(doctrine, ctx.repo))
    if not problems:
        return None
    return util.context(
        "⚠️ Integrity: %s. Run `python -m kaios doctor` before trusting the setup."
        % "; ".join(problems)
    )
