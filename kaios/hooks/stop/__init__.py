"""Stop: close gates, rendering, learning capture, cleanup.

Every module here exposes ``run(event: dict, ctx) -> dict | None`` and is loaded
by the runner in alphabetical order.
"""
