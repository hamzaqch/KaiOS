#!/usr/bin/env python3
"""Track the state of a manually driven loop across sessions.

There is no scheduler in this environment, so a recurring prompt is driven by a
person or a task runner. This tool is the memory between iterations: which loop,
how many times it has run, what the last result was, and whether a stop
condition has been reached.

State lives in ``$KAIOS_HOME/MEMORY/STATE/loops.json`` (KAIOS_HOME defaults to
``~/.kaios``).

Exit codes: 0 ok, 1 the loop is finished or the named loop is unknown,
2 usage or unreadable state.
"""

import argparse
import datetime
import json
import os
import sys

RESULTS = ("ok", "fail", "nochange", "blocked")


def kaios_home():
    value = os.environ.get("KAIOS_HOME", "").strip()
    if value:
        return os.path.abspath(os.path.expanduser(value))
    return os.path.join(os.path.expanduser("~"), ".kaios")


def state_path(override=""):
    if override:
        return os.path.abspath(os.path.expanduser(override))
    return os.path.join(kaios_home(), "MEMORY", "STATE", "loops.json")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path):
    if not os.path.exists(path):
        return {"loops": {}}
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "loops" not in data:
        raise ValueError("state file is not a loops document")
    return data


def save(path, data):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def cmd_start(args, data):
    loops = data["loops"]
    if args.name in loops and not args.force:
        return 1, {"error": "loop exists", "name": args.name, "hint": "use --force to reset"}
    loops[args.name] = {
        "name": args.name,
        "prompt": args.prompt,
        "cadence": args.every,
        "max_iterations": args.max,
        "stop_when": args.stop_when,
        "iterations": 0,
        "created": now_iso(),
        "updated": now_iso(),
        "status": "running",
        "last_result": None,
        "last_note": "",
        "history": [],
    }
    return 0, loops[args.name]


def cmd_tick(args, data):
    loop = data["loops"].get(args.name)
    if loop is None:
        return 1, {"error": "unknown loop", "name": args.name}
    if loop["status"] != "running":
        return 1, {"error": "loop is not running", "name": args.name, "status": loop["status"]}
    loop["iterations"] += 1
    loop["last_result"] = args.result
    loop["last_note"] = args.note
    loop["updated"] = now_iso()
    entry = {
        "iteration": loop["iterations"],
        "at": loop["updated"],
        "result": args.result,
        "note": args.note,
    }
    loop["history"].append(entry)
    loop["history"] = loop["history"][-50:]
    reason = ""
    if loop["max_iterations"] and loop["iterations"] >= loop["max_iterations"]:
        reason = "reached max_iterations"
    elif args.done:
        reason = "caller reported the stop condition met"
    elif args.result == "fail" and args.stop_on_fail:
        reason = "failed and stop-on-fail was set"
    if reason:
        loop["status"] = "finished"
        loop["finished_reason"] = reason
        return 1, {"loop": loop, "finished": reason}
    return 0, {"loop": loop, "finished": None}


def cmd_stop(args, data):
    loop = data["loops"].get(args.name)
    if loop is None:
        return 1, {"error": "unknown loop", "name": args.name}
    loop["status"] = "stopped"
    loop["finished_reason"] = args.reason or "stopped by request"
    loop["updated"] = now_iso()
    return 0, loop


def cmd_status(args, data):
    if args.name:
        loop = data["loops"].get(args.name)
        if loop is None:
            return 1, {"error": "unknown loop", "name": args.name}
        return 0, loop
    return 0, {"loops": sorted(data["loops"].values(), key=lambda l: l["name"])}


def render(payload):
    if "loops" in payload:
        rows = payload["loops"]
        if not rows:
            return "no loops recorded"
        lines = [
            "%-22s %-9s %-6s %-9s %s" % ("NAME", "STATUS", "ITERS", "LAST", "CADENCE"),
            "-" * 64,
        ]
        for loop in rows:
            lines.append(
                "%-22s %-9s %-6d %-9s %s"
                % (
                    loop["name"][:22],
                    loop["status"],
                    loop["iterations"],
                    str(loop.get("last_result") or "-"),
                    loop.get("cadence") or "-",
                )
            )
        return "\n".join(lines)
    return json.dumps(payload, indent=2)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="loop_state.py",
        description="Track iteration count and last result for manually driven loops.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", default="", help="override the state file path")
    common.add_argument("--json", action="store_true", help="emit JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="register a loop", parents=[common])
    start.add_argument("--name", required=True)
    start.add_argument("--prompt", required=True, help="the prompt or slash command to run")
    start.add_argument("--every", default="", help="intended cadence, free text, e.g. 30m")
    start.add_argument("--max", type=int, default=0, help="stop after this many iterations")
    start.add_argument("--stop-when", default="", help="the stop condition in words")
    start.add_argument("--force", action="store_true", help="overwrite an existing loop")

    tick = sub.add_parser("tick", help="record one iteration", parents=[common])
    tick.add_argument("--name", required=True)
    tick.add_argument("--result", choices=RESULTS, default="ok")
    tick.add_argument("--note", default="", help="one line about what this iteration did")
    tick.add_argument("--done", action="store_true", help="the stop condition is met")
    tick.add_argument(
        "--stop-on-fail", action="store_true", help="finish the loop on a fail result"
    )

    stop = sub.add_parser("stop", help="finish a loop", parents=[common])
    stop.add_argument("--name", required=True)
    stop.add_argument("--reason", default="")

    status = sub.add_parser("status", help="show one loop or all of them", parents=[common])
    status.add_argument("--name", default="")

    listing = sub.add_parser("list", help="show all loops", parents=[common])
    listing.add_argument("--name", default="", help=argparse.SUPPRESS)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    path = state_path(args.state)
    try:
        data = load(path)
    except (OSError, ValueError) as exc:
        payload = {"error": "cannot read state", "path": path, "detail": str(exc)}
        print(json.dumps(payload) if args.json else "error: %s" % exc)
        return 2

    handlers = {
        "start": cmd_start,
        "tick": cmd_tick,
        "stop": cmd_stop,
        "status": cmd_status,
        "list": cmd_status,
    }
    code, payload = handlers[args.command](args, data)
    if args.command in ("start", "tick", "stop"):
        try:
            save(path, data)
        except OSError as exc:
            message = {"error": "cannot write state", "path": path, "detail": str(exc)}
            print(json.dumps(message) if args.json else "error: %s" % exc)
            return 2
    payload["state_file"] = path
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render(payload))
    return code


if __name__ == "__main__":
    sys.exit(main())
