"""Rule: every write to an ISA is mirrored into ``MEMORY/STATE/work.json`` at once,
and a change in the derived phase or progress prints the Algorithm strip.

Falsifier: an ISA write leaving the registry entry stale, or a progress change
printing no strip.
"""

from __future__ import annotations

import json

from ... import isa as isa_mod
from .. import claims
from .. import util


def _registry_entry(ctx, slug: str) -> dict:
    try:
        data = json.loads(ctx.paths.work_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entries = data.get("isas") if isinstance(data, dict) else None
    if not isinstance(entries, dict):
        return {}
    entry = entries.get(slug)
    return entry if isinstance(entry, dict) else {}


def run(event: dict, ctx) -> dict | None:
    target = claims.isa_target(event)
    if target is None:
        return None
    try:
        parsed = isa_mod.parse(target)
    except (OSError, ValueError):
        return None

    before = _registry_entry(ctx, parsed.slug)
    try:
        entry = isa_mod.sync(ctx.paths, target)
    except (OSError, ValueError):
        return None

    phase = str(entry.get("phase") or "unknown")
    progress = str(entry.get("progress") or "")
    was = (str(before.get("phase") or ""), str(before.get("progress") or ""))
    if was == (phase, progress):
        return None
    return util.context("════ KaiOS | Algorithm | %s %s ════" % (phase, progress))
