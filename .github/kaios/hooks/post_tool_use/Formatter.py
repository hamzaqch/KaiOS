"""Rule: a Python file that was just written is formatted by whichever formatter
the machine actually has, and says nothing at all when it has none.

Falsifier: a ``.py`` write with a formatter on PATH producing no line, or a write
with no formatter producing one.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import util

#: ``(executable, argument array before the file)`` in preference order.
FORMATTERS: tuple = (
    ("ruff", ["format"]),
    ("black", ["-q"]),
)
_TIMEOUT = 30


def available() -> tuple:
    """The first formatter present on PATH as ``(executable path, arguments)``."""
    for name, arguments in FORMATTERS:
        found = shutil.which(name)
        if found:
            return found, list(arguments), name
    return None, [], ""


def run(event: dict, ctx) -> dict | None:
    if not util.is_write(event):
        return None
    raw = util.file_path(event)
    if not raw or not util.posix(raw).lower().endswith(".py"):
        return None
    target = Path(raw)
    if not target.is_file():
        return None
    if ctx.repo is not None:
        try:
            target.resolve().relative_to(ctx.repo.resolve())
        except (OSError, ValueError):
            return None

    executable, arguments, name = available()
    if executable is None:
        return None
    try:
        completed = subprocess.run(  # noqa: S603 - argument array, no shell
            [executable] + arguments + [str(target)],
            cwd=str(ctx.repo) if ctx.repo is not None else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=_TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return util.context("🧹 %s could not run on %s: %s" % (name, target.name, exc))
    if completed.returncode != 0:
        return util.context(
            "🧹 %s exited %d on %s: %s"
            % (name, completed.returncode, target.name, util.clip(completed.stderr, 120))
        )
    return util.context("🧹 %s formatted %s." % (name, util.display(target, ctx.repo)))
