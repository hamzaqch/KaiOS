"""SessionStart: what the model cannot see on its own gets injected here.

Every module here exposes ``run(event: dict, ctx) -> dict | None`` and is loaded
by the runner in alphabetical order.
"""
