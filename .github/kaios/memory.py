"""Memory: append-only captures, a knowledge archive, and the session hot layer.

Captures are one JSON object per line under ``MEMORY/LEARNING/captures.jsonl``.
Knowledge is markdown with typed frontmatter under ``MEMORY/KNOWLEDGE/``.
Nothing is ever rewritten in place, so a crashed write can only lose the last
line.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import isa as isa_mod
from .paths import Paths

#: Accepted capture kinds. The first six are the set the skills document; the
#: last three are the original core set, kept so nothing already written breaks.
KINDS = (
    "learning",
    "gotcha",
    "decision",
    "preference",
    "probe",
    "incident-seed",
    "reflection",
    "incident",
    "fact",
)

_STALE_DAYS = 14


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    out: list[dict] = []
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


# ---------------------------------------------------------------- capture


def capture(paths: Paths, kind: str, text: str, meta: dict | None = None) -> dict:
    """Append one capture. Raises ValueError on an unknown kind or empty text."""
    normalized = str(kind or "").strip().lower()
    if normalized not in KINDS:
        raise ValueError("kind must be one of %s" % ", ".join(KINDS))
    body = str(text or "").strip()
    if not body:
        raise ValueError("capture text is empty")
    record = {
        "ts": now_iso(),
        "kind": normalized,
        "text": body,
        "meta": meta or {},
    }
    _append_jsonl(paths.captures, record)
    return record


def captures(paths: Paths, limit: int | None = None, kind: str | None = None) -> list[dict]:
    records = _read_jsonl(paths.captures)
    if kind:
        wanted = kind.strip().lower()
        records = [r for r in records if str(r.get("kind") or "").lower() == wanted]
    records.sort(key=lambda r: str(r.get("ts") or ""))
    if limit is not None and limit >= 0:
        records = records[-limit:]
    return records


def reflections(paths: Paths, limit: int | None = None) -> list[dict]:
    """Reflection records hooks drop into ``MEMORY/LEARNING/REFLECTIONS``."""
    records: list[dict] = []
    if paths.reflections.is_dir():
        for path in sorted(paths.reflections.glob("*.jsonl")):
            records.extend(_read_jsonl(path))
    records.sort(key=lambda r: str(r.get("ts") or ""))
    if limit is not None and limit >= 0:
        records = records[-limit:]
    return records


# ---------------------------------------------------------------- search


def search(paths: Paths, query: str, limit: int = 20) -> list[dict]:
    """Case-insensitive substring search over captures, knowledge, and ISA tasks."""
    needle = str(query or "").strip().lower()
    hits: list[dict] = []
    if not needle:
        return hits

    for record in reversed(captures(paths)):
        blob = "%s %s" % (record.get("text") or "", json.dumps(record.get("meta") or {}))
        if needle in blob.lower():
            hits.append(
                {
                    "source": "capture",
                    "kind": record.get("kind"),
                    "ts": record.get("ts"),
                    "text": _clip(str(record.get("text") or "")),
                    "path": str(paths.captures),
                }
            )
            if len(hits) >= limit:
                return hits

    if paths.knowledge.is_dir():
        for path in sorted(paths.knowledge.glob("*.md")):
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if needle not in body.lower():
                continue
            hits.append(
                {
                    "source": "knowledge",
                    "kind": "note",
                    "title": _title_of(body, path),
                    "text": _clip(_first_line(body, needle)),
                    "path": str(path),
                }
            )
            if len(hits) >= limit:
                return hits

    for entry in isa_mod.registry(paths):
        blob = "%s %s %s" % (entry.get("slug"), entry.get("task"), entry.get("path"))
        if needle in blob.lower():
            hits.append(
                {
                    "source": "isa",
                    "kind": entry.get("phase"),
                    "ts": entry.get("updated"),
                    "text": _clip(str(entry.get("task") or entry.get("slug") or "")),
                    "path": str(entry.get("path") or ""),
                }
            )
            if len(hits) >= limit:
                return hits

    return hits


def _clip(text: str, limit: int = 200) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def _first_line(body: str, needle: str) -> str:
    for line in body.split("\n"):
        if needle in line.lower():
            return line.strip()
    return body.split("\n")[0]


def _title_of(body: str, path: Path) -> str:
    fm, start = isa_mod.parse_frontmatter(body.split("\n"))
    if fm.get("title"):
        return str(fm["title"])
    for line in body.split("\n")[start:]:
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem


# ---------------------------------------------------------------- digest


def digest(paths: Paths, since_iso: str | None = None) -> str:
    """Markdown summary of captures, reflections, and ISA state."""
    cutoff = _parse_iso(since_iso) if since_iso else None
    records = captures(paths)
    if cutoff is not None:
        records = [r for r in records if (_parse_iso(str(r.get("ts") or "")) or cutoff) >= cutoff]

    lines = ["# Memory digest", ""]
    lines.append("Generated %s%s." % (now_iso(), " since %s" % since_iso if since_iso else ""))
    lines.append("")

    by_kind: dict = {}
    for record in records:
        by_kind.setdefault(str(record.get("kind") or "unknown"), []).append(record)

    lines += ["## Captures", ""]
    if not records:
        lines += ["- nothing captured in this window", ""]
    else:
        lines += ["| kind | count |", "|---|---|"]
        for kind in sorted(by_kind):
            lines.append("| %s | %d |" % (kind, len(by_kind[kind])))
        lines.append("")
        for kind in sorted(by_kind):
            lines += ["### %s" % kind, ""]
            for record in by_kind[kind][-10:]:
                lines.append("- %s — %s" % (record.get("ts"), _clip(str(record.get("text") or ""))))
            lines.append("")

    reflected = reflections(paths)
    if cutoff is not None:
        reflected = [r for r in reflected if (_parse_iso(str(r.get("ts") or "")) or cutoff) >= cutoff]
    lines += ["## Reflections", ""]
    if reflected:
        for record in reflected[-10:]:
            text = record.get("text") or record.get("summary") or json.dumps(record, sort_keys=True)
            lines.append("- %s — %s" % (record.get("ts"), _clip(str(text))))
    else:
        lines.append("- none recorded")
    lines.append("")

    lines += ["## Work", ""]
    entries = isa_mod.registry(paths)
    if entries:
        lines += ["| slug | phase | progress | open |", "|---|---|---|---|"]
        for entry in entries[:20]:
            lines.append(
                "| %s | %s | %s | %s |"
                % (
                    entry.get("slug"),
                    entry.get("phase"),
                    entry.get("progress"),
                    entry.get("claims_open"),
                )
            )
    else:
        lines.append("- no ISAs registered")
    lines.append("")

    knowledge_count = len(list(paths.knowledge.glob("*.md"))) if paths.knowledge.is_dir() else 0
    lines += ["## Knowledge", "", "- %d note(s) in the archive" % knowledge_count, ""]
    return "\n".join(lines)


def hot_layer(paths: Paths, limit: int = 8) -> str:
    """The short block a SessionStart hook injects. Kept deliberately small."""
    lines: list[str] = []
    active = None
    try:
        active = isa_mod.find_active(paths)
    except OSError:
        active = None

    if active is not None:
        try:
            info = isa_mod.status(isa_mod.parse(active))
            lines.append(
                "Active ISA %s — phase %s, %s done, frontier: %s"
                % (
                    info["slug"],
                    info["phase"] or "unknown",
                    info["counted"],
                    ", ".join(info["frontier"][:5]) or "none",
                )
            )
        except (OSError, ValueError):
            lines.append("Active ISA at %s could not be parsed." % active.name)
    else:
        lines.append("No active ISA: articulate done before building.")

    recent = captures(paths, limit=limit)
    if recent:
        lines.append("")
        lines.append("Recent memory:")
        for record in reversed(recent):
            lines.append(
                "- [%s] %s" % (record.get("kind"), _clip(str(record.get("text") or ""), 140))
            )
    return "\n".join(lines)


# ---------------------------------------------------------------- health


def health(paths: Paths) -> dict:
    """Sizes, last-capture age, stale ISAs, missing directories."""
    missing = []
    for name in (
        "config_dir",
        "user_dir",
        "memory",
        "work",
        "state",
        "knowledge",
        "learning",
        "observability",
    ):
        path = getattr(paths, name)
        if not path.is_dir():
            missing.append(str(path))

    sizes = {}
    for name in ("captures", "work_json", "ledger", "hook_events", "tool_events", "ask_fidelity"):
        path = getattr(paths, name)
        sizes[name] = path.stat().st_size if path.is_file() else 0

    records = captures(paths)
    last_ts = str(records[-1].get("ts")) if records else None
    age_days = None
    if last_ts:
        stamp = _parse_iso(last_ts)
        if stamp is not None:
            age_days = round((datetime.now(timezone.utc) - stamp).total_seconds() / 86400.0, 2)

    stale = []
    now = datetime.now(timezone.utc)
    for entry in isa_mod.registry(paths):
        if str(entry.get("phase") or "").lower() in isa_mod.COMPLETE_PHASES:
            continue
        stamp = _parse_iso(str(entry.get("updated") or ""))
        if stamp is None:
            continue
        if (now - stamp).total_seconds() > _STALE_DAYS * 86400:
            stale.append({"slug": entry.get("slug"), "updated": entry.get("updated")})

    return {
        "home": str(paths.home),
        "exists": paths.home.is_dir(),
        "missing_dirs": missing,
        "sizes_bytes": sizes,
        "captures": len(records),
        "reflections": len(reflections(paths)),
        "knowledge_notes": len(list(paths.knowledge.glob("*.md"))) if paths.knowledge.is_dir() else 0,
        "last_capture": last_ts,
        "last_capture_age_days": age_days,
        "isas": len(isa_mod.registry(paths)),
        "stale_isas": stale,
        "stale_after_days": _STALE_DAYS,
    }


# ---------------------------------------------------------------- knowledge


def knowledge_slug(title: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", str(title)) if part]
    if not parts:
        return "Note"
    return "".join(part[:1].upper() + part[1:] for part in parts)[:80]


def knowledge_add(
    paths: Paths,
    title: str,
    body: str,
    tags: list | str | None = None,
    kind: str = "fact",
) -> Path:
    """Write one knowledge note with typed frontmatter. Updates in place if present."""
    clean_title = str(title or "").strip()
    if not clean_title:
        raise ValueError("a knowledge note needs a title")
    if isinstance(tags, str):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    else:
        tag_list = [str(t).strip() for t in (tags or []) if str(t).strip()]

    target = paths.knowledge / ("%s.md" % knowledge_slug(clean_title))
    stamp = now_iso()
    created = stamp
    if target.is_file():
        try:
            existing, _ = isa_mod.parse_frontmatter(
                target.read_text(encoding="utf-8").split("\n")
            )
            created = str(existing.get("created") or stamp)
        except OSError:
            pass

    content = "\n".join(
        [
            "---",
            "type: %s" % kind,
            "title: %s" % clean_title,
            "tags: [%s]" % ", ".join(tag_list),
            "created: %s" % created,
            "updated: %s" % stamp,
            "convention: kaios-freshness-v1",
            "---",
            "",
            "# %s" % clean_title,
            "",
            str(body or "").strip(),
            "",
        ]
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return target


def knowledge_find(paths: Paths, query: str, limit: int = 20) -> list[dict]:
    """Title-and-body search across the knowledge archive."""
    needle = str(query or "").strip().lower()
    out: list[dict] = []
    if not paths.knowledge.is_dir():
        return out
    for path in sorted(paths.knowledge.glob("*.md")):
        try:
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle and needle not in body.lower() and needle not in path.stem.lower():
            continue
        frontmatter, _ = isa_mod.parse_frontmatter(body.split("\n"))
        out.append(
            {
                "path": str(path),
                "title": _title_of(body, path),
                "type": frontmatter.get("type"),
                "tags": frontmatter.get("tags") or [],
                "updated": frontmatter.get("updated"),
                "excerpt": _clip(_first_line(body, needle) if needle else body.split("\n")[0]),
            }
        )
        if len(out) >= limit:
            break
    return out
