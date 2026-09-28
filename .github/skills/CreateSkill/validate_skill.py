#!/usr/bin/env python3
"""Validate a skill directory against the KaiOS skill contract.

Checks the frontmatter schema (name, description, optional argument-hint), the
required routing strings, the ideal-state writing standard (no long step
choreography without a keep tag), and the bundled-tool rules (``--help``
support, no shell interpretation).

Exit codes: 0 clean, 1 findings, 2 usage or unreadable input.
"""

import argparse
import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONT_KEY = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*)\s*:\s*(?P<value>.*)$")
NUMBERED = re.compile(r"^\s{0,3}(\d{1,2})[.)]\s+\S")
# Built at runtime so this file never contains the literal it bans.
SHELL_FLAG = "shell" + "=" + "True"
KEEP_TAG = re.compile(r"<!--\s*keep\s*:\s*[a-z0-9-]+\s*-->", re.IGNORECASE)
# Text IO whose default encoding is locale-dependent. Windows-first means utf-8 must be explicit.
TEXT_IO = re.compile(
    r"(?:\.(?:read_text|write_text)\s*\(|(?<![\w.])open\s*\([^)]*[\"']\s*[rwax][^\"']*[\"'])"
)
MAX_STEPS = 8
MAX_NAME = 64
MAX_DESCRIPTION = 1024
KNOWN_KEYS = {
    "name",
    "description",
    "argument-hint",
    "user-invocable",
    "disable-model-invocation",
}


