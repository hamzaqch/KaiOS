"""Rule: a prompt whose subject is an unresolved referent — "the file", "that
thing" — with no path or name attached is sent back for resolution before work
starts, because building on the wrong reading wastes the whole turn.

Falsifier: "fix the file" producing no reminder, or the same prompt with a path
producing one.
"""

from __future__ import annotations

import re

from .. import util

#: Referents whose reading changes what gets built.
REFERENTS: tuple = (
    r"\bthe file\b",
    r"\bthe doc\b",
    r"\bthe document\b",
    r"\bthat thing\b",
    r"\bthe one we discussed\b",
    r"\bthat one\b",
    r"\bthe script\b",
    r"\bthe usual\b",
)

_REFERENT = re.compile("|".join(REFERENTS), re.IGNORECASE)
#: Anything that resolves a referent: a path, an extension, or a quoted name.
_RESOLVED = re.compile(
    r"(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)"
    r"|(?:[A-Za-z]:[\\/])"
    r"|(?:\.(?:py|md|ps1|json|ya?ml|sql|txt|csv|ipynb|toml|cfg|ini)\b)"
    r"|(?:`[^`]+`)"
    r"|(?:\"[^\"]{3,}\")",
    re.IGNORECASE,
)


def run(event: dict, ctx) -> dict | None:
    text = util.prompt(event)
    if not text:
        return None
    match = _REFERENT.search(text)
    if not match:
        return None
    if _RESOLVED.search(text):
        return None
    return util.context(
        "Unresolved referent: %r has no path or name in this message. Resolve it or ask — "
        "at most three questions, each one you cannot answer from the repo, and `proceed` "
        "accepts your stated defaults." % match.group(0).strip()
    )
