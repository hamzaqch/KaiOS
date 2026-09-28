"""Rule: a turn does not end while the active ISA has a claim checked ``[x]`` with no
evidence stub, and a response missing the banner or the closer is reminded without
being blocked.

Falsifier: the bad fixture ISA letting a turn close, the good one blocking it, or a
second pass blocking when ``stop_hook_active`` is already true.
"""

from __future__ import annotations

from ... import isa as isa_mod
from .. import util


def unevidenced(isa) -> list:
    """Ids of claims closed with no evidence stub."""
    return [
        claim.id
        for claim in isa.isc()
        if claim.checked and not claim.dropped and not claim.evidence
    ]


def _last_message(event: dict) -> str:
    for key in ("last_message", "response", "assistant_message", "lastMessage", "message"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _format_note(event: dict) -> str:
    text = _last_message(event)
    if not text:
        return ""
    missing: list = []
    if "════ KaiOS" not in text:
        missing.append("the banner as the first line")
    if util.CLOSER not in text and "Kai:" not in text:
        missing.append("the `%s <one line>` closer as the last line" % util.CLOSER)
    if not missing:
        return ""
    return "⚠️ Response format: this turn is missing %s." % " and ".join(missing)


def run(event: dict, ctx) -> dict | None:
    note = _format_note(event)
    already = bool(event.get("stop_hook_active") or event.get("stopHookActive"))

    if ctx.active_isa is None or already:
        return util.context(note)

    try:
        parsed = isa_mod.parse(ctx.active_isa)
    except (OSError, ValueError):
        return util.context(note)

    open_claims = unevidenced(parsed)
    if not open_claims:
        return util.context(note)

    reason = (
        "%s closed with no evidence stub in %s. Add `— evidence: <commit|test|probe>` to each, or "
        "reopen the claim, before ending the turn."
        % (", ".join(open_claims), util.display(ctx.active_isa, ctx.repo))
    )
    result = util.block(reason)
    if note:
        result["additionalContext"] = note
    return result
