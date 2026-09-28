"""The ledger: the shipped version number and the append-only change registry.

``SYSTEM/VERSION`` in the checkout is the one place the version lives. Every bump
and every recorded change appends a line to ``MEMORY/STATE/ledger.jsonl`` so the
history survives outside git.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import version_file_candidates
from .paths import DOCTRINE_DIR, Paths, doctrine_candidates

PARTS = ("patch", "minor", "major")
_SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def version_file(paths: Paths | None = None, root: Path | str | None = None) -> Path:
    """Where VERSION lives: an explicit root, then the repo, then the package."""
    if root is not None:
        base = Path(root)
        for candidate in _under(base):
            if candidate.is_file():
                return candidate
        return base / DOCTRINE_DIR / "VERSION"

    resolved = paths or Paths.resolve()
    if resolved.repo is not None:
        for candidate in _under(resolved.repo):
            if candidate.is_file():
                return candidate
    for candidate in version_file_candidates():
        if candidate.is_file():
            return candidate
    if resolved.repo is not None:
        return resolved.repo / DOCTRINE_DIR / "VERSION"
    return version_file_candidates()[0]


def _under(base: Path) -> list[Path]:
    """VERSION locations under one root: the doctrine tree, then flat."""
    return [candidate / "VERSION" for candidate in doctrine_candidates(base)] + [base / "VERSION"]


def version(paths: Paths | None = None, root: Path | str | None = None) -> str:
    path = version_file(paths, root)
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return "0.0.0"
    return text.splitlines()[0].strip() if text else "0.0.0"


def bump(
    part: str = "patch",
    paths: Paths | None = None,
    root: Path | str | None = None,
    summary: str | None = None,
) -> dict:
    """Raise the version and append the bump to the registry."""
    normalized = str(part or "patch").strip().lower()
    if normalized not in PARTS:
        raise ValueError("part must be one of %s" % ", ".join(PARTS))

    resolved = paths or Paths.resolve()
    path = version_file(resolved, root)
    previous = version(resolved, root)
    match = _SEMVER_RE.match(previous)
    if not match:
        raise ValueError("version %r is not major.minor.patch" % previous)

    major, minor, patch = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    if normalized == "major":
        major, minor, patch = major + 1, 0, 0
    elif normalized == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = "%d.%d.%d" % (major, minor, patch)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new + "\n", encoding="utf-8", newline="\n")

    entry = record(
        "version",
        summary or ("%s bump %s -> %s" % (normalized, previous, new)),
        {"part": normalized, "previous": previous, "version": new, "file": str(path)},
        paths=resolved,
    )
    return {"previous": previous, "version": new, "file": str(path), "entry": entry}


def record(kind: str, summary: str, meta: dict | None = None, paths: Paths | None = None) -> dict:
    """Append one change to the registry."""
    resolved = paths or Paths.resolve()
    clean_kind = str(kind or "").strip().lower()
    if not clean_kind:
        raise ValueError("record needs a kind")
    clean_summary = str(summary or "").strip()
    if not clean_summary:
        raise ValueError("record needs a summary")

    entry = {
        "ts": now_iso(),
        "kind": clean_kind,
        "summary": clean_summary,
        "version": version(resolved),
        "meta": meta or {},
    }
    resolved.ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved.ledger, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def log(limit: int = 20, paths: Paths | None = None) -> list[dict]:
    """The most recent registry entries, newest first."""
    resolved = paths or Paths.resolve()
    if not resolved.ledger.is_file():
        return []
    out: list[dict] = []
    try:
        raw = resolved.ledger.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict):
            out.append(entry)
    out.reverse()
    if limit is not None and limit >= 0:
        out = out[:limit]
    return out
