"""Per-session scratch state under ``MEMORY/STATE/session-<id>.json``.

Rule: a hook that needs to know what the session already saw keeps that in one
JSON file per session, never in module globals, because every hook runs in a
fresh process.
Falsifier: two runs of the same event in separate processes disagreeing about a
counter that ``state.bump`` incremented.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_ID = 64


def sanitize(session_id: str) -> str:
    """A filesystem-safe session id. Windows-safe: no colons, no separators."""
    clean = _SAFE.sub("-", str(session_id or "").strip()).strip("-.")
    return (clean or "unknown")[:_MAX_ID]


def path_for(paths, session_id: str) -> Path:
    return paths.state / ("session-%s.json" % sanitize(session_id))


def load(paths, session_id: str) -> dict:
    target = path_for(paths, session_id)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save(paths, session_id: str, data: dict) -> Path:
    target = path_for(paths, session_id)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(data, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError:
        pass
    return target


def bump(paths, session_id: str, key: str, amount: int = 1) -> int:
    """Increment one counter and return its new value."""
    data = load(paths, session_id)
    try:
        current = int(data.get(key) or 0)
    except (TypeError, ValueError):
        current = 0
    current += amount
    data[key] = current
    save(paths, session_id, data)
    return current


def get(paths, session_id: str, key: str, default=None):
    return load(paths, session_id).get(key, default)


def put(paths, session_id: str, key: str, value) -> None:
    data = load(paths, session_id)
    data[key] = value
    save(paths, session_id, data)
