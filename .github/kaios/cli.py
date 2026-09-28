"""``python -m kaios <group> <command>``.

JSON on stdout by default so hooks and scripts can consume it; ``--md`` where a
human is the reader. Exit codes: 0 ok, 1 failure, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, integrity
from . import isa as isa_mod
from . import ledger as ledger_mod
from . import memory as memory_mod
from . import models as models_mod
from . import setup as setup_mod
from . import doctor as doctor_mod
from .paths import Paths

OK = 0
FAILURE = 1
USAGE = 2


def emit(payload, markdown: str | None = None, as_md: bool = False) -> None:
    if as_md and markdown is not None:
        sys.stdout.write(markdown if markdown.endswith("\n") else markdown + "\n")
        return
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")


def fail(message: str, code: str = "error", as_md: bool = False) -> int:
    payload = {"ok": False, "error": code, "message": message}
    if as_md:
        sys.stdout.write("**%s** — %s\n" % (code, message))
    else:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return FAILURE


# ---------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kaios",
        description="KaiOS core: paths, ISAs, memory, ledger, models, setup, integrity, hooks.",
    )
    parser.add_argument("--version", action="version", version="kaios %s" % __version__)
    parser.add_argument("--home", default=None, help="override KAIOS_HOME for this call")
    parser.add_argument("--md", action="store_true", help="markdown output where it is supported")
    groups = parser.add_subparsers(dest="group", metavar="GROUP")

    groups.add_parser("paths", help="print every resolved path")
    groups.add_parser("doctor", help="self-check; exit 1 on any FAIL")

    isa_group = groups.add_parser("isa", help="scaffold, check, and read ISAs").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    scaffold = isa_group.add_parser("scaffold", help="write a new ISA")
    scaffold.add_argument("--slug", required=True)
    scaffold.add_argument("--goal", required=True)
    scaffold.add_argument("--task", default=None)
    scaffold.add_argument("--project", action="store_true", help="write <repo>/ISA.md")
    scaffold.add_argument("--dest", default=None, help="explicit destination path")
    scaffold.add_argument("--overwrite", action="store_true")
    for name, helptext in (
        ("check", "completeness, falsifiers, anti-claims, id stability, edges"),
        ("frontier", "the claims takeable right now"),
        ("status", "counts, phase, progress, frontier"),
        ("render", "a markdown status table"),
    ):
        sub = isa_group.add_parser(name, help=helptext)
        sub.add_argument("path", nargs="?", default=None, help="ISA path; default: the active ISA")
    isa_group.add_parser("list", help="every registered ISA")
    sync = isa_group.add_parser("sync", help="refresh an ISA's registry entry")
    sync.add_argument("path", nargs="?", default=None)

    memory_group = groups.add_parser("memory", help="captures, search, digest, knowledge").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    capture = memory_group.add_parser("capture", help="append one capture")
    capture.add_argument("--kind", required=True, choices=list(memory_mod.KINDS))
    capture.add_argument("--text", required=True)
    capture.add_argument("--meta", default=None, help="JSON object of extra fields")
    search = memory_group.add_parser("search", help="substring search across memory")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)
    digest = memory_group.add_parser("digest", help="markdown summary")
    digest.add_argument("--since", default=None, help="ISO timestamp")
    memory_group.add_parser("health", help="sizes, ages, stale ISAs, missing directories")
    memory_group.add_parser("hot", help="the short block a SessionStart hook injects")
    knowledge = memory_group.add_parser("knowledge", help="the knowledge archive").add_subparsers(
        dest="subcommand", metavar="SUBCOMMAND"
    )
    knowledge_add = knowledge.add_parser("add", help="write one note")
    knowledge_add.add_argument("--title", required=True)
    knowledge_add.add_argument("--body", required=True)
    knowledge_add.add_argument("--tags", default="")
    knowledge_add.add_argument("--type", dest="kind", default="fact")
    knowledge_find = knowledge.add_parser("find", help="search the archive")
    knowledge_find.add_argument("query", nargs="?", default="")
    knowledge_find.add_argument("--limit", type=int, default=20)

    ledger_group = groups.add_parser("ledger", help="version and change registry").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    version = ledger_group.add_parser("version", help="read or bump the version")
    version.add_argument("action", nargs="?", default=None, choices=["bump"])
    version.add_argument("part", nargs="?", default="patch", choices=list(ledger_mod.PARTS))
    record = ledger_group.add_parser("record", help="append one change")
    record.add_argument("--kind", required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--meta", default=None, help="JSON object of extra fields")
    log = ledger_group.add_parser("log", help="read the registry back")
    log.add_argument("--limit", type=int, default=20)

    models_group = groups.add_parser("models", help="role to model registry").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    models_group.add_parser("show", help="the effective registry")
    models_set = models_group.add_parser("set", help="write a role's model list")
    models_set.add_argument("role")
    models_set.add_argument("models", help="comma-separated, in priority order")
    models_apply = models_group.add_parser("apply", help="rewrite every agent's model list")
    models_apply.add_argument("--agents-dir", default=None)
    models_apply.add_argument("--dry-run", action="store_true")

    setup_group = groups.add_parser("setup", help="detect tools, store choices, render files").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    setup_group.add_parser("detect", help="what this machine has")
    write_config = setup_group.add_parser("write-config", help="merge answers into config.json")
    write_config.add_argument("config", help="JSON object, a path to one, or - for stdin")
    render = setup_group.add_parser("render", help="render profile, projects, mcp, hooks")
    render.add_argument("--answers", default=None, help="JSON object, a path to one, or - for stdin")
    render.add_argument("--dry-run", action="store_true")

    integrity_group = groups.add_parser("integrity", help="containment, docs, versions, imports").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    for name in integrity.CHECKS:
        sub = integrity_group.add_parser(name, help="the %s gate" % name)
        sub.add_argument("--root", default=None, help="repo root; default: the enclosing checkout")
        if name == "containment":
            sub.add_argument("--terms", default=None)
            sub.add_argument("--extra-terms", default=None)

    hooks_group = groups.add_parser("hooks", help="run, list, and probe hooks").add_subparsers(
        dest="command", metavar="COMMAND"
    )
    run_hook = hooks_group.add_parser("run", help="run one event: stdin to stdout")
    run_hook.add_argument("event")
    hooks_group.add_parser("list", help="every registered hook module")
    hooks_group.add_parser("probe", help="fire every event with sample stdin")

    _spread_common(parser)
    return parser


def _spread_common(parser: argparse.ArgumentParser, root: bool = True) -> None:
    """Let ``--md`` and ``--home`` be typed at any level, not only before the group.

    ``argparse.SUPPRESS`` as the default keeps a subparser from overwriting a
    value the caller already gave at an outer level.
    """
    if not root:
        parser.add_argument(
            "--md", action="store_true", default=argparse.SUPPRESS, help="markdown output"
        )
        parser.add_argument(
            "--home", default=argparse.SUPPRESS, help="override KAIOS_HOME for this call"
        )
    for action in parser._actions:  # noqa: SLF001 - argparse exposes no public walk
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for child in action.choices.values():
                _spread_common(child, root=False)


# ---------------------------------------------------------------- dispatch


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)

    # The hooks group lives in a package another builder owns; hand it the
    # remaining arguments untouched so its own parser stays authoritative.
    for index, token in enumerate(args_list):
        if token == "hooks" and not token.startswith("-"):
            return _delegate_hooks(args_list[index + 1 :])
        if not token.startswith("-"):
            break

    parser = build_parser()
    args = parser.parse_args(args_list)
    if not args.group:
        parser.print_help()
        return USAGE

    paths = Paths.resolve(home=args.home)
    handlers = {
        "paths": _paths,
        "doctor": _doctor,
        "isa": _isa,
        "memory": _memory,
        "ledger": _ledger,
        "models": _models,
        "setup": _setup,
        "integrity": _integrity,
    }
    handler = handlers.get(args.group)
    if handler is None:
        parser.print_help()
        return USAGE
    try:
        return handler(args, paths)
    except _Usage as exc:
        sys.stderr.write("%s\n" % exc)
        return USAGE
    except (OSError, ValueError, FileExistsError, FileNotFoundError) as exc:
        return fail(str(exc), type(exc).__name__, args.md)


class _Usage(Exception):
    pass


def _delegate_hooks(rest: list[str]) -> int:
    try:
        from .hooks import cli as hooks_cli  # type: ignore
    except ImportError as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": "HooksUnavailable",
                    "message": "the hooks package is not installed in this checkout: %s" % exc,
                    "expected_module": "kaios.hooks.cli",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return FAILURE
    entry = getattr(hooks_cli, "main", None)
    if entry is None:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": "HooksUnavailable",
                    "message": "kaios.hooks.cli has no main(argv) entry point",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        return FAILURE
    try:
        result = entry(rest)
    except TypeError:
        result = entry()
    return int(result or OK)


# ---------------------------------------------------------------- handlers


def _paths(args, paths: Paths) -> int:
    data = paths.to_dict()
    lines = ["# kaios paths", "", "| name | value |", "|---|---|"]
    for key in sorted(data):
        lines.append("| %s | `%s` |" % (key, data[key]))
    emit(data, "\n".join(lines) + "\n", args.md)
    return OK


def _doctor(args, paths: Paths) -> int:
    report = doctor_mod.run(paths)
    emit(report, doctor_mod.to_markdown(report), args.md)
    return OK if report["ok"] else FAILURE


def _resolve_isa_path(given: str | None, paths: Paths) -> Path:
    if given:
        target = Path(given).expanduser()
        if not target.is_file():
            raise FileNotFoundError("no ISA at %s" % target)
        return target
    active = isa_mod.find_active(paths)
    if active is None:
        raise FileNotFoundError("no active ISA; pass a path or scaffold one")
    return active


def _isa(args, paths: Paths) -> int:
    command = getattr(args, "command", None)
    if command is None:
        raise _Usage("kaios isa needs a command: scaffold, check, frontier, status, render, list, sync")

    if command == "scaffold":
        paths.ensure()
        written = isa_mod.scaffold(
            slug=args.slug,
            goal=args.goal,
            paths=paths,
            project=args.project,
            task=args.task,
            dest=args.dest,
            overwrite=args.overwrite,
        )
        parsed = isa_mod.parse(written)
        payload = {"ok": True, "path": str(written), "status": isa_mod.status(parsed)}
        emit(payload, "Wrote `%s`.\n" % written, args.md)
        return OK

    if command == "list":
        entries = isa_mod.registry(paths)
        lines = ["# ISAs", "", "| slug | phase | progress | open | path |", "|---|---|---|---|---|"]
        for entry in entries:
            lines.append(
                "| %s | %s | %s | %s | `%s` |"
                % (
                    entry.get("slug"),
                    entry.get("phase"),
                    entry.get("progress"),
                    entry.get("claims_open"),
                    entry.get("path"),
                )
            )
        if not entries:
            lines.append("| (none) | - | - | - | - |")
        emit({"count": len(entries), "isas": entries}, "\n".join(lines) + "\n", args.md)
        return OK

    target = _resolve_isa_path(getattr(args, "path", None), paths)
    parsed = isa_mod.parse(target)

    if command == "check":
        findings = isa_mod.check(parsed)
        errors = isa_mod.errors(findings)
        payload = {
            "path": str(target),
            "ok": not errors,
            "errors": len(errors),
            "warnings": len(findings) - len(errors),
            "findings": [f.to_dict() for f in findings],
        }
        lines = [
            "# isa check",
            "",
            "`%s` — %s (%d error(s), %d warning(s))"
            % (target, "OK" if not errors else "FAILED", payload["errors"], payload["warnings"]),
            "",
        ]
        if findings:
            lines += ["| level | code | message |", "|---|---|---|"]
            for finding in findings:
                lines.append("| %s | %s | %s |" % (finding.level, finding.code, finding.message))
            lines.append("")
        emit(payload, "\n".join(lines), args.md)
        return OK if not errors else FAILURE

    if command == "frontier":
        claims = isa_mod.frontier(parsed)
        payload = {
            "path": str(target),
            "count": len(claims),
            "frontier": [c.to_dict() for c in claims],
        }
        lines = ["# frontier", ""]
        lines += ["- %s: %s" % (c.id, c.text) for c in claims] or ["- nothing takeable"]
        emit(payload, "\n".join(lines) + "\n", args.md)
        return OK

    if command == "status":
        info = isa_mod.status(parsed)
        emit(info, isa_mod.render(parsed), args.md)
        return OK

    if command == "render":
        markdown = isa_mod.render(parsed)
        if args.md:
            sys.stdout.write(markdown if markdown.endswith("\n") else markdown + "\n")
        else:
            emit({"path": str(target), "markdown": markdown})
        return OK

    if command == "sync":
        paths.ensure()
        entry = isa_mod.sync(paths, target)
        emit({"ok": True, "entry": entry}, "Registered `%s`.\n" % target, args.md)
        return OK

    raise _Usage("unknown isa command %r" % command)


def _parse_meta(raw: str | None) -> dict:
    if not raw:
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--meta must be a JSON object")
    return data


def _memory(args, paths: Paths) -> int:
    command = getattr(args, "command", None)
    if command is None:
        raise _Usage("kaios memory needs a command: capture, search, digest, health, hot, knowledge")
    paths.ensure()

    if command == "capture":
        record = memory_mod.capture(paths, args.kind, args.text, _parse_meta(args.meta))
        emit({"ok": True, "record": record, "path": str(paths.captures)}, "Captured.\n", args.md)
        return OK

    if command == "search":
        hits = memory_mod.search(paths, args.query, args.limit)
        lines = ["# memory search", "", "%d hit(s) for %r" % (len(hits), args.query), ""]
        for hit in hits:
            lines.append("- [%s] %s" % (hit.get("source"), hit.get("text")))
        emit({"query": args.query, "count": len(hits), "hits": hits}, "\n".join(lines) + "\n", args.md)
        return OK

    if command == "digest":
        markdown = memory_mod.digest(paths, args.since)
        if args.md:
            sys.stdout.write(markdown if markdown.endswith("\n") else markdown + "\n")
        else:
            emit({"since": args.since, "markdown": markdown})
        return OK

    if command == "health":
        report = memory_mod.health(paths)
        lines = ["# memory health", "", "| field | value |", "|---|---|"]
        for key in sorted(report):
            lines.append("| %s | %s |" % (key, report[key]))
        emit(report, "\n".join(lines) + "\n", args.md)
        return OK

    if command == "hot":
        block = memory_mod.hot_layer(paths)
        if args.md:
            sys.stdout.write(block if block.endswith("\n") else block + "\n")
        else:
            emit({"hot_layer": block, "chars": len(block)})
        return OK

    if command == "knowledge":
        sub = getattr(args, "subcommand", None)
        if sub == "add":
            written = memory_mod.knowledge_add(paths, args.title, args.body, args.tags, args.kind)
            emit({"ok": True, "path": str(written)}, "Wrote `%s`.\n" % written, args.md)
            return OK
        if sub == "find":
            hits = memory_mod.knowledge_find(paths, args.query, args.limit)
            lines = ["# knowledge", "", "%d note(s)" % len(hits), ""]
            for hit in hits:
                lines.append("- %s — %s" % (hit.get("title"), hit.get("excerpt")))
            emit({"count": len(hits), "notes": hits}, "\n".join(lines) + "\n", args.md)
            return OK
        raise _Usage("kaios memory knowledge needs add or find")

    raise _Usage("unknown memory command %r" % command)


def _ledger(args, paths: Paths) -> int:
    command = getattr(args, "command", None)
    if command is None:
        raise _Usage("kaios ledger needs a command: version, record, log")
    paths.ensure()

    if command == "version":
        if args.action == "bump":
            result = ledger_mod.bump(args.part, paths=paths)
            emit(
                result,
                "Bumped %s to **%s** (`%s`).\n" % (args.part, result["version"], result["file"]),
                args.md,
            )
            return OK
        current = ledger_mod.version(paths)
        emit(
            {"version": current, "file": str(ledger_mod.version_file(paths))},
            "KaiOS **%s**\n" % current,
            args.md,
        )
        return OK

    if command == "record":
        entry = ledger_mod.record(args.kind, args.summary, _parse_meta(args.meta), paths=paths)
        emit({"ok": True, "entry": entry}, "Recorded.\n", args.md)
        return OK

    if command == "log":
        entries = ledger_mod.log(args.limit, paths=paths)
        lines = ["# ledger", "", "| ts | kind | version | summary |", "|---|---|---|---|"]
        for entry in entries:
            lines.append(
                "| %s | %s | %s | %s |"
                % (entry.get("ts"), entry.get("kind"), entry.get("version"), entry.get("summary"))
            )
        if not entries:
            lines.append("| (empty) | - | - | - |")
        emit({"count": len(entries), "entries": entries}, "\n".join(lines) + "\n", args.md)
        return OK

    raise _Usage("unknown ledger command %r" % command)


def _models(args, paths: Paths) -> int:
    command = getattr(args, "command", None)
    if command is None:
        raise _Usage("kaios models needs a command: show, set, apply")

    if command == "show":
        report = models_mod.show(paths)
        lines = ["# models", "", "Source: `%s`" % report["source"], "", "| role | purpose | models |", "|---|---|---|"]
        for role in sorted(report["roles"]):
            entry = report["roles"][role]
            lines.append(
                "| %s | %s | %s |" % (role, entry.get("purpose") or "-", ", ".join(entry["models"]) or "-")
            )
        lines.append("")
        emit(report, "\n".join(lines), args.md)
        return OK

    if command == "set":
        paths.ensure()
        result = models_mod.set_role(args.role, args.models, paths=paths)
        emit(result, "Set **%s** to %s.\n" % (result["role"], ", ".join(result["models"])), args.md)
        return OK

    if command == "apply":
        result = models_mod.apply(args.agents_dir, paths=paths, dry_run=args.dry_run)
        lines = [
            "# models apply",
            "",
            "%d changed, %d unchanged, %d skipped, %d error(s) in `%s`"
            % (
                len(result["changed"]),
                len(result["unchanged"]),
                len(result["skipped"]),
                len(result["errors"]),
                result["agents_dir"],
            ),
            "",
        ]
        for item in result["changed"]:
            lines.append("- %s -> %s (%s)" % (item["file"], ", ".join(item["models"]), item["role"]))
        lines.append("")
        emit(result, "\n".join(lines), args.md)
        return FAILURE if result["errors"] else OK

    raise _Usage("unknown models command %r" % command)


def _setup(args, paths: Paths) -> int:
    command = getattr(args, "command", None)
    if command is None:
        raise _Usage("kaios setup needs a command: detect, write-config, render")

    if command == "detect":
        report = setup_mod.detect(paths)
        lines = ["# setup detect", "", "| tool | found | version |", "|---|---|---|"]
        for name in sorted(report["tools"]):
            info = report["tools"][name]
            lines.append(
                "| %s | %s | %s |"
                % (name, "yes" if info.get("found") else "no", info.get("version") or "-")
            )
        lines += [
            "",
            "MCP config: %s" % ("present" if report["mcp_json"]["present"] else "absent"),
            "",
        ]
        emit(report, "\n".join(lines), args.md)
        return OK

    if command == "write-config":
        paths.ensure()
        stored = setup_mod.write_config(args.config, paths=paths)
        emit(
            {"ok": True, "path": str(paths.config_file), "config": stored},
            "Wrote `%s`.\n" % paths.config_file,
            args.md,
        )
        return OK

    if command == "render":
        result = setup_mod.render(args.answers, paths=paths, write=not args.dry_run)
        lines = ["# setup render", "", "%d file(s) written" % len(result["written"]), ""]
        for path in result["written"]:
            lines.append("- `%s`" % path)
        lines.append("")
        emit(result, "\n".join(lines), args.md)
        return OK

    raise _Usage("unknown setup command %r" % command)


def _integrity(args, paths: Paths) -> int:
    command = getattr(args, "command", None)
    if command is None:
        raise _Usage("kaios integrity needs a check: %s" % ", ".join(integrity.CHECKS))

    root = args.root or (paths.repo if paths.repo is not None else Path.cwd())
    kwargs: dict = {}
    if command == "containment":
        if getattr(args, "terms", None):
            kwargs["terms_file"] = args.terms
        if getattr(args, "extra_terms", None):
            kwargs["extra_terms_file"] = args.extra_terms

    report = integrity.run(command, root, **kwargs)
    emit(report, integrity.to_markdown(report), args.md)
    return OK if report["ok"] else FAILURE
