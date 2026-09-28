"""``python -m kaios hooks <run|list|probe>``.

Rule: the hook layer is inspectable and provable from the command line — what is
registered, what modules exist, and whether every event still answers with valid
JSON.
Falsifier: ``python -m kaios hooks probe`` exiting 0 while an event returns
something that is not one JSON object.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import EVENTS, canonical
from .. import events as events_mod
from ..paths import Paths
from . import runner as runner_mod
from .samples import sample

OK = 0
FAILURE = 1
USAGE = 2

USAGE_TEXT = (
    "usage: python -m kaios hooks <run <Event> | list | probe> [--json] [--md] [--home PATH]"
)


# ---------------------------------------------------------------- registry


def registry_file(paths: Paths):
    """The hook registration file: the checkout's first, then ``KAIOS_HOME``."""
    candidates = []
    if paths.repo is not None:
        candidates.append(paths.repo / events_mod.REGISTRY_RELATIVE)
    candidates.append(paths.hooks_json)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def registry_report(path) -> dict:
    """What one registration file registers, and why it could not be read.

    Parsing is ``kaios.events.read_registry``, which is path-addressed and
    raises rather than substituting ``EVENTS``. Both matter here: the installed
    registry under ``KAIOS_HOME/hooks`` is not at the checkout-relative
    location, and ISC-11's falsifier is a registry naming fewer than eight
    events, which a fallback to the default would mask. The failure reason is
    carried into the report because ``hooks list`` is the surface someone reads
    when that claim fails.
    """
    report: dict = {"path": str(path), "exists": Path(path).is_file()}
    try:
        registered = list(events_mod.read_registry(path))
    except (OSError, ValueError) as exc:
        report["events_registered"] = 0
        report["registered"] = []
        report["error"] = "%s: %s" % (type(exc).__name__, exc)
        return report
    report["events_registered"] = len(registered)
    report["registered"] = registered
    return report


# ---------------------------------------------------------------- commands


def do_list(paths: Paths, as_md: bool = False) -> int:
    events = runner_mod.inventory()
    path = registry_file(paths)
    registry = registry_report(path)
    registered = registry["registered"]
    payload = {
        "events": events,
        "count": sum(len(names) for names in events.values()),
        "registry": registry,
    }
    if as_md:
        lines = ["# kaios hooks", "", "| event | modules | hooks |", "|---|---|---|"]
        for name in EVENTS:
            names = events.get(name) or []
            lines.append("| %s | %d | %s |" % (name, len(names), ", ".join(names) or "-"))
        lines += [
            "",
            "%d module(s) across %d event(s); registry `%s` registers %d event(s)."
            % (payload["count"], len(EVENTS), path, len(registered)),
            "",
        ]
        sys.stdout.write("\n".join(lines))
        return OK
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    return OK


def probe(home: str | None = None) -> dict:
    """Fire every event in-process with its sample payload. Never raises."""
    rows = []
    for name in EVENTS:
        payload = sample(name)
        note = ""
        valid = False
        decision = None
        try:
            decision = runner_mod.dispatch(name, payload, home=home)
            blob = json.dumps(decision, sort_keys=True, default=str)
            reloaded = json.loads(blob)
            valid = isinstance(reloaded, dict) and "continue" in reloaded
            if not valid:
                note = "output is not an object with a continue key"
        except Exception as exc:  # noqa: BLE001 - the probe reports, never crashes
            note = "%s: %s" % (type(exc).__name__, exc)
        rows.append(
            {
                "event": name,
                "hooks": len(runner_mod.discover(name)),
                "ok": bool(valid),
                "keys": sorted(decision) if isinstance(decision, dict) else [],
                "note": note,
            }
        )
    failed = [row for row in rows if not row["ok"]]
    return {"ok": not failed, "events": len(rows), "failed": len(failed), "rows": rows}


def probe_markdown(report: dict) -> str:
    lines = ["# kaios hooks probe", "", "| event | hooks | result | keys | note |", "|---|---|---|---|---|"]
    for row in report["rows"]:
        lines.append(
            "| %s | %d | %s | %s | %s |"
            % (
                row["event"],
                row["hooks"],
                "OK" if row["ok"] else "FAIL",
                ", ".join(row["keys"]) or "-",
                row["note"] or "-",
            )
        )
    lines += [
        "",
        "%s — %d event(s), %d failed."
        % ("PASS" if report["ok"] else "FAIL", report["events"], report["failed"]),
        "",
    ]
    return "\n".join(lines)


def do_probe(home: str | None, as_json: bool) -> int:
    report = probe(home=home)
    if as_json:
        sys.stdout.write(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n")
    else:
        sys.stdout.write(probe_markdown(report))
    return OK if report["ok"] else FAILURE


def do_run(event_name: str, home: str | None) -> int:
    """Dispatch one event. An unknown name still answers; the runner logs it."""
    return runner_mod.run_event(event_name, home=home)


# ---------------------------------------------------------------- entry


def main(argv: list | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = False
    as_md = False
    home = None
    rest: list = []
    index = 0
    while index < len(args):
        token = args[index]
        if token == "--json":
            as_json = True
        elif token == "--md":
            as_md = True
        elif token == "--home":
            index += 1
            home = args[index] if index < len(args) else None
        elif token.startswith("--home="):
            home = token.split("=", 1)[1]
        elif token in ("-h", "--help"):
            sys.stdout.write(USAGE_TEXT + "\n")
            return USAGE
        else:
            rest.append(token)
        index += 1

    if not rest:
        sys.stdout.write(USAGE_TEXT + "\n")
        return USAGE

    command = rest[0]
    paths = Paths.resolve(home=home)

    if command == "list":
        return do_list(paths, as_md=as_md and not as_json)
    if command == "probe":
        return do_probe(home, as_json=as_json)
    if command == "run":
        if len(rest) < 2:
            sys.stdout.write(USAGE_TEXT + "\n")
            return USAGE
        return do_run(rest[1], home)
    if canonical(command) is not None:
        # `kaios hooks SessionStart` is accepted as shorthand for `run`.
        return do_run(command, home)

    sys.stdout.write(USAGE_TEXT + "\n")
    return USAGE


if __name__ == "__main__":
    raise SystemExit(main())
