"""Rule: the active ISA's rendered state is refreshed to
``MEMORY/STATE/isa-status.md`` at the end of every turn, so its current state is
readable without parsing the file.

Falsifier: a turn with an active ISA leaving no rendered file.
"""

from __future__ import annotations

from ... import isa as isa_mod
from .. import util

#: Where the rendered view lives, relative to ``MEMORY/STATE``.
FILENAME = "isa-status.md"


def run(event: dict, ctx) -> dict | None:
    if ctx.active_isa is None:
        return None
    try:
        markdown = isa_mod.render(isa_mod.parse(ctx.active_isa))
    except (OSError, ValueError):
        return None
    target = ctx.paths.state / FILENAME
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8", newline="\n")
    except OSError:
        return None
    return None
