"""Rule: a message that asks for substantial work with no ISA registered is told to
write done down first, and a message that matches a shipped skill's USE WHEN
phrases is told that capability already exists.

Falsifier: "build the importer" with no active ISA producing no nudge, or a prompt
quoting a skill's USE WHEN phrase producing no pointer to that skill.
"""

from __future__ import annotations

import json
import re

from ... import isa as isa_mod
from .. import util

#: Where the built skill index is cached inside ``MEMORY/STATE``.
INDEX_NAME = "skill-index.json"
#: At most this many skill pointers per prompt.
MAX_SUGGESTIONS = 3

_DEPTH = re.compile(
    r"\bgo heavy\b|\bheavy\b|\bgo deep\b|\bdeeply\b|\bdeep dive\b|\bthorough(?:ly)?\b"
    r"|\bcarefully\b|\bquick pass\b|\bquick look\b|\btake your time\b",
    re.IGNORECASE,
)
_BUILD = re.compile(
    r"\b(?:build|implement|add|create|write|refactor|migrate|port|ship|wire up|wire|"
    r"scaffold|design|rework|rewrite|extend|integrate)\b",
    re.IGNORECASE,
)
_PHRASE_SPLIT = re.compile(r"[,;]| / ")
_FRONTMATTER_LIMIT = 40


# ---------------------------------------------------------------- skill index


def _skill_dirs(ctx) -> list:
    candidates = []
    if ctx.repo is not None:
        candidates.append(ctx.repo / ".github" / "skills")
    candidates.append(ctx.paths.home / "skills")
    return [item for item in candidates if item.is_dir()]


def _skill_files(ctx) -> list:
    files: list = []
    for directory in _skill_dirs(ctx):
        try:
            files.extend(sorted(directory.glob("*/SKILL.md")))
        except OSError:
            continue
    return files


def _newest_mtime(files: list) -> float:
    newest = 0.0
    for path in files:
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            continue
    return round(newest, 3)


def _phrases(description: str) -> list:
    """The USE WHEN clause, split into matchable phrases."""
    text = str(description or "")
    lowered = text.lower()
    start = lowered.find("use when")
    if start < 0:
        return []
    body = text[start + len("use when") :]
    stop = body.lower().find("not for")
    if stop >= 0:
        body = body[:stop]
    out: list = []
    for chunk in _PHRASE_SPLIT.split(body):
        phrase = chunk.strip(" .:—-").lower()
        if len(phrase) < 8 or len(phrase) > 60:
            continue
        if len(phrase.split()) < 2:
            continue
        if phrase not in out:
            out.append(phrase)
    return out[:20]


def build_index(ctx) -> dict:
    """Scan every SKILL.md and return ``{mtime, skills: [{name, phrases}]}``."""
    files = _skill_files(ctx)
    skills: list = []
    for path in files:
        text = util.read_text(path)
        if not text:
            continue
        frontmatter, _ = isa_mod.parse_frontmatter(text.split("\n")[:_FRONTMATTER_LIMIT])
        name = str(frontmatter.get("name") or path.parent.name).strip()
        phrases = _phrases(frontmatter.get("description") or "")
        if name and phrases:
            skills.append({"name": name, "phrases": phrases})
    return {"mtime": _newest_mtime(files), "built": util.now_iso(), "skills": skills}


def index(ctx) -> dict:
    """The cached index, rebuilt when any SKILL.md is newer than the cache."""
    cache = ctx.paths.state / INDEX_NAME
    current = _newest_mtime(_skill_files(ctx))
    try:
        stored = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        stored = None
    if isinstance(stored, dict) and abs(float(stored.get("mtime") or -1.0) - current) < 0.001:
        return stored
    fresh = build_index(ctx)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(
            json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
    except OSError:
        pass
    return fresh


def matches(ctx, text: str) -> list:
    """Skill names whose USE WHEN phrases appear in this prompt."""
    lowered = " ".join(str(text).lower().split())
    hits: list = []
    for entry in index(ctx).get("skills") or []:
        for phrase in entry.get("phrases") or []:
            if phrase in lowered:
                name = str(entry.get("name"))
                if name not in hits:
                    hits.append(name)
                break
    return hits[:MAX_SUGGESTIONS]


# ---------------------------------------------------------------- hook


def run(event: dict, ctx) -> dict | None:
    text = util.prompt(event)
    if not text:
        return None

    lines: list = []
    depth = _DEPTH.search(text)
    build = _BUILD.search(text)

    if ctx.active_isa is None and (depth or build):
        lines.append(
            "No ISA is registered and this reads as substantial work. Write done down first: "
            "`python -m kaios isa scaffold --slug <slug> --goal <goal>`."
        )
    elif depth is not None and ctx.active_isa is not None:
        try:
            info = isa_mod.status(isa_mod.parse(ctx.active_isa))
            frontier = ", ".join(info["frontier"][:5]) or "none"
        except (OSError, ValueError):
            frontier = "unreadable"
        lines.append(
            "Depth directive %r noted. The active ISA's frontier is %s — climb a claim, do not "
            "wander." % (depth.group(0), frontier)
        )

    try:
        found = matches(ctx, text)
    except (OSError, ValueError):
        found = []
    if found:
        lines.append(
            "That capability exists: %s." % ", ".join("/%s" % name for name in found)
        )

    return util.context("\n".join(lines))
