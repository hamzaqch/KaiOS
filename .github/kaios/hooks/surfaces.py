"""Which self-surface a path belongs to: doctrine, machinery, or memory.

Rule: one classifier decides what counts as a write to the system itself, so the
PreToolUse gate and the PostToolUse surface line can never disagree about a path.
Falsifier: a path that ``SystemFileGuard`` asks about but ``SystemChangeSurface``
reports as ordinary code.
"""

from __future__ import annotations

from pathlib import Path

from .. import paths as paths_mod
from . import util

#: Doctrine tree names, taken from ``kaios.paths`` so the rename stays in one
#: place: the current name plus every legacy spelling still resolved.
DOCTRINE_DIRS: tuple = (getattr(paths_mod, "DOCTRINE_DIR", "SYSTEM"),) + tuple(
    getattr(paths_mod, "LEGACY_DOCTRINE_DIRS", ("KAIOS",))
)

#: Kinds ``SystemFileGuard`` gates before the write happens.
GATED: tuple = ("doctrine", "hooks", "instructions")

#: Kinds ``SystemChangeSurface`` reports after the write happens.
SELF_SURFACES: tuple = ("doctrine", "hooks", "instructions", "agents", "skills", "config")

_MEMORY_KINDS: tuple = (
    ("KNOWLEDGE", "knowledge"),
    ("LEARNING/REFLECTIONS", "reflection"),
    ("LEARNING/INCIDENTS", "incident"),
    ("LEARNING", "capture"),
    ("OBSERVABILITY", "observability"),
    ("STATE", "state"),
    ("WORK", "work"),
)


def doctrine_names(ctx) -> tuple:
    """Doctrine directory names to recognise, including this checkout's own."""
    names = list(DOCTRINE_DIRS)
    for candidate in (ctx.paths.repo_doctrine, ctx.paths.doctrine):
        if candidate is not None and candidate.name and candidate.name not in names:
            names.append(candidate.name)
    return tuple(names)


def relative(ctx, path) -> str:
    """A forward-slash path relative to the repo or the home when it is inside one."""
    text = util.posix(str(path)).strip()
    if not text:
        return ""
    target = Path(str(path))
    if not target.is_absolute():
        while text.startswith("./"):
            text = text[2:]
        return text
    for base in (ctx.repo, ctx.paths.home):
        if base is None:
            continue
        try:
            return target.resolve().relative_to(Path(base).resolve()).as_posix()
        except (OSError, ValueError):
            continue
    return text


def classify(ctx, path) -> str | None:
    """The self-surface this path belongs to, or ``None`` for ordinary content."""
    rel = relative(ctx, path)
    if not rel:
        return None
    lowered = rel.lower()
    parts = [part for part in rel.split("/") if part and part != ".."]

    if lowered.endswith(".github/copilot-instructions.md") or lowered == "copilot-instructions.md":
        return "instructions"
    if "/.github/" in "/" + lowered:
        # Case is kept for the doctrine test below: the package directory
        # ``.github/kaios`` differs from the legacy doctrine name ``KAIOS`` only
        # in case, which is the collision the doctrine rename existed to avoid.
        after = rel[lowered.index(".github/") + len(".github/") :]
        for prefix, kind in (
            ("hooks/", "hooks"),
            ("instructions/", "instructions"),
            ("agents/", "agents"),
            ("skills/", "skills"),
        ):
            if after.lower().startswith(prefix):
                return kind
        # The doctrine tree lives at ``.github/SYSTEM`` now, so the first segment
        # after ``.github/`` is what says whether this is a doctrine write.
        if after.split("/", 1)[0] in doctrine_names(ctx):
            return "doctrine"
    if parts and parts[0] in doctrine_names(ctx):
        return "doctrine"
    if "kaios/hooks/" in lowered:
        return "hooks"
    if lowered.endswith("config/config.json") or lowered.endswith("config/models.json"):
        return "config"
    if memory_kind(ctx, path) is not None:
        return "memory"
    return None


def memory_kind(ctx, path) -> str | None:
    """Which part of memory a path writes to, or ``None``."""
    rel = relative(ctx, path)
    if not rel:
        return None
    marker = "MEMORY/"
    index = rel.find(marker)
    if index < 0:
        return None
    tail = rel[index + len(marker) :]
    for prefix, kind in _MEMORY_KINDS:
        if tail.startswith(prefix):
            return kind
    return "memory"


def is_gated(ctx, path) -> bool:
    return classify(ctx, path) in GATED


def is_self_surface(ctx, path) -> bool:
    return classify(ctx, path) in SELF_SURFACES
