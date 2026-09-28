"""Rule: a write into ``MEMORY/KNOWLEDGE/`` must carry a ``type:`` line in its
frontmatter, or the archive stops being queryable and becomes a folder of notes.

Falsifier: a knowledge write whose content has no ``type:`` producing no ask, or
one with typed frontmatter producing one.
"""

from __future__ import annotations

import re

from .. import surfaces
from .. import util

_TYPE = re.compile(r"^\s*type\s*:\s*\S+", re.IGNORECASE | re.MULTILINE)
#: Only the frontmatter counts, so look at the head of the content.
_HEAD_LINES = 30


def has_type(content: str) -> bool:
    head = "\n".join(str(content or "").split("\n")[:_HEAD_LINES])
    return bool(_TYPE.search(head))


def run(event: dict, ctx) -> dict | None:
    if not util.is_write(event):
        return None
    path = util.file_path(event)
    if not path:
        return None
    if surfaces.memory_kind(ctx, path) != "knowledge":
        return None
    if has_type(util.content(event)):
        return None
    return util.ask(
        "knowledge write with no `type:` frontmatter: %s. Use "
        "`python -m kaios memory knowledge add --title … --body …` so the note stays typed."
        % surfaces.relative(ctx, path)
    )
