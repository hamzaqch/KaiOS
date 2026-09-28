"""Rule: every prompt gets the response format contract restated in one line, so a
long session cannot drift out of the shape it promised.

Falsifier: the injected line missing the banner-first rule or the closer rule.
"""

from __future__ import annotations

from .. import util


def run(event: dict, ctx) -> dict | None:
    return util.context(
        "Format: `%s` first, `%s <one line>` last; 🔧 CHANGE and ✅ VERIFY only when this "
        "turn mutated something, and always together. Lead with the answer." % (util.BANNER, util.CLOSER)
    )
