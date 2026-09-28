"""PreCompact: snapshotting state a compaction would lose.

Every module here exposes ``run(event: dict, ctx) -> dict | None`` and is loaded
by the runner in alphabetical order.
"""
