"""Rule: an ISA that reached ``complete`` with no reflection captured for its slug
today gets one prompt to capture what the run taught, because a closed run with no
reflection loses the only thing that was expensive to learn.

Falsifier: a complete ISA with no reflection producing no prompt, or one with a
reflection captured today producing one.
"""

from __future__ import annotations

import json

from ... import isa as isa_mod
from ... import memory as memory_mod
from .. import util


def _captured_today(ctx, slug: str) -> bool:
    today = (ctx.now or util.now_iso())[:10]
    try:
        records = memory_mod.captures(ctx.paths, kind="reflection")
    except (OSError, ValueError):
        return False
    for record in records:
        if str(record.get("ts") or "")[:10] != today:
            continue
        blob = "%s %s" % (record.get("text") or "", json.dumps(record.get("meta") or {}, default=str))
        if slug.lower() in blob.lower():
            return True
    return False


def run(event: dict, ctx) -> dict | None:
    if ctx.active_isa is None:
        return None
    try:
        parsed = isa_mod.parse(ctx.active_isa)
    except (OSError, ValueError):
        return None
    if not parsed.complete:
        return None
    slug = parsed.slug
    if _captured_today(ctx, slug):
        return None
    return util.context(
        "%s is complete and has no reflection captured today. Capture one: "
        "`python -m kaios memory capture --kind reflection --text \"%s: what the run taught\"`."
        % (slug, slug)
    )
