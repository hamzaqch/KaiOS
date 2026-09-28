"""Rule: a write to an ISA whose ``updated:`` on disk is newer than what this
session last saw asks first, because that is exactly how two sessions overwrite
each other's claims.

Falsifier: a second write after the file changed underneath the session producing
no ask, or the first write to an unseen ISA producing one.
"""

from __future__ import annotations

from ... import isa as isa_mod
from .. import state
from .. import util

#: Session state key holding ``{isa path: updated stamp last seen}``.
KEY = "isa_seen"


def _updated(path) -> str:
    text = util.read_text(path)
    if not text:
        return ""
    frontmatter, _ = isa_mod.parse_frontmatter(text.split("\n"))
    return str(frontmatter.get("updated") or "").strip()


def run(event: dict, ctx) -> dict | None:
    path = util.file_path(event)
    if not path or not util.posix(path).lower().endswith("isa.md"):
        return None
    if not util.is_write(event):
        return None

    key = util.posix(path)
    seen = state.get(ctx.paths, ctx.session_id, KEY, {}) or {}
    if not isinstance(seen, dict):
        seen = {}
    on_disk = _updated(path)
    last = str(seen.get(key) or "")

    seen[key] = on_disk
    state.put(ctx.paths, ctx.session_id, KEY, seen)

    if not last or not on_disk or on_disk <= last:
        return None
    return util.ask(
        "the ISA at %s was updated to %s after this session last read it (%s). Re-read it before "
        "writing, or claims get overwritten." % (util.display(path), on_disk, last)
    )
