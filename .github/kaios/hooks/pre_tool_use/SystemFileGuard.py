"""Rule: a write to doctrine or to the machinery that runs the system — the
doctrine tree, ``.github/copilot-instructions.md``, ``.github/hooks/**`` — asks
first, because changing the rules mid-session changes what every later hook does.

Falsifier: a write to a doctrine path returning no ask, or a write to ordinary
source returning one.
"""

from __future__ import annotations

from .. import surfaces
from .. import util

REASON = "doctrine/machinery write"


def run(event: dict, ctx) -> dict | None:
    if not util.is_write(event):
        return None
    path = util.file_path(event)
    if not path:
        return None
    kind = surfaces.classify(ctx, path)
    if kind not in surfaces.GATED:
        return None
    return util.ask(
        "%s: %s (%s). Confirm the change is intended and record it in the ISA log."
        % (REASON, surfaces.relative(ctx, path), kind)
    )
