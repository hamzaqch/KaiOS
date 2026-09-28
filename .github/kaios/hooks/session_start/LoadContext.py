"""Rule: a session opens with the doctrine pointer, the active ISA's state, the
repo, the optional-integration flags, the profile's presence, and the memory hot
layer, as one bounded ``additionalContext`` string under 6000 characters.

Falsifier: ``.github/tests/test_hooks.py`` asserts the injected block names the Algorithm
pointer and the ISA state and stays under the size cap on a fixture home.
"""

from __future__ import annotations

from ... import __version__
from ... import isa as isa_mod
from ... import memory as memory_mod
from .. import util

#: Hard ceiling for the block this hook contributes (ISC-16 allows 6000).
LIMIT = 5600
_HOT_LIMIT = 1600


def _doctrine_pointer(ctx) -> str:
    where = util.display(ctx.doctrine, ctx.repo) or "SYSTEM"
    return (
        "Substantial work: read `%s/ALGORITHM/LATEST` then that version file." % where
    )


def _isa_line(ctx) -> str:
    if ctx.active_isa is None:
        return "No active ISA. Write done down before building: `python -m kaios isa scaffold`."
    try:
        info = isa_mod.status(isa_mod.parse(ctx.active_isa))
    except (OSError, ValueError):
        return "Active ISA at %s could not be parsed." % util.display(ctx.active_isa, ctx.repo)
    frontier = ", ".join(info["frontier"][:5]) or "none"
    return "Active ISA %s — phase %s, %s done, frontier %s (%s)." % (
        info["slug"],
        info["phase"] or "unknown",
        info["counted"],
        frontier,
        util.display(ctx.active_isa, ctx.repo),
    )


def _flag_line(ctx) -> str:
    config = ctx.config if isinstance(ctx.config, dict) else {}
    on: list = []
    for key in sorted(config):
        value = config[key]
        if value is True:
            on.append(key)
        elif isinstance(value, dict):
            for inner in sorted(value):
                if value[inner] is True:
                    on.append("%s.%s" % (key, inner))
    if not config:
        return "Config: none recorded yet; every integration is optional."
    if not on:
        return "Config: %d key(s) recorded, no optional integration switched on." % len(config)
    return "Config: %d key(s); on — %s." % (len(config), ", ".join(on[:8]))


def _profile_line(ctx) -> str:
    if ctx.paths.profile.is_file():
        return "Profile: USER/PROFILE.md present."
    return "Profile: USER/PROFILE.md absent — run `/kaios-setup` to write it."


def run(event: dict, ctx) -> dict | None:
    lines = [
        util.BANNER,
        "",
        "KaiOS %s · repo %s · home %s"
        % (
            __version__,
            ctx.repo.name if ctx.repo is not None else "none",
            ctx.paths.home.name,
        ),
        "",
        _doctrine_pointer(ctx),
        "",
        _isa_line(ctx),
        _flag_line(ctx),
        _profile_line(ctx),
    ]

    try:
        hot = memory_mod.hot_layer(ctx.paths, limit=5)
    except (OSError, ValueError):
        hot = ""
    if hot.strip():
        lines += ["", "Memory:", util.clip(hot.replace("\n", " · "), _HOT_LIMIT)]

    block = "\n".join(lines)
    if len(block) > LIMIT:
        block = block[: LIMIT - 1].rstrip() + "…"
    return util.context(block)
