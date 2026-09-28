"""Rule: a write to a surface that changes how the system itself behaves — doctrine,
instructions, an agent, a skill, a hook, the registries — is named in the response,
so self-modification is never silent.

Falsifier: a write to a hook module producing no line, or a write to ordinary
source producing one.
"""

from __future__ import annotations

from .. import surfaces
from .. import util


def run(event: dict, ctx) -> dict | None:
    if not util.is_write(event):
        return None
    path = util.file_path(event)
    if not path:
        return None
    kind = surfaces.classify(ctx, path)
    if kind not in surfaces.SELF_SURFACES:
        return None
    return util.context("⚙️ SYSTEM: %s write → %s" % (kind, surfaces.relative(ctx, path)))
