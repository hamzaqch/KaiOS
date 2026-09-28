"""Rule: every write under ``MEMORY/`` is named in the response, so what memory
gained this turn is visible rather than inferred.

Falsifier: a knowledge write producing no line, or a write outside memory
producing one.
"""

from __future__ import annotations

from .. import surfaces
from .. import util

#: Memory kinds worth reporting; state and observability churn every turn.
REPORTED: tuple = ("knowledge", "capture", "reflection", "incident", "work")


def run(event: dict, ctx) -> dict | None:
    if not util.is_write(event):
        return None
    path = util.file_path(event)
    if not path:
        return None
    kind = surfaces.memory_kind(ctx, path)
    if kind not in REPORTED:
        return None
    return util.context("🧠 MEMORY: %s +1 %s" % (kind, surfaces.relative(ctx, path)))
