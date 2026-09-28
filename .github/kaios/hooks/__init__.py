"""The hook layer: eight harness events, one runner, one module per rule.

Rule: doctrine that nothing enforces decays, so every rule that is a checkable
property of an artifact or a gate on an irreversible act lives here as a module
under ``.github/kaios/hooks/<event_snake>/``.
Falsifier: ``python -m kaios hooks list`` shows fewer than eight events or fewer
than 25 modules, or ``python -m kaios hooks probe`` reports a failing row.

The event vocabulary is not defined here. ``kaios.events`` is the one place it is
written in Python and imports nothing from the rest of the package, so this
re-export keeps ``kaios.hooks.EVENTS`` working for the runner, the CLI, and the
tests without a second tuple that could drift from it.
"""

from __future__ import annotations

from ..events import EVENTS, canonical, event_dir

__all__ = ["EVENTS", "event_dir", "canonical"]
