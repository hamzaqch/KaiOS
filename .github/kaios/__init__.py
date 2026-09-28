"""KaiOS — work-only AI operating system core for Copilot in VS Code.

Standard library only. Every module in this package must import nothing that is
not in ``sys.stdlib_module_names``; ``python -m kaios integrity imports`` is the
falsifier for that rule.
"""

from pathlib import Path

__all__ = ["__version__", "version_file_candidates"]


def version_file_candidates() -> "list[Path]":
    """Places the shipped VERSION file may live, most-specific first.

    The package lives at ``.github/kaios``, so its parent is the framework
    directory and the doctrine tree is ``.github/SYSTEM`` beside it. ``KAIOS/``
    is probed as a fallback for a checkout made before that rename, and the flat
    shapes cover a tree whose doctrine directory collided with the package name
    on a case-insensitive filesystem.
    """
    here = Path(__file__).resolve().parent
    return [
        here.parent / "SYSTEM" / "VERSION",
        here.parent / "KAIOS" / "VERSION",
        here.parent / "VERSION",
        here / "VERSION",
    ]


def _read_version() -> str:
    for candidate in version_file_candidates():
        try:
            if candidate.is_file():
                text = candidate.read_text(encoding="utf-8").strip()
                if text:
                    return text.splitlines()[0].strip()
        except OSError:
            continue
    return "0.0.0"


__version__ = _read_version()
