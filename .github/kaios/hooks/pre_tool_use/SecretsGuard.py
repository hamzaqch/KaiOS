"""Rule: a tool call whose command or content carries a credential-shaped value is
denied, because a secret written into a tracked file or a transcript is a secret
that has to be rotated.

Falsifier: a fixture payload containing each pattern below must be denied, and a
payload with no secret must pass silently.
"""

from __future__ import annotations

import re

from .. import util

#: ``(name, pattern)`` — shapes, not values. Nothing here is a real credential.
PATTERNS: tuple = (
    ("aws access key id", r"AKIA[0-9A-Z]{16}"),
    ("github personal access token", r"ghp_[A-Za-z0-9]{36}"),
    ("databricks personal access token", r"dapi[0-9a-f]{32}"),
    ("private key block", r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP) PRIVATE KEY-----"),
    ("model provider api key", r"sk-[A-Za-z0-9]{20,}"),
    ("slack token", r"xox[bpasr]-[A-Za-z0-9-]{8,}"),
)

_COMPILED = tuple((name, re.compile(pattern)) for name, pattern in PATTERNS)


def scan(text: str) -> list:
    """Names of every secret shape present in this text."""
    found: list = []
    if not text:
        return found
    for name, pattern in _COMPILED:
        if pattern.search(text) and name not in found:
            found.append(name)
    return found


def run(event: dict, ctx) -> dict | None:
    blob = "\n".join(part for part in (util.command(event), util.content(event)) if part)
    found = scan(blob)
    if not found:
        return None
    return util.deny(
        "secret pattern: %s. Put the value in an environment variable and reference its name."
        % ", ".join(found)
    )
