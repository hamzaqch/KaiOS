"""Rule: a shell command that destroys a filesystem root, a home directory, a
protected branch's history, a database object, or a Databricks asset is denied,
and a production deploy or an unpinned remote-script install is asked about.

Falsifier: the table in ``.github/tests/test_hooks.py`` — every deny row must deny, every
ask row must ask, and `git status`, `ls`, `python -m unittest` must pass silently.
"""

from __future__ import annotations

import re

from .. import util

#: ``(pattern, decision, reason)``. Evaluated case-insensitively, in order.
RULES: tuple = (
    (
        r"\brm\s+(?:-[a-z]*\s+)*-[a-z]*r[a-z]*f[a-z]*\s+/(?:\s|$|\*)",
        "deny",
        "recursive force delete of the filesystem root",
    ),
    (
        r"\brm\s+(?:-[a-z]*\s+)*-[a-z]*f[a-z]*r[a-z]*\s+/(?:\s|$|\*)",
        "deny",
        "recursive force delete of the filesystem root",
    ),
    (
        r"\brm\s+(?:-[a-z]*\s+)*-[a-z]*r[a-z]*f?[a-z]*\s+(?:~|\$HOME|\$\{HOME\})(?:/\s*|\s|$)",
        "deny",
        "recursive delete of the home directory",
    ),
    (
        r"remove-item(?=[^\n]*-recurse)(?=[^\n]*-force)[^\n]*[a-z]:[\\/]\s*(?:['\"]|$)",
        "deny",
        "recursive force delete of a drive root",
    ),
    (
        r"\bgit\s+push\b(?=[^\n]*(?:--force\b|\s-f\b))(?=[^\n]*\b(?:main|master)\b)",
        "deny",
        "force push to a protected branch rewrites shared history",
    ),
    (r"\bdrop\s+(?:table|schema|database)\b", "deny", "destructive schema statement"),
    (r"\bdatabricks\s+workspace\s+delete\b", "deny", "workspace delete is irreversible"),
    (r"\bdatabricks\s+jobs\s+delete\b", "deny", "job delete is irreversible"),
    (
        r"\bgit\s+reset\s+--hard\s+origin\b",
        "deny",
        "hard reset to the remote discards local commits",
    ),
    (
        r"\bdatabricks\s+bundle\s+deploy\b(?=[^\n]*(?:-t\s+prod|--target\s+prod|\bproduction\b))",
        "ask",
        "production bundle deploy",
    ),
    (r"\bgit\s+push\b", "ask", "push publishes to a shared remote"),
    (
        r"\bpip\s+install\b[^\n]*(?:https?://|\bgit\+)",
        "ask",
        "pip install from a URL runs unpinned remote code",
    ),
    (
        r"\b(?:curl|wget)\b[^\n]*\|\s*(?:sudo\s+)?(?:ba|z|d)?sh\b",
        "ask",
        "piping a downloaded script into a shell",
    ),
    (
        r"\b(?:curl|wget|iwr|invoke-webrequest)\b[^\n]*\|\s*iex\b",
        "ask",
        "piping a downloaded script into the shell",
    ),
)

_COMPILED = tuple((re.compile(pattern, re.IGNORECASE), decision, reason) for pattern, decision, reason in RULES)


def evaluate(command: str) -> dict | None:
    """The decision for one command string, or ``None`` when nothing matches."""
    text = str(command or "")
    if not text.strip():
        return None
    denies: list = []
    asks: list = []
    for pattern, decision, reason in _COMPILED:
        if pattern.search(text):
            (denies if decision == "deny" else asks).append(reason)
    if denies:
        return util.deny("%s (%s)" % ("; ".join(dict.fromkeys(denies)), util.clip(text, 120)))
    if asks:
        return util.ask("%s (%s)" % ("; ".join(dict.fromkeys(asks)), util.clip(text, 120)))
    return None


def run(event: dict, ctx) -> dict | None:
    return evaluate(util.command(event))
