#!/usr/bin/env python3
"""Wrap the Databricks CLI with argument arrays, JSON output and two safety gates.

Every call is ``subprocess.run([...])`` with a list, never a command string, so a
path or an identifier containing a space or a quote cannot turn into extra
arguments. Two operations refuse to proceed without an explicit approval flag:
deploying a bundle to a production target, and running destructive SQL.

Exit codes:
  0  the command succeeded
  1  the CLI ran and returned a failure
  2  the CLI is not installed, or usage was wrong
  3  approval required and not given
"""

import argparse
import json
import re
import shutil
import subprocess
import sys

CLI = "databricks"
INSTALL_DOC = "https://docs.databricks.com/dev-tools/cli/install.html"
PROD_TARGET = re.compile(r"prod", re.IGNORECASE)
DESTRUCTIVE_SQL = re.compile(
    r"\b(drop\s+(table|view|schema|database|catalog|volume|function)"
    r"|truncate\s+table"
    r"|delete\s+from"
    r"|alter\s+table\s+\S+\s+drop"
    r"|vacuum\b"
    r"|replace\s+table)\b",
    re.IGNORECASE,
)
EXIT_OK = 0
EXIT_FAIL = 1
EXIT_NO_CLI = 2
EXIT_APPROVAL = 3


def emit(payload, as_json, human=None):
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print(human if human is not None else json.dumps(payload, indent=2))


def cli_missing(as_json):
    payload = {"error": "databricks CLI not found", "install": INSTALL_DOC}
    emit(payload, as_json, "error: databricks CLI not found. Install: %s" % INSTALL_DOC)
    return EXIT_NO_CLI


def run_cli(args, profile="", timeout=300):
    """Run the Databricks CLI with an argument array. Never a shell string."""
    command = [CLI]
    if profile:
        command += ["--profile", profile]
    command += list(args)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"found": False, "command": command}
    except subprocess.TimeoutExpired:
        return {
            "found": True,
            "command": command,
            "returncode": 124,
            "stdout": "",
            "stderr": "timed out after %ds" % timeout,
        }
    return {
        "found": True,
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout or "",
        "stderr": completed.stderr or "",
    }


def shape(result, label):
    """Normalise a CLI result into a reportable payload."""
    payload = {
        "action": label,
        "command": result.get("command", []),
        "returncode": result.get("returncode"),
        "ok": result.get("returncode") == 0,
    }
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    if stdout.strip():
        try:
            payload["data"] = json.loads(stdout)
        except ValueError:
            payload["stdout"] = stdout.strip()
    if stderr.strip():
        payload["stderr"] = stderr.strip()
    return payload


def human_lines(payload):
    lines = ["%s: %s" % (payload["action"], "ok" if payload["ok"] else "FAILED")]
    lines.append("  command: %s" % " ".join(payload.get("command", [])))
    if "data" in payload:
        lines.append(json.dumps(payload["data"], indent=2))
    if "stdout" in payload:
        lines.append(payload["stdout"])
    if payload.get("stderr"):
        lines.append("  stderr: %s" % payload["stderr"])
    return "\n".join(lines)


def finish(result, label, as_json):
    if not result.get("found", True):
        return cli_missing(as_json)
    payload = shape(result, label)
    emit(payload, as_json, human_lines(payload))
    return EXIT_OK if payload["ok"] else EXIT_FAIL


# ---------------------------------------------------------------- subcommands


def do_auth_check(args):
    result = run_cli(["current-user", "me", "-o", "json"], args.profile, args.timeout)
    return finish(result, "auth-check", args.json)


def do_workspace_ls(args):
    call = ["workspace", "list", args.path, "-o", "json"]
    if args.absolute:
        call.append("--absolute")
    return finish(run_cli(call, args.profile, args.timeout), "workspace-ls", args.json)


def do_jobs_list(args):
    call = ["jobs", "list", "-o", "json"]
    if args.limit:
        call += ["--limit", str(args.limit)]
    return finish(run_cli(call, args.profile, args.timeout), "jobs-list", args.json)


def do_jobs_run(args):
    body = {"job_id": args.job_id}
    if args.param:
        params = {}
        for item in args.param:
            if "=" not in item:
                emit(
                    {"error": "param must be key=value", "got": item},
                    args.json,
                    "error: param must be key=value, got %r" % item,
                )
                return EXIT_NO_CLI
            key, _, value = item.partition("=")
            params[key] = value
        body["notebook_params"] = params
        call = ["jobs", "run-now", "--json", json.dumps(body), "-o", "json"]
    else:
        call = ["jobs", "run-now", str(args.job_id), "-o", "json"]
    return finish(run_cli(call, args.profile, args.timeout), "jobs-run", args.json)


def do_bundle_validate(args):
    call = ["bundle", "validate"]
    if args.target:
        call += ["--target", args.target]
    return finish(run_cli(call, args.profile, args.timeout), "bundle-validate", args.json)


def do_bundle_deploy(args):
    # <!-- keep: safety-gate -->  production deploys need an explicit approval flag.
    if PROD_TARGET.search(args.target) and not args.approved:
        payload = {
            "action": "bundle-deploy",
            "target": args.target,
            "requires_approval": True,
            "reason": "target looks like production; rerun with --approved once a human has agreed",
            "ok": False,
        }
        emit(
            payload,
            args.json,
            "REFUSED: target %r looks like production. Requires approval: rerun with --approved."
            % args.target,
        )
        return EXIT_APPROVAL
    call = ["bundle", "deploy", "--target", args.target]
    if args.force_lock:
        call.append("--force-lock")
    return finish(run_cli(call, args.profile, args.timeout), "bundle-deploy", args.json)


