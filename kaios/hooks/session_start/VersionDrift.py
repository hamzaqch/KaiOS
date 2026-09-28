"""Rule: the shipped doctrine version, the Python package version, and the copy
installed under ``KAIOS_HOME`` must agree; a session is warned only when they do
not.

Falsifier: three matching versions producing any output, or a mismatch producing
none.
"""

from __future__ import annotations

from ... import __version__
from .. import util


def _version_at(directory) -> str:
    """The first line of ``<directory>/VERSION``, or an empty string."""
    if directory is None:
        return ""
    text = util.read_text(directory / "VERSION").strip()
    if not text:
        return ""
    return text.splitlines()[0].strip()


def run(event: dict, ctx) -> dict | None:
    repo_version = _version_at(ctx.paths.repo_doctrine)
    home_version = _version_at(ctx.paths.doctrine)
    package_version = str(__version__ or "").strip()

    seen: dict = {}
    for label, value in (
        ("doctrine", repo_version),
        ("package", package_version),
        ("installed", home_version),
    ):
        if value:
            seen.setdefault(value, []).append(label)
    if len(seen) < 2:
        return None
    parts = ["%s %s" % ("/".join(labels), value) for value, labels in sorted(seen.items())]
    return util.context(
        "⚠️ WARN version drift: %s. Reinstall or bump before trusting doctrine paths."
        % "; ".join(parts)
    )