def split_frontmatter(text):
    """Return (frontmatter_lines, body_lines, error)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [], lines, "no frontmatter: first line must be ---"
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index], lines[index + 1 :], None
    return [], lines, "frontmatter opened but never closed"


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(front_lines):
    """Flat key/value parse. Folds continuation lines into the previous value."""
    data = {}
    order = []
    current = None
    for raw in front_lines:
        if not raw.strip():
            continue
        match = FRONT_KEY.match(raw)
        if match and not raw.startswith((" ", "\t")):
            current = match.group("key")
            data[current] = unquote(match.group("value"))
            order.append(current)
        elif current is not None:
            data[current] = (data[current] + " " + raw.strip()).strip()
    return data, order


def find_step_runs(body_lines):
    """Return (start_line, length) for each run of consecutive numbered items."""
    runs = []
    start = None
    count = 0
    last_item = -10
    for index, line in enumerate(body_lines):
        if NUMBERED.match(line):
            if start is None or index - last_item > 4:
                if start is not None and count > 0:
                    runs.append((start, count))
                start = index
                count = 0
            count += 1
            last_item = index
    if start is not None and count > 0:
        runs.append((start, count))
    return runs


def has_keep_tag(body_lines, run_start, window=10):
    lower = max(0, run_start - window)
    for line in body_lines[lower : run_start + 1]:
        if KEEP_TAG.search(line):
            return True
    return False


def check_skill_md(path, findings, warnings):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        findings.append("cannot read SKILL.md: %s" % exc)
        return {}
    front_lines, body_lines, error = split_frontmatter(text)
    if error:
        findings.append(error)
        return {}
    data, order = parse_frontmatter(front_lines)

    name = data.get("name", "")
    if not name:
        findings.append("frontmatter is missing name")
    else:
        if not NAME_RE.match(name):
            findings.append("name must be lowercase with hyphens only, got %r" % name)
        if len(name) > MAX_NAME:
            findings.append("name is %d chars, limit %d" % (len(name), MAX_NAME))

    description = data.get("description", "")
    if not description:
        findings.append("frontmatter is missing description")
    else:
        if len(description) > MAX_DESCRIPTION:
            findings.append(
                "description is %d chars, limit %d" % (len(description), MAX_DESCRIPTION)
            )
        if "USE WHEN" not in description:
            findings.append("description must contain the literal USE WHEN")
        if "NOT FOR" not in description:
            findings.append("description must contain the literal NOT FOR")

    for key in order:
        if key not in KNOWN_KEYS:
            warnings.append("unknown frontmatter key %r" % key)

    body = "\n".join(body_lines)
    if not body.strip():
        findings.append("body is empty")
    if "USE WHEN" not in body and "## USE WHEN" not in body:
        warnings.append("body does not restate USE WHEN")
    if "NOT FOR" not in body:
        warnings.append("body does not restate NOT FOR")
    if not re.search(r"done looks like", body, re.IGNORECASE):
        warnings.append("body states no done-criteria section")

    for start, length in find_step_runs(body_lines):
        if length > MAX_STEPS and not has_keep_tag(body_lines, start):
            findings.append(
                "step choreography: %d numbered steps starting near body line %d; "
                "cap is %d unless a keep comment sits within the 10 lines above"
                % (length, start + 1, MAX_STEPS)
            )
    return data


def check_tools(directory, findings, warnings):
    tools = []
    for root, _dirs, files in os.walk(directory):
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(root, filename)
            tools.append(os.path.relpath(path, directory))
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    source = handle.read()
            except OSError as exc:
                findings.append("cannot read %s: %s" % (filename, exc))
                continue
            if SHELL_FLAG in source:
                findings.append("%s enables shell interpretation" % filename)
            if "--help" not in source and "argparse" not in source:
                findings.append("%s exposes no --help" % filename)
            for lineno, line in enumerate(source.splitlines(), start=1):
                if "encoding" in line:
                    continue
                if TEXT_IO.search(line):
                    warnings.append(
                        "%s:%d reads or writes text without an explicit encoding; on "
                        "Windows the default is the ANSI code page" % (filename, lineno)
                    )
    return tools


def link_resolves(containing_dir, target, base):
    """True when the link resolves next to its file, or from the repository root."""
    if os.path.exists(os.path.normpath(os.path.join(containing_dir, target))):
        return True
    if base and not os.path.isabs(target):
        return os.path.exists(os.path.normpath(os.path.join(base, target)))
    return False


def repo_root(start):
    """Nearest ancestor holding a .git entry, or None."""
    current = os.path.abspath(start)
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def check_links(directory, findings):
    """Every markdown file in the skill, not only SKILL.md. A dead link in a
    reference file is just as broken and is the one a doc-integrity gate finds."""
    base = repo_root(directory)
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for filename in sorted(files):
            if not filename.endswith(".md"):
                continue
            path = os.path.join(root, filename)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    text = handle.read()
            except OSError:
                continue
            for target in re.findall(r"\]\((?!https?:|mailto:|#)([^)#]+)\)", text):
                target = target.strip()
                if not target or target.startswith("<"):
                    continue
                # A link resolves against the file that contains it, or, because
                # docs here write paths like .github/SYSTEM/DOCUMENTATION/X.md
                # freely, against the repository root. Either form counts as
                # resolved.
                if link_resolves(root, target, base):
                    continue
                findings.append(
                    "broken relative link in %s: %s"
                    % (os.path.relpath(path, directory), target)
                )


def validate(directory):
    findings = []
    warnings = []
    if not os.path.isdir(directory):
        return {"path": directory, "findings": ["not a directory"], "warnings": []}
    skill_md = os.path.join(directory, "SKILL.md")
    if not os.path.isfile(skill_md):
        findings.append("SKILL.md is missing")
        return {"path": directory, "findings": findings, "warnings": warnings}
    data = check_skill_md(skill_md, findings, warnings)
    tools = check_tools(directory, findings, warnings)
    check_links(directory, findings)

    dirname = os.path.basename(os.path.normpath(directory))
    name = data.get("name", "")
    if name and dirname:
        if dirname.replace("-", "").replace("_", "").lower() != name.replace("-", ""):
            warnings.append(
                "directory %r and name %r do not agree once case and hyphens are dropped"
                % (dirname, name)
            )
    return {
        "path": directory,
        "name": name,
        "tools": tools,
        "findings": findings,
        "warnings": warnings,
    }


def cross_check(results):
    """Names must be globally unique: two skills sharing a name make routing a coin flip."""
    seen = {}
    for result in results:
        name = result.get("name") or ""
        if name:
            seen.setdefault(name, []).append(result["path"])
    for name, paths in seen.items():
        if len(paths) > 1:
            for result in results:
                if result.get("name") == name:
                    others = [p for p in paths if p != result["path"]]
                    result["findings"].append(
                        "duplicate skill name %r, also declared by: %s"
                        % (name, ", ".join(sorted(others)))
                    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="validate_skill.py",
        description="Validate one or more skill directories against the KaiOS contract.",
    )
    parser.add_argument("directories", nargs="+", help="skill directories to validate")
    parser.add_argument("--json", action="store_true", help="emit results as JSON")
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as findings"
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    results = [validate(directory) for directory in args.directories]
    cross_check(results)
    failed = 0
    for result in results:
        problems = len(result["findings"])
        if args.strict:
            problems += len(result["warnings"])
        if problems:
            failed += 1
    if args.json:
        print(json.dumps({"results": results, "failed": failed}, indent=2))
    else:
        for result in results:
            status = "FAIL" if result["findings"] else "PASS"
            if args.strict and result["warnings"]:
                status = "FAIL"
            print("%s  %s" % (status, result["path"]))
            for item in result["findings"]:
                print("      finding: %s" % item)
            for item in result["warnings"]:
                print("      warn:    %s" % item)
        print("")
        print("%d of %d skills failed" % (failed, len(results)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