def do_sql_query(args):
    # <!-- keep: safety-gate -->  destructive statements need an explicit approval flag.
    if DESTRUCTIVE_SQL.search(args.sql) and not args.approved:
        payload = {
            "action": "sql-query",
            "requires_approval": True,
            "reason": "statement drops, truncates, replaces or deletes data; rerun with --approved once a human has agreed",
            "ok": False,
        }
        emit(
            payload,
            args.json,
            "REFUSED: destructive statement. Requires approval: rerun with --approved.",
        )
        return EXIT_APPROVAL
    body = {
        "warehouse_id": args.warehouse_id,
        "statement": args.sql,
        "wait_timeout": args.wait_timeout,
        "on_wait_timeout": "CONTINUE",
    }
    if args.catalog:
        body["catalog"] = args.catalog
    if args.schema:
        body["schema"] = args.schema
    if args.param:
        parameters = []
        for item in args.param:
            if "=" not in item:
                emit(
                    {"error": "param must be name=value", "got": item},
                    args.json,
                    "error: param must be name=value, got %r" % item,
                )
                return EXIT_NO_CLI
            name, _, value = item.partition("=")
            parameters.append({"name": name, "value": value})
        body["parameters"] = parameters
    call = ["api", "post", "/api/2.0/sql/statements", "--json", json.dumps(body)]
    return finish(run_cli(call, args.profile, args.timeout), "sql-query", args.json)


def do_notebook_export(args):
    call = ["workspace", "export", args.path, "--format", args.format]
    if args.file:
        call += ["--file", args.file]
    return finish(run_cli(call, args.profile, args.timeout), "notebook-export", args.json)


# ---------------------------------------------------------------- arg parsing


def build_parser():
    parser = argparse.ArgumentParser(
        prog="databricks_tool.py",
        description="Safe, JSON-shaped wrappers around the Databricks CLI.",
        epilog="Production bundle deploys and destructive SQL exit 3 unless --approved.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", default="", help="Databricks CLI profile name")
    common.add_argument("--json", action="store_true", help="emit the result as JSON")
    common.add_argument(
        "--timeout", type=int, default=300, help="seconds before the call is abandoned"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    auth = sub.add_parser(
        "auth-check", parents=[common], help="who am I, against which workspace"
    )
    auth.set_defaults(func=do_auth_check)

    ls = sub.add_parser("workspace-ls", parents=[common], help="list a workspace path")
    ls.add_argument("path", help="workspace path, e.g. /Workspace/Shared/project")
    ls.add_argument("--absolute", action="store_true", help="print absolute paths")
    ls.set_defaults(func=do_workspace_ls)

    jobs = sub.add_parser("jobs-list", parents=[common], help="list jobs")
    jobs.add_argument("--limit", type=int, default=0, help="maximum jobs to return")
    jobs.set_defaults(func=do_jobs_list)

    run = sub.add_parser("jobs-run", parents=[common], help="trigger a job run now")
    run.add_argument("job_id", help="numeric job id")
    run.add_argument(
        "--param",
        action="append",
        default=[],
        help="notebook parameter as key=value (repeatable)",
    )
    run.set_defaults(func=do_jobs_run)

    validate = sub.add_parser(
        "bundle-validate", parents=[common], help="validate the bundle in this directory"
    )
    validate.add_argument("--target", default="", help="bundle target to validate")
    validate.set_defaults(func=do_bundle_validate)

    deploy = sub.add_parser(
        "bundle-deploy", parents=[common], help="deploy the bundle to a target"
    )
    deploy.add_argument("--target", required=True, help="bundle target name")
    deploy.add_argument(
        "--approved",
        action="store_true",
        help="a human has approved this production deploy",
    )
    deploy.add_argument(
        "--force-lock", action="store_true", help="take the deployment lock by force"
    )
    deploy.set_defaults(func=do_bundle_deploy)

    query = sub.add_parser("sql-query", parents=[common], help="run a SQL statement")
    query.add_argument("--warehouse-id", required=True, help="SQL warehouse id")
    query.add_argument("--sql", required=True, help="the statement; parameterise it")
    query.add_argument(
        "--param",
        action="append",
        default=[],
        help="named parameter as name=value (repeatable); use :name in the statement",
    )
    query.add_argument("--catalog", default="", help="catalog to run against")
    query.add_argument("--schema", default="", help="schema to run against")
    query.add_argument("--wait-timeout", default="30s", help="server wait timeout")
    query.add_argument(
        "--approved", action="store_true", help="a human has approved a destructive statement"
    )
    query.set_defaults(func=do_sql_query)

    export = sub.add_parser(
        "notebook-export", parents=[common], help="export a notebook or file"
    )
    export.add_argument("path", help="workspace path of the notebook")
    export.add_argument(
        "--format",
        default="SOURCE",
        choices=["SOURCE", "HTML", "JUPYTER", "DBC", "AUTO"],
        help="export format (default SOURCE)",
    )
    export.add_argument("--file", default="", help="write to this local path")
    export.set_defaults(func=do_notebook_export)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if shutil.which(CLI) is None:
        return cli_missing(args.json)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
