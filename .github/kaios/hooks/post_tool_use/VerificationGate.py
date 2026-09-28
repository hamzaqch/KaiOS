"""Rule: a claim that just went ``[x]`` without an evidence stub is called out by id
in the response, because a closed claim with no evidence is an unverified claim.

Falsifier: closing a claim with no ``— evidence:`` producing no warning, or closing
one with evidence producing one.
"""

from __future__ import annotations

from .. import claims
from .. import util


def run(event: dict, ctx) -> dict | None:
    target = claims.isa_target(event)
    if target is None:
        return None
    _, fresh = claims.newly_checked(ctx, target)
    missing = [claim for claim in fresh if not claim.evidence]
    if not missing:
        return None
    return util.context(
        "⚠️ %s closed without an evidence stub; add `— evidence: <commit|test|probe>` or reopen."
        % ", ".join(claim.id for claim in missing)
    )
