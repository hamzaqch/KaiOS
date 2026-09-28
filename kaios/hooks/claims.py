"""Which claims this session just closed, computed once per hook run.

Rule: the checkpoint hook and the verification gate must see the same set of
newly-closed claims, so the comparison against the session snapshot happens once
and is cached on the context rather than recomputed per hook.
Falsifier: the commit hook committing a claim the gate did not grade, or the other
way round, in one PostToolUse run.
"""

from __future__ import annotations

from pathlib import Path

from .. import isa as isa_mod
from . import state
from . import util

#: Session state key holding ``{isa path: [checked claim ids]}``.
KEY = "checked"


def isa_target(event: dict):
    """The ISA this tool call wrote, or ``None``."""
    path = util.file_path(event)
    if not path:
        return None
    if not util.posix(path).lower().endswith("isa.md"):
        return None
    target = Path(path)
    return target if target.is_file() else None


def newly_checked(ctx, isa_path):
    """``(parsed ISA, [claims closed since the snapshot])``; snapshot updated once.

    The first call for a path records the snapshot and reports nothing new, so a
    session that opens on an ISA with closed claims does not re-commit them.
    """
    key = "newly_checked:%s" % util.posix(isa_path)
    if key in ctx.scratch:
        return ctx.scratch[key]

    try:
        parsed = isa_mod.parse(isa_path)
    except (OSError, ValueError):
        ctx.scratch[key] = (None, [])
        return ctx.scratch[key]

    closed = [claim for claim in parsed.isc() if claim.checked and not claim.dropped]
    snapshots = state.get(ctx.paths, ctx.session_id, KEY, {}) or {}
    if not isinstance(snapshots, dict):
        snapshots = {}
    stored = snapshots.get(util.posix(isa_path))
    if isinstance(stored, list):
        known = set(str(item) for item in stored)
        fresh = [claim for claim in closed if claim.id not in known]
    else:
        fresh = []

    snapshots[util.posix(isa_path)] = [claim.id for claim in closed]
    state.put(ctx.paths, ctx.session_id, KEY, snapshots)

    ctx.scratch[key] = (parsed, fresh)
    return ctx.scratch[key]
