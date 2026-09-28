#!/usr/bin/env python3
"""Deterministic helper for the create-workflow skill.

Three kinds of workflow, one tool: a KaiOS agent workflow (stages run by
Copilot agents), a GitHub Actions workflow, and a Databricks job shipped as a
bundle resource. The tool lists the kinds, prints the interview question bank,
scaffolds the artifacts from an answers file, validates any of the three shapes,
renders the stage table used in a skill body, and tracks runs in KAIOS_HOME.

Standard library only. No third-party YAML: this module carries a small block
serializer and a matching subset parser so a written file can be read back and
checked. Exit codes: 0 ok, 1 invalid or failed, 2 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOL_VERSION = "1.0.0"

ROLES = ("max", "high", "medium", "cross", "third", "research")
GATES = ("auto", "ask", "evidence")
KNOWN_AGENTS = {
    "Planner": "max",
    "Builder": "high",
    "Reviewer": "max",
    "Auditor": "cross",
    "Researcher": "research",
    "Verifier": "high",
    "ThirdOpinion": "third",
    "DatabricksOps": "high",
    "Kai": "max",
}
DB_TASK_TYPES = (
    "notebook_task",
    "python_wheel_task",
    "sql_task",
    "spark_python_task",
    "pipeline_task",
    "run_job_task",
)
TYPE_ALIASES = {
    "notebook": "notebook_task",
    "python_wheel": "python_wheel_task",
    "wheel": "python_wheel_task",
    "sql": "sql_task",
    "spark_python": "spark_python_task",
    "pipeline": "pipeline_task",
    "run_job": "run_job_task",
}
STATE_TOKEN = "$KAIOS_HOME/MEMORY/STATE/workflows.json"
ACTIONS_TEMPLATES = ("python-tests", "databricks-bundle-deploy", "scheduled-job")

KINDS = [
    {
        "kind": "agent",
        "title": "KaiOS agent workflow",
        "default": True,
        "use_when": "Several stages of thinking or building need to run in order, "
        "each by a different role, with gates between them.",
        "artifacts": [
            ".github/skills/<Name>/SKILL.md",
            ".github/skills/<Name>/workflow.json",
            ".github/agents/<Name>.agent.md",
        ],
        "runs_on": "Copilot in the editor: pick the orchestrator agent, or type /<name>.",
    },
    {
        "kind": "actions",
        "title": "GitHub Actions workflow",
        "default": False,
        "use_when": "Something must run on a push, a pull request, a schedule, or a "
        "manual dispatch, on GitHub's runners, with no human in the loop.",
        "artifacts": [".github/workflows/<name>.yml"],
        "runs_on": "GitHub runners, on the events in the on: block.",
    },
    {
        "kind": "databricks",
        "title": "Databricks job workflow",
        "default": False,
        "use_when": "Tasks must run on Databricks compute with dependencies between "
        "them, deployed through a bundle.",
        "artifacts": ["resources/<name>.job.yml", "databricks.yml (only when absent)"],
        "runs_on": "Databricks Jobs, deployed with the Databricks CLI bundle commands.",
    },
]

QUESTIONS = {
    "agent": [
        {
            "id": "goal",
            "ask": "In one sentence, what does this workflow make true that is not true now?",
            "why": "The goal is what every stage is measured against. Without it the stages "
            "become a procedure nobody can grade.",
            "key": "goal",
        },
        {
            "id": "name",
            "ask": "What should the workflow be called, in PascalCase?",
            "why": "The name becomes the skill directory, the skill name in lowercase-hyphen, "
            "and the orchestrator agent file.",
            "key": "name",
        },
        {
            "id": "stages",
            "ask": "Walk me through the stages in order. For each: a short title and the role "
            "that should run it.",
            "why": "Stages are the unit of handoff. One stage per change of role or change of "
            "artifact; anything finer is choreography.",
            "key": "stages",
        },
        {
            "id": "io",
            "ask": "For each stage, what goes in and what comes out?",
            "why": "A stage whose output is not named cannot hand off, and the next stage has "
            "nothing to check.",
            "key": "stages[].input / stages[].output",
        },
        {
            "id": "done",
            "ask": "For each stage, how would someone else prove the stage is done? Name the "
            "observation, not the feeling.",
            "why": "These become done_criteria. Falsifiable criteria are the only thing that "
            "stops a stage declaring victory.",
            "key": "stages[].done_criteria",
        },
        {
            "id": "gates",
            "ask": "Which stages may pass on their own, which must stop and ask a human, and "
            "which must show tool output before passing?",
            "why": "Gates are auto, ask, and evidence. At least one evidence gate is required "
            "or nothing in the flow is ever verified.",
            "key": "stages[].gate",
        },
        {
            "id": "after",
            "ask": "Does any stage depend on more than the one before it?",
            "why": "The after edges make the order explicit and let independent stages run in "
            "parallel. They must stay acyclic.",
            "key": "stages[].after",
        },
        {
            "id": "anti",
            "ask": "What must never become true while this workflow runs?",
            "why": "Anti-claims catch the failure that passing tests will not: the shortcut, "
            "the self-review, the silent scope change.",
            "key": "anti_claims",
        },
        {
            "id": "review",
            "ask": "Who checks the builder's work, and is it a different vendor family?",
            "why": "A stage reviewing its own family's output shares its blind spots. The cross "
            "and third roles exist for this.",
            "key": "stages[].role",
        },
        {
            "id": "entry",
            "ask": "How will you start it: the agent picker, or the slash command?",
            "why": "Decides whether the orchestrator agent or the skill is the front door, and "
            "what the argument hint should say.",
            "key": "entry",
        },
    ],
    "actions": [
        {
            "id": "purpose",
            "ask": "What should happen automatically, and what breaks today because it does not?",
            "why": "An Actions workflow with no failure it prevents is decoration.",
            "key": "display_name",
        },
        {
            "id": "template",
            "ask": "Is this a test run, a bundle deploy, or a scheduled task?",
            "why": "Picks the template: python-tests, databricks-bundle-deploy, or scheduled-job.",
            "key": "template",
        },
        {
            "id": "trigger",
            "ask": "What triggers it: push, pull request, a cron schedule, or a manual dispatch?",
            "why": "The on: block is the whole contract with GitHub. Everything else is steps.",
            "key": "on / branches / cron",
        },
        {
            "id": "runner",
            "ask": "Which runner, and does it need a specific Python version?",
            "why": "Runner and interpreter version decide whether the steps are portable or "
            "silently shell-specific.",
            "key": "runs_on / python_version",
        },
        {
            "id": "command",
            "ask": "What is the exact command that proves the job worked?",
            "why": "A workflow whose command cannot fail proves nothing. This is the falsifier.",
            "key": "test_command / command",
        },
        {
            "id": "secrets",
            "ask": "What credentials does it need, and are they repository secrets already?",
            "why": "Secrets belong in env, referenced by name, never interpolated into a run "
            "line where the log would print them.",
            "key": "env",
        },
        {
            "id": "target",
            "ask": "Does it touch a protected target such as production?",
            "why": "A prod job needs an environment for approval, or the workflow can deploy "
            "without anyone agreeing to it.",
            "key": "target",
        },
        {
            "id": "fail",
            "ask": "Who should notice when it fails, and how?",
            "why": "A red run nobody looks at is a disabled test with extra steps.",
            "key": "notify",
        },
    ],
    "databricks": [
        {
            "id": "purpose",
            "ask": "What does this job produce, and who consumes it?",
            "why": "Names the job and decides how loud failure needs to be.",
            "key": "job_name",
        },
        {
            "id": "bundle",
            "ask": "Which bundle does it belong to, and does a databricks.yml already exist?",
            "why": "The resource file is meaningless outside a bundle. A missing bundle root "
            "gets scaffolded with dev and prod targets.",
            "key": "bundle_name",
        },
        {
            "id": "tasks",
            "ask": "List the tasks in order, with a task_key for each.",
            "why": "task_key is the identity of a task; duplicates make the dependency graph "
            "ambiguous and the deploy rejects them.",
            "key": "tasks[].task_key",
        },
        {
            "id": "types",
            "ask": "For each task: notebook, Python wheel, or SQL?",
            "why": "Exactly one task type per task. Two types is a task that does not deploy.",
            "key": "tasks[].type",
        },
        {
            "id": "depends",
            "ask": "Which tasks wait on which?",
            "why": "depends_on must point at real task_keys and stay acyclic, or the job hangs "
            "at validate time.",
            "key": "tasks[].depends_on",
        },
        {
            "id": "schedule",
            "ask": "Does it run on a schedule, or only when triggered?",
            "why": "A scheduled job needs a quartz expression and an explicit timezone, or it "
            "drifts twice a year.",
            "key": "schedule",
        },
        {
            "id": "alerts",
            "ask": "Where should failure notifications go?",
            "why": "Jobs fail at night. The notification is the only reason anyone finds out.",
            "key": "email_notifications",
        },
        {
            "id": "prod",
            "ask": "Who is allowed to deploy this to prod, and through what?",
            "why": "The prod target should be reached through a reviewed pipeline with an "
            "approval gate, not from a laptop.",
            "key": "targets.prod",
        },
    ],
}


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def kaios_home() -> Path:
    raw = os.environ.get("KAIOS_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".kaios"


def state_path() -> Path:
    return kaios_home() / "MEMORY" / "STATE" / "workflows.json"


def emit(payload) -> None:
    print(json.dumps(payload, indent=2))


def slugify(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-").lower()


def titleize(value: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", slugify(value)) if w]
    if not words:
        return "Workflow"
    return " ".join([words[0].capitalize()] + words[1:])


def pascalize(value: str) -> str:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", str(value)) if w]
    if not words:
        return "Workflow"
    if len(words) == 1 and re.search(r"[a-z][A-Z]", words[0]):
        return words[0]
    return "".join(w[:1].upper() + w[1:] for w in words)


def read_utf8(path: Path) -> str:
    """Read a file as UTF-8. Never Path.read_text, whose default is the ANSI code page."""
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def write_utf8(path: Path, text: str) -> None:
    """Write a file as UTF-8 with newline endings, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def clip(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "."


def finding(code: str, message: str, where: str = "") -> dict:
    item = {"code": code, "message": message}
    if where:
        item["where"] = where
    return item


def find_cycle(edges: dict) -> list:
    """Return one cycle as a list of nodes, or an empty list when acyclic."""
    state = {}
    trail = []

    def visit(node):
        state[node] = 1
        trail.append(node)
        for dep in edges.get(node, []):
            if dep not in edges:
                continue
            mark = state.get(dep, 0)
            if mark == 1:
                return trail[trail.index(dep) :] + [dep]
            if mark == 0:
                found = visit(dep)
                if found:
                    return found
        state[node] = 2
        trail.pop()
        return []

    for node in edges:
        if state.get(node, 0) == 0:
            found = visit(node)
            if found:
                return found
    return []


# --------------------------------------------------------------------------
# YAML: block serializer
# --------------------------------------------------------------------------

_SPECIAL_HEAD = "-?:,[]{}#&*!|>'\"%@`"
_NUMBERISH = re.compile(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")
_RESERVED = ("true", "false", "null", "yes", "no", "on", "off", "~", "")


def _needs_quotes(text: str) -> bool:
    if text == "" or text.strip() != text:
        return True
    if text[0] in _SPECIAL_HEAD:
        return True
    if ": " in text or text.endswith(":") or " #" in text:
        return True
    if any(ch in text for ch in "*{}[]"):
        return True
    if text.lower() in _RESERVED:
        return True
    return bool(_NUMBERISH.match(text))


def _quote(text: str) -> str:
    out = text.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\t", "\\t")
    return '"' + out + '"'


def _scalar(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    text = str(value)
    return _quote(text) if _needs_quotes(text) else text


def _key(name) -> str:
    text = str(name)
    if text.lower() in ("on", "off", "yes", "no"):
        return text
    return _quote(text) if _needs_quotes(text) else text


def _block_marker(text: str) -> str:
    return "|" if text.endswith("\n") else "|-"


def _dump_block_scalar(pad: str, text: str, lines: list) -> None:
    for line in text.rstrip("\n").split("\n"):
        lines.append((pad + line).rstrip() if line.strip() else "")


def _dump(data, indent: int, lines: list) -> None:
    pad = " " * indent
    if isinstance(data, dict):
        for name, value in data.items():
            head = pad + _key(name)
            if isinstance(value, dict):
                if value:
                    lines.append(head + ":")
                    _dump(value, indent + 2, lines)
                else:
                    lines.append(head + ": {}")
            elif isinstance(value, (list, tuple)):
                if value:
                    lines.append(head + ":")
                    _dump(list(value), indent + 2, lines)
                else:
                    lines.append(head + ": []")
            elif isinstance(value, str) and "\n" in value:
                lines.append(head + ": " + _block_marker(value))
                _dump_block_scalar(" " * (indent + 2), value, lines)
            else:
                lines.append(head + ": " + _scalar(value))
    elif isinstance(data, (list, tuple)):
        for item in data:
            _dump_item(item, indent, lines)
    else:
        lines.append(pad + _scalar(data))


def _dump_item(item, indent: int, lines: list) -> None:
    pad = " " * indent
    if isinstance(item, (dict, list, tuple)) and item:
        sub: list = []
        _dump(item if isinstance(item, dict) else list(item), indent + 2, sub)
        sub[0] = pad + "- " + sub[0][indent + 2 :]
        lines.extend(sub)
    elif isinstance(item, dict):
        lines.append(pad + "- {}")
    elif isinstance(item, (list, tuple)):
        lines.append(pad + "- []")
    elif isinstance(item, str) and "\n" in item:
        lines.append(pad + "- " + _block_marker(item))
        _dump_block_scalar(" " * (indent + 2), item, lines)
    else:
        lines.append(pad + "- " + _scalar(item))


def dump_yaml(data) -> str:
    lines: list = []
    _dump(data, 0, lines)
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# YAML: subset parser (block mappings, block sequences, scalars, block text)
# --------------------------------------------------------------------------


class YamlError(Exception):
    pass


def _strip_comment(text: str) -> str:
    out: list = []
    quote = None
    escaped = False
    for ch in text:
        if quote:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\" and quote == '"':
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (not out or out[-1] == " "):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _unescape(body: str) -> str:
    table = {"n": "\n", "t": "\t", "\\": "\\", '"': '"', "'": "'", "/": "/", "0": "\0"}
    out: list = []
    idx = 0
    while idx < len(body):
        ch = body[idx]
        if ch == "\\" and idx + 1 < len(body):
            nxt = body[idx + 1]
            out.append(table.get(nxt, "\\" + nxt))
            idx += 2
        else:
            out.append(ch)
            idx += 1
    return "".join(out)


def _unquote(text: str) -> str:
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        body = text[1:-1]
        if text[0] == '"':
            return _unescape(body)
        return body.replace("''", "'")
    return text


def _atom(text: str):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return _unquote(text)
    low = text.lower()
    if low in ("", "null", "~"):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+)([eE][-+]?\d+)?", text):
        return float(text)
    return text


def _split_top(text: str, sep: str) -> list:
    parts: list = []
    buf: list = []
    quote = None
    depth = 0
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{":
            depth += 1
            buf.append(ch)
        elif ch in "]}":
            depth -= 1
            buf.append(ch)
        elif ch == sep and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail or parts:
        parts.append(tail)
    return parts


def _split_key(text: str, lineno: int):
    quote = None
    depth = 0
    for idx, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        elif ch == ":" and depth == 0:
            nxt = text[idx + 1 : idx + 2]
            if nxt in ("", " "):
                return _unquote(text[:idx].strip()), text[idx + 1 :].strip()
    raise YamlError("expected 'key: value' on line %d: %s" % (lineno, text))


def _is_seq_entry(text: str) -> bool:
    return text == "-" or text.startswith("- ")


def _looks_like_mapping(text: str) -> bool:
    try:
        _split_key(text, 0)
        return True
    except YamlError:
        return False


_BLOCK_MARKERS = ("|", "|-", "|+", ">", ">-", ">+")


class _Parser:
    def __init__(self, text: str):
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        self.lines = normalized.split("\n")
        self.idx = 0

    def parse(self):
        value = self._block(0)
        if self._current() is not None:
            raise YamlError("unparsed content on line %d" % (self.idx + 1))
        return {} if value is None else value

    # -- cursor ---------------------------------------------------------
    def _current(self):
        while self.idx < len(self.lines):
            raw = self.lines[self.idx]
            stripped = raw.strip()
            if stripped == "" or stripped.startswith("#") or stripped in ("---", "..."):
                self.idx += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if "\t" in raw[:indent]:
                raise YamlError("tab indentation on line %d" % (self.idx + 1))
            return indent, _strip_comment(stripped)
        return None

    # -- structure ------------------------------------------------------
    def _block(self, indent: int):
        cur = self._current()
        if cur is None or cur[0] < indent:
            return None
        return self._sequence(cur[0]) if _is_seq_entry(cur[1]) else self._mapping(cur[0])

    def _mapping(self, indent: int) -> dict:
        out: dict = {}
        while True:
            cur = self._current()
            if cur is None or cur[0] < indent:
                break
            if cur[0] > indent:
                raise YamlError("unexpected indentation on line %d" % (self.idx + 1))
            if _is_seq_entry(cur[1]):
                break
            key, rest = _split_key(cur[1], self.idx + 1)
            self.idx += 1
            out[key] = self._value(rest, indent)
        return out

    def _sequence(self, indent: int) -> list:
        out: list = []
        while True:
            cur = self._current()
            if cur is None or cur[0] != indent or not _is_seq_entry(cur[1]):
                break
            text = cur[1]
            rest = "" if text == "-" else text[1:].strip()
            if rest == "":
                self.idx += 1
                nxt = self._current()
                out.append(self._block(nxt[0]) if nxt is not None and nxt[0] > indent else None)
                continue
            offset = indent + 1 + (len(text[1:]) - len(text[1:].lstrip(" ")))
            if rest in _BLOCK_MARKERS:
                self.idx += 1
                out.append(self._block_scalar(rest, indent))
            elif _looks_like_mapping(rest):
                self.lines[self.idx] = " " * offset + rest
                out.append(self._mapping(offset))
            elif _is_seq_entry(rest):
                self.lines[self.idx] = " " * offset + rest
                out.append(self._sequence(offset))
            else:
                self.idx += 1
                out.append(_parse_flow(rest))
        return out

    def _value(self, rest: str, indent: int):
        if rest in _BLOCK_MARKERS:
            return self._block_scalar(rest, indent)
        if rest != "":
            return _parse_flow(rest)
        nxt = self._current()
        if nxt is None or nxt[0] < indent:
            return None
        if nxt[0] == indent and _is_seq_entry(nxt[1]):
            return self._sequence(indent)
        if nxt[0] > indent:
            return self._block(nxt[0])
        return None

    def _block_scalar(self, marker: str, indent: int) -> str:
        body: list = []
        while self.idx < len(self.lines):
            raw = self.lines[self.idx]
            if raw.strip() == "":
                body.append("")
                self.idx += 1
                continue
            if len(raw) - len(raw.lstrip(" ")) <= indent:
                break
            body.append(raw)
            self.idx += 1
        while body and body[-1] == "":
            body.pop()
        if not body:
            return ""
        base = min(len(x) - len(x.lstrip(" ")) for x in body if x.strip())
        rows = [x[base:] if len(x) >= base else x for x in body]
        text = " ".join(r.strip() for r in rows if r.strip()) if marker[0] == ">" else "\n".join(rows)
        if marker.endswith("-"):
            return text
        return text + "\n"


def _parse_flow(text: str):
    text = text.strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        return [] if not inner else [_parse_flow(part) for part in _split_top(inner, ",")]
    if text.startswith("{") and text.endswith("}"):
        inner = text[1:-1].strip()
        if not inner:
            return {}
        out: dict = {}
        for part in _split_top(inner, ","):
            key, value = _split_key(part, 0)
            out[key] = _parse_flow(value)
        return out
    return _atom(text)


def parse_yaml(text: str):
    return _Parser(text).parse()


# --------------------------------------------------------------------------
# agent workflow: spec, validation, rendering
# --------------------------------------------------------------------------


def build_agent_spec(answers: dict) -> tuple:
    notes: list = []
    name = pascalize(answers.get("name") or answers.get("workflow_name") or "Workflow")
    stages_in = answers.get("stages") or []
    if not isinstance(stages_in, list) or not stages_in:
        raise ValueError("answers for kind agent need a non-empty stages list")

    stages: list = []
    seen: list = []
    previous = None
    for position, raw in enumerate(stages_in, start=1):
        if not isinstance(raw, dict):
            raise ValueError("stage %d is not an object" % position)
        title = str(raw.get("title") or raw.get("id") or ("Stage %d" % position)).strip()
        stage_id = slugify(raw.get("id") or title) or ("stage-%d" % position)
        base = stage_id
        bump = 2
        while stage_id in seen:
            stage_id = "%s-%d" % (base, bump)
            bump += 1
            notes.append("duplicate stage id %r renamed to %r" % (base, stage_id))
        seen.append(stage_id)

        agent = str(raw.get("agent") or "Builder").strip() or "Builder"
        role = str(raw.get("role") or KNOWN_AGENTS.get(agent, "high")).strip().lower()
        if role not in ROLES:
            notes.append("stage %r had role %r outside the registry; using high" % (stage_id, role))
            role = "high"
        gate = str(raw.get("gate") or "auto").strip().lower()
        if gate not in GATES:
            notes.append("stage %r had gate %r outside the set; using auto" % (stage_id, gate))
            gate = "auto"

        criteria = [str(c).strip() for c in (raw.get("done_criteria") or []) if str(c).strip()]
        output = str(raw.get("output") or ("the %s result" % title.lower())).strip()
        if not criteria:
            criteria = ["%s exists and names the evidence that produced it." % output.capitalize()]
            notes.append("stage %r had no done criterion; a placeholder was written" % stage_id)

        after = raw.get("after")
        if after is None:
            after = [] if previous is None else [previous]
        after = [slugify(a) for a in after if str(a).strip()]

        stages.append(
            {
                "id": stage_id,
                "title": title,
                "agent": agent,
                "role": role,
                "input": str(raw.get("input") or "the previous stage output").strip(),
                "output": output,
                "done_criteria": criteria,
                "gate": gate,
                "after": after,
            }
        )
        previous = stage_id

    if not any(s["gate"] == "evidence" for s in stages):
        stages[-1]["gate"] = "evidence"
        notes.append("no evidence gate was given; the last stage now carries one")

    anti = [str(a).strip() for a in (answers.get("anti_claims") or []) if str(a).strip()]
    if not anti:
        anti = [
            "No stage reports done for a criterion whose probe was never run.",
            "No stage reviews work it produced itself.",
        ]
        notes.append("no anti-claims were given; two defaults were written")

    spec = {
        "name": name,
        "version": str(answers.get("version") or "1.0.0"),
        "goal": str(answers.get("goal") or "").strip() or ("Run the %s stages in order." % name),
        "kind": "agent",
        "stages": stages,
        "anti_claims": anti,
        "state_file": STATE_TOKEN,
    }
    return spec, notes


def validate_agent_spec(spec) -> list:
    findings: list = []
    if not isinstance(spec, dict):
        return [finding("not-an-object", "the spec is not a JSON object")]
    if spec.get("kind") != "agent":
        findings.append(finding("wrong-kind", "kind must be 'agent', found %r" % spec.get("kind")))
    for field in ("name", "version", "goal"):
        if not str(spec.get(field) or "").strip():
            findings.append(finding("missing-field", "%s is required and must be non-empty" % field))
    if not str(spec.get("state_file") or "").strip():
        findings.append(finding("missing-field", "state_file is required"))

    anti = spec.get("anti_claims")
    if not isinstance(anti, list) or not [a for a in anti if str(a).strip()]:
        findings.append(finding("no-anti-claims", "anti_claims must be an array with at least one entry"))

    stages = spec.get("stages")
    if not isinstance(stages, list) or not stages:
        findings.append(finding("no-stages", "stages must be a non-empty array"))
        return findings

    ids: list = []
    edges: dict = {}
    for position, stage in enumerate(stages, start=1):
        where = "stages[%d]" % (position - 1)
        if not isinstance(stage, dict):
            findings.append(finding("bad-stage", "stage is not an object", where))
            continue
        stage_id = str(stage.get("id") or "").strip()
        if not stage_id:
            findings.append(finding("missing-stage-id", "every stage needs an id", where))
        elif stage_id in ids:
            findings.append(finding("duplicate-stage-id", "stage id %r is used twice" % stage_id, where))
        else:
            ids.append(stage_id)
        where = stage_id or where
        if not str(stage.get("agent") or "").strip():
            findings.append(finding("missing-agent", "stage needs an agent name", where))
        role = str(stage.get("role") or "").strip()
        if role not in ROLES:
            findings.append(
                finding("bad-role", "role %r is not one of %s" % (role, ", ".join(ROLES)), where)
            )
        gate = str(stage.get("gate") or "").strip()
        if gate not in GATES:
            findings.append(
                finding("bad-gate", "gate %r is not one of %s" % (gate, ", ".join(GATES)), where)
            )
        for field in ("input", "output"):
            if not str(stage.get(field) or "").strip():
                findings.append(finding("missing-field", "stage needs a non-empty %s" % field, where))
        criteria = stage.get("done_criteria")
        if not isinstance(criteria, list) or not [c for c in criteria if str(c).strip()]:
            findings.append(
                finding("no-done-criteria", "stage needs at least one done criterion", where)
            )
        after = stage.get("after") or []
        if not isinstance(after, list):
            findings.append(finding("bad-after", "after must be an array of stage ids", where))
            after = []
        edges[stage_id] = [str(a).strip() for a in after]

    for stage_id, deps in edges.items():
        for dep in deps:
            if dep == stage_id:
                findings.append(finding("self-dependency", "stage %r depends on itself" % stage_id, stage_id))
            elif dep not in edges:
                findings.append(
                    finding("unknown-after", "after references unknown stage %r" % dep, stage_id)
                )
    cycle = find_cycle(edges)
    if cycle:
        findings.append(finding("cyclic-after", "after edges form a cycle: %s" % " -> ".join(cycle)))

    gates = [str(s.get("gate") or "") for s in stages if isinstance(s, dict)]
    if "evidence" not in gates:
        findings.append(
            finding("no-evidence-gate", "at least one stage must carry the evidence gate")
        )
    return findings


def render_stage_table(spec: dict) -> str:
    rows = [
        "| # | stage | agent (role) | in | out | gate | after | done when |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for position, stage in enumerate(spec.get("stages") or [], start=1):
        criteria = "; ".join(str(c) for c in (stage.get("done_criteria") or []))
        after = ", ".join(stage.get("after") or []) or "-"
        rows.append(
            "| %d | `%s` %s | %s (%s) | %s | %s | `%s` | %s | %s |"
            % (
                position,
                stage.get("id", ""),
                stage.get("title", ""),
                stage.get("agent", ""),
                stage.get("role", ""),
                stage.get("input", ""),
                stage.get("output", ""),
                stage.get("gate", ""),
                after,
                criteria,
            )
        )
    return "\n".join(rows) + "\n"


def render_workflow_skill(spec: dict) -> str:
    name = spec["name"]
    slug = slugify(name)
    stages = spec.get("stages") or []
    titles = ", ".join(str(s.get("id")) for s in stages)
    description = clip(
        "%s Runs the %d-stage %s agent workflow: %s. Each stage names its input, its output, "
        "and the criteria that close it; the evidence gates refuse to pass on an assertion. "
        "USE WHEN %s, run the %s workflow, %s workflow, start the %s pipeline, resume %s. "
        "NOT FOR a single-shot task one agent finishes in one pass, editing one line of an "
        "existing pipeline, or choosing which model runs a stage (the role registry decides)."
        % (
            spec.get("goal", ""),
            len(stages),
            name,
            titles,
            slug,
            slug,
            slug,
            slug,
            slug,
        ),
        1024,
    )
    anti = "\n".join("- %s" % a for a in spec.get("anti_claims") or [])
    gate_rows = "\n".join(
        [
            "| `auto` | the stage closes its own criteria and hands off |",
            "| `ask` | the stage stops and waits for a human answer before handing off |",
            "| `evidence` | the stage may not pass until tool output for every criterion is in the trail |",
        ]
    )
    return (
        "---\n"
        "name: %s\n"
        "description: %s\n"
        'argument-hint: "<the work item to run through the workflow>"\n'
        "---\n\n"
        "# %s\n\n"
        "%s\n\n"
        "## What done looks like\n\n"
        "- Every stage below ran, with its `after` dependencies satisfied first.\n"
        "- Each stage produced the output named in the table, and each done criterion is closed on "
        "evidence a reader can re-run.\n"
        "- Every `evidence` gate was closed by tool output in the trail, never by a claim that it "
        "would pass.\n"
        "- Every `ask` gate stopped and got a human answer before the next stage started.\n"
        "- None of the anti-claims below is true at the end.\n\n"
        "## Stages\n\n"
        "%s\n"
        "## Gates\n\n"
        "| gate | meaning |\n|---|---|\n%s\n\n"
        "## Anti-claims\n\n"
        "%s\n\n"
        "## How to run\n\n"
        "Pick the **%s** agent in the agent picker and describe the work item, or type `/%s <work "
        "item>` to run this skill directly. The orchestrator dispatches each stage to the agent in "
        "the table and holds the gates. Run state lives at `%s`.\n\n"
        "## Spec\n\n"
        "The machine-readable spec is [workflow.json](workflow.json). Validate it after any edit:\n\n"
        "```\npython .github/skills/CreateWorkflow/workflow_tool.py validate "
        ".github/skills/%s/workflow.json\n```\n"
        % (
            slug,
            description,
            name,
            spec.get("goal", ""),
            render_stage_table(spec),
            gate_rows,
            anti,
            name,
            slug,
            spec.get("state_file", STATE_TOKEN),
            name,
        )
    )


def render_orchestrator(spec: dict) -> str:
    name = spec["name"]
    stages = spec.get("stages") or []
    agents: list = []
    for stage in stages:
        agent = str(stage.get("agent") or "").strip()
        if agent and agent not in agents:
            agents.append(agent)

    gate_reason = {
        "auto": "all criteria closed",
        "ask": "all criteria closed and the human answered the open question",
        "evidence": "all criteria closed and the tool output is in the trail",
    }
    handoffs: list = []
    for stage in stages:
        for dep in stage.get("after") or []:
            source = next((s for s in stages if s.get("id") == dep), None)
            when = gate_reason.get(str(source.get("gate")) if source else "auto", "criteria closed")
            handoffs.append({"from": dep, "to": stage.get("id"), "when": when})

    front = {
        "name": name,
        "description": clip(
            "Orchestrates the %s workflow: %s. Dispatches each stage to its agent, enforces the "
            "gates, and refuses to report the workflow done while any criterion is unclosed."
            % (name, ", ".join(str(s.get("id")) for s in stages)),
            1024,
        ),
        "tools": ["agent", "search", "edit", "runCommands"],
        "model": "max",
        "agents": agents,
        "handoffs": handoffs,
        "user-invocable": True,
    }
    entry = [s.get("id") for s in stages if not (s.get("after") or [])]
    return (
        "---\n"
        + dump_yaml(front)
        + "---\n"
        + "# kaios-role: max\n\n"
        + "I run the %s workflow. The stage table in "
        "[the skill](../skills/%s/SKILL.md) is the contract; "
        "[workflow.json](../skills/%s/workflow.json) is its machine-readable form.\n\n"
        "## How I behave\n\n"
        "- I start at %s and follow the `after` edges. A stage whose dependencies are unclosed does "
        "not start.\n"
        "- I dispatch each stage to the agent named for it and pass only that stage's declared "
        "input.\n"
        "- I close a stage only when every one of its done criteria is closed. At an `evidence` "
        "gate I need the tool output, not a report of it.\n"
        "- At an `ask` gate I stop and ask, and I do not answer on the principal's behalf.\n"
        "- The reviewing stage is never the stage that built the work.\n"
        "- When a stage fails twice the same way I stop the workflow and report what is blocking it "
        "rather than trying a third variation.\n\n"
        "## What I report\n\n"
        "One line per stage: the stage id, the agent that ran it, the evidence that closed it, and "
        "the gate outcome. Then the anti-claims, each marked held or broken.\n"
        % (name, name, name, ", ".join(entry) or "the first stage")
    )


def scaffold_agent(answers: dict, out: Path, force: bool) -> dict:
    spec, notes = build_agent_spec(answers)
    name = spec["name"]
    targets = [
        (out / ".github" / "skills" / name / "workflow.json", json.dumps(spec, indent=2) + "\n"),
        (out / ".github" / "skills" / name / "SKILL.md", render_workflow_skill(spec)),
        (out / ".github" / "agents" / (name + ".agent.md"), render_orchestrator(spec)),
    ]
    written, skipped = _write_all(targets, force)
    return {"spec_name": name, "written": written, "skipped": skipped, "notes": notes}


# --------------------------------------------------------------------------
# GitHub Actions workflow
# --------------------------------------------------------------------------


def _checkout_step() -> dict:
    return {"name": "Check out the repository", "uses": "actions/checkout@v4"}


def _setup_python_step(version: str) -> dict:
    return {
        "name": "Set up Python",
        "uses": "actions/setup-python@v5",
        "with": {"python-version": str(version)},
    }


def build_actions_workflow(answers: dict) -> tuple:
    notes: list = []
    template = str(answers.get("template") or "python-tests").strip().lower()
    if template not in ACTIONS_TEMPLATES:
        notes.append("template %r is unknown; using python-tests" % template)
        template = "python-tests"
    slug = slugify(answers.get("name") or template) or template
    display = str(answers.get("display_name") or titleize(slug))
    runner = str(answers.get("runs_on") or "ubuntu-latest")
    python_version = str(answers.get("python_version") or "3.11")
    branches = answers.get("branches") or ["main"]

    if template == "python-tests":
        command = str(answers.get("test_command") or "python -m unittest discover -s tests -v")
        workflow = {
            "name": display,
            "on": {
                "push": {"branches": list(branches)},
                "pull_request": {"branches": list(branches)},
                "workflow_dispatch": {},
            },
            "jobs": {
                "tests": {
                    "runs-on": runner,
                    "steps": [
                        _checkout_step(),
                        _setup_python_step(python_version),
                        {
                            "name": "Install dependencies",
                            "if": "hashFiles('requirements.txt') != ''",
                            "run": "python -m pip install --upgrade pip\n"
                            "python -m pip install -r requirements.txt\n",
                        },
                        {"name": "Run the test suite", "run": command},
                    ],
                }
            },
        }
    elif template == "databricks-bundle-deploy":
        target = str(answers.get("target") or "prod")
        dev_target = str(answers.get("dev_target") or "dev")
        env = {
            "DATABRICKS_HOST": "${{ vars.DATABRICKS_HOST }}",
            "DATABRICKS_TOKEN": "${{ secrets.DATABRICKS_TOKEN }}",
        }
        cli_step = {"name": "Set up the Databricks CLI", "uses": "databricks/setup-cli@main"}
        workflow = {
            "name": display,
            "on": {"push": {"branches": list(branches)}, "workflow_dispatch": {}},
            "jobs": {
                "validate": {
                    "runs-on": runner,
                    "steps": [
                        _checkout_step(),
                        cli_step,
                        {
                            "name": "Validate the bundle",
                            "run": "databricks bundle validate -t " + dev_target,
                            "env": dict(env),
                        },
                    ],
                },
                "deploy": {
                    "needs": "validate",
                    "runs-on": runner,
                    "environment": target,
                    "steps": [
                        _checkout_step(),
                        cli_step,
                        {
                            "name": "Deploy the bundle",
                            "run": "databricks bundle deploy -t " + target,
                            "env": dict(env),
                        },
                    ],
                },
            },
        }
        notes.append(
            "the deploy job is pinned to the %r environment so the protection rules on it are the "
            "approval gate" % target
        )
    else:
        cron = str(answers.get("cron") or "0 7 * * 1-5")
        command = str(answers.get("command") or "python -m kaios doctor")
        workflow = {
            "name": display,
            "on": {"schedule": [{"cron": cron}], "workflow_dispatch": {}},
            "jobs": {
                "run": {
                    "runs-on": runner,
                    "steps": [
                        _checkout_step(),
                        _setup_python_step(python_version),
                        {"name": "Run the scheduled task", "run": command},
                    ],
                }
            },
        }

    extra = answers.get("extra_steps") or []
    if extra:
        job_key = sorted(workflow["jobs"].keys())[0]
        workflow["jobs"][job_key]["steps"].extend(extra)
        notes.append("appended %d extra step(s) to job %r" % (len(extra), job_key))
    if answers.get("on"):
        workflow["on"] = answers["on"]
        notes.append("the on: block was taken from the answers file verbatim")
    return workflow, slug, notes


_SECRET_IN_RUN = re.compile(r"\$\{\{\s*secrets\.", re.IGNORECASE)
_PROD_TARGET = re.compile(r"(-t|--target)\s+prod", re.IGNORECASE)


def validate_actions(data) -> list:
    findings: list = []
    if not isinstance(data, dict):
        return [finding("not-a-mapping", "the workflow file is not a YAML mapping")]
    if not str(data.get("name") or "").strip():
        findings.append(finding("missing-name", "a top-level name is required"))
    if "on" not in data or data.get("on") in (None, "", {}, []):
        findings.append(finding("missing-on", "a top-level on: block is required"))
    jobs = data.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        findings.append(finding("missing-jobs", "a top-level jobs mapping with at least one job is required"))
        return findings

    for job_name, job in jobs.items():
        where = "jobs.%s" % job_name
        if not isinstance(job, dict):
            findings.append(finding("bad-job", "job is not a mapping", where))
            continue
        if not str(job.get("runs-on") or "").strip():
            findings.append(finding("missing-runs-on", "job needs runs-on", where))
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            findings.append(finding("missing-steps", "job needs a non-empty steps list", where))
            continue
        for position, step in enumerate(steps):
            step_where = "%s.steps[%d]" % (where, position)
            if not isinstance(step, dict):
                findings.append(finding("bad-step", "step is not a mapping", step_where))
                continue
            has_uses = bool(str(step.get("uses") or "").strip())
            has_run = bool(str(step.get("run") or "").strip())
            if not has_uses and not has_run:
                findings.append(finding("step-without-action", "step needs either uses or run", step_where))
            if has_uses and has_run:
                findings.append(finding("step-with-both", "step has both uses and run", step_where))
            run = str(step.get("run") or "")
            if _SECRET_IN_RUN.search(run):
                findings.append(
                    finding(
                        "secret-in-run",
                        "a run line interpolates a secret; pass it through env instead",
                        step_where,
                    )
                )
            if "bundle deploy" in run and _PROD_TARGET.search(run) and not str(job.get("environment") or ""):
                findings.append(
                    finding(
                        "unprotected-prod-deploy",
                        "a job that deploys to prod needs an environment for its protection rules",
                        where,
                    )
                )
    return findings


def scaffold_actions(answers: dict, out: Path, force: bool) -> dict:
    workflow, slug, notes = build_actions_workflow(answers)
    target = out / ".github" / "workflows" / (slug + ".yml")
    written, skipped = _write_all([(target, dump_yaml(workflow))], force)
    return {"spec_name": slug, "written": written, "skipped": skipped, "notes": notes}


# --------------------------------------------------------------------------
# Databricks job workflow
# --------------------------------------------------------------------------


def _task_block(raw: dict, position: int) -> dict:
    task_key = str(raw.get("task_key") or ("task_%d" % position)).strip()
    present = [t for t in DB_TASK_TYPES if t in raw]
    task: dict = {"task_key": task_key}
    if present:
        for name in present:
            task[name] = raw[name]
    else:
        kind = TYPE_ALIASES.get(str(raw.get("type") or "notebook").strip().lower(), "notebook_task")
        if kind == "notebook_task":
            body = {"notebook_path": str(raw.get("notebook_path") or ("../notebooks/%s.py" % task_key))}
            if raw.get("base_parameters"):
                body["base_parameters"] = raw["base_parameters"]
        elif kind == "python_wheel_task":
            body = {
                "package_name": str(raw.get("package_name") or "jobs"),
                "entry_point": str(raw.get("entry_point") or task_key),
            }
        elif kind == "sql_task":
            body = {
                "warehouse_id": str(raw.get("warehouse_id") or "${var.warehouse_id}"),
                "query": {"query_id": str(raw.get("query_id") or task_key)},
            }
        else:
            body = raw.get("body") or {}
        task[kind] = body
    depends = raw.get("depends_on") or []
    blocks = []
    for dep in depends:
        if isinstance(dep, dict):
            blocks.append({"task_key": str(dep.get("task_key") or "").strip()})
        elif str(dep).strip():
            blocks.append({"task_key": str(dep).strip()})
    if blocks:
        task["depends_on"] = blocks
    if raw.get("job_cluster_key"):
        task["job_cluster_key"] = str(raw["job_cluster_key"])
    return task


def build_databricks_job(answers: dict) -> tuple:
    notes: list = []
    slug = slugify(answers.get("name") or "job").replace("-", "_") or "job"
    tasks_in = answers.get("tasks") or []
    if not isinstance(tasks_in, list) or not tasks_in:
        raise ValueError("answers for kind databricks need a non-empty tasks list")
    tasks = [_task_block(raw, i) for i, raw in enumerate(tasks_in, start=1)]
    job: dict = {"name": str(answers.get("job_name") or titleize(slug)), "tasks": tasks}
    if answers.get("schedule"):
        job["schedule"] = answers["schedule"]
    else:
        notes.append("no schedule was given; the job runs only when triggered")
    if answers.get("email_notifications"):
        job["email_notifications"] = answers["email_notifications"]
    else:
        notes.append("no failure notification was given; nobody learns when this job fails at night")
    if answers.get("max_concurrent_runs"):
        job["max_concurrent_runs"] = answers["max_concurrent_runs"]
    return {"resources": {"jobs": {slug: job}}}, slug, notes


def build_bundle_root(answers: dict) -> dict:
    bundle = slugify(answers.get("bundle_name") or answers.get("name") or "bundle").replace("-", "_")
    return {
        "bundle": {"name": bundle},
        "include": ["resources/*.yml"],
        "targets": {
            "dev": {"mode": "development", "default": True},
            "prod": {"mode": "production"},
        },
    }


def validate_databricks_job(data, path: Path) -> list:
    findings: list = []
    if not isinstance(data, dict):
        return [finding("not-a-mapping", "the resource file is not a YAML mapping")]
    resources = data.get("resources")
    if not isinstance(resources, dict):
        findings.append(finding("missing-resources", "a top-level resources mapping is required"))
        return findings
    jobs = resources.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        findings.append(finding("missing-jobs", "resources.jobs must hold at least one job"))
        return findings

    for job_key, job in jobs.items():
        where = "resources.jobs.%s" % job_key
        if not isinstance(job, dict):
            findings.append(finding("bad-job", "job is not a mapping", where))
            continue
        if not str(job.get("name") or "").strip():
            findings.append(finding("missing-name", "job needs a name", where))
        tasks = job.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            findings.append(finding("missing-tasks", "job needs a non-empty tasks list", where))
            continue
        edges: dict = {}
        for position, task in enumerate(tasks):
            task_where = "%s.tasks[%d]" % (where, position)
            if not isinstance(task, dict):
                findings.append(finding("bad-task", "task is not a mapping", task_where))
                continue
            key = str(task.get("task_key") or "").strip()
            if not key:
                findings.append(finding("missing-task-key", "task needs a task_key", task_where))
                continue
            if key in edges:
                findings.append(
                    finding("duplicate-task-key", "task_key %r is used twice" % key, task_where)
                )
            types = [t for t in DB_TASK_TYPES if t in task and task[t] not in (None, {}, [])]
            if len(types) == 0:
                findings.append(
                    finding(
                        "no-task-type",
                        "task needs exactly one of %s" % ", ".join(DB_TASK_TYPES),
                        task_where,
                    )
                )
            elif len(types) > 1:
                findings.append(
                    finding("many-task-types", "task carries several types: %s" % ", ".join(types), task_where)
                )
            deps = []
            for dep in task.get("depends_on") or []:
                deps.append(str(dep.get("task_key") if isinstance(dep, dict) else dep).strip())
            edges[key] = deps
        for key, deps in edges.items():
            for dep in deps:
                if dep == key:
                    findings.append(finding("self-dependency", "task %r depends on itself" % key, where))
                elif dep not in edges:
                    findings.append(
                        finding("unknown-depends-on", "depends_on names unknown task %r" % dep, where)
                    )
        cycle = find_cycle(edges)
        if cycle:
            findings.append(
                finding("cyclic-depends-on", "depends_on forms a cycle: %s" % " -> ".join(cycle), where)
            )

    findings.extend(_check_bundle_root(path))
    return findings


def _check_bundle_root(path: Path) -> list:
    for candidate in (path.parent / "databricks.yml", path.parent.parent / "databricks.yml"):
        if candidate.exists():
            try:
                root = parse_yaml(read_utf8(candidate))
            except YamlError as exc:
                return [finding("unparsable-bundle-root", str(exc), str(candidate))]
            return validate_bundle_root(root)
    return [
        finding(
            "missing-bundle-root",
            "no databricks.yml was found beside or above the resource file, so the job belongs to "
            "no bundle",
        )
    ]


def validate_bundle_root(data) -> list:
    findings: list = []
    if not isinstance(data, dict):
        return [finding("not-a-mapping", "databricks.yml is not a YAML mapping")]
    bundle = data.get("bundle")
    if not isinstance(bundle, dict) or not str(bundle.get("name") or "").strip():
        findings.append(finding("missing-bundle-name", "databricks.yml needs bundle.name"))
    targets = data.get("targets")
    if not isinstance(targets, dict) or not targets:
        findings.append(finding("missing-targets", "databricks.yml needs a targets mapping"))
        return findings
    if "prod" not in targets:
        findings.append(finding("missing-prod-target", "targets must include prod"))
    return findings


def scaffold_databricks(answers: dict, out: Path, force: bool) -> dict:
    job, slug, notes = build_databricks_job(answers)
    targets = [(out / "resources" / (slug + ".job.yml"), dump_yaml(job))]
    root = out / "databricks.yml"
    if root.exists():
        notes.append("databricks.yml already exists and was left alone")
    else:
        targets.append((root, dump_yaml(build_bundle_root(answers))))
        notes.append("a minimal databricks.yml was written with dev and prod targets")
    written, skipped = _write_all(targets, force)
    return {"spec_name": slug, "written": written, "skipped": skipped, "notes": notes}


# --------------------------------------------------------------------------
# shared scaffold plumbing
# --------------------------------------------------------------------------


def _write_all(targets: list, force: bool) -> tuple:
    written: list = []
    skipped: list = []
    for path, text in targets:
        if path.exists() and not force:
            skipped.append(str(path))
            continue
        write_utf8(path, text)
        written.append(str(path))
    return written, skipped


SCAFFOLDERS = {
    "agent": scaffold_agent,
    "actions": scaffold_actions,
    "databricks": scaffold_databricks,
}


# --------------------------------------------------------------------------
# validation entry point
# --------------------------------------------------------------------------


def validate_file(path: Path) -> tuple:
    if not path.exists():
        return "unknown", [finding("missing-file", "no file at %s" % path)]
    text = read_utf8(path)
    name = path.name.lower()
    if name.endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError as exc:
            return "agent", [finding("unparsable-json", str(exc))]
        if isinstance(data, dict) and (data.get("kind") == "agent" or "stages" in data):
            return "agent", validate_agent_spec(data)
        return "unknown", [
            finding("unknown-shape", "a JSON file here should be an agent workflow spec with stages")
        ]

    try:
        data = parse_yaml(text)
    except YamlError as exc:
        return "unknown", [finding("unparsable-yaml", str(exc))]

    if name in ("databricks.yml", "databricks.yaml"):
        return "databricks-bundle", validate_bundle_root(data)
    if isinstance(data, dict) and "resources" in data:
        return "databricks", validate_databricks_job(data, path)
    if name.endswith((".job.yml", ".job.yaml")):
        return "databricks", validate_databricks_job(data, path)
    if isinstance(data, dict) and ("jobs" in data or "on" in data):
        return "actions", validate_actions(data)
    if path.parent.name == "workflows":
        return "actions", validate_actions(data)
    return "unknown", [
        finding(
            "unknown-shape",
            "the file is neither an agent spec, an Actions workflow, nor a bundle job resource",
        )
    ]


# --------------------------------------------------------------------------
# run state
# --------------------------------------------------------------------------


def load_state() -> dict:
    path = state_path()
    if not path.exists():
        return {"version": 1, "runs": []}
    try:
        data = json.loads(read_utf8(path))
    except ValueError:
        return {"version": 1, "runs": []}
    if not isinstance(data, dict):
        return {"version": 1, "runs": []}
    data.setdefault("version", 1)
    if not isinstance(data.get("runs"), list):
        data["runs"] = []
    return data


def save_state(state: dict) -> Path:
    path = state_path()
    write_utf8(path, json.dumps(state, indent=2) + "\n")
    return path


def runs_start(name: str) -> dict:
    state = load_state()
    entry = {
        "name": name,
        "status": "running",
        "started": now_iso(),
        "finished": None,
        "run_id": "%s-%d" % (slugify(name) or "run", len(state["runs"]) + 1),
    }
    state["runs"].append(entry)
    path = save_state(state)
    return {"ok": True, "action": "start", "run": entry, "state_file": str(path)}


def runs_finish(name: str, status: str) -> dict:
    state = load_state()
    for entry in reversed(state["runs"]):
        if entry.get("name") == name and entry.get("status") == "running":
            entry["status"] = status
            entry["finished"] = now_iso()
            path = save_state(state)
            return {"ok": True, "action": "finish", "run": entry, "state_file": str(path)}
    return {
        "ok": False,
        "action": "finish",
        "error": "no running workflow named %r in the state file" % name,
        "state_file": str(state_path()),
    }


def runs_list() -> dict:
    state = load_state()
    return {
        "ok": True,
        "action": "list",
        "state_file": str(state_path()),
        "count": len(state["runs"]),
        "runs": state["runs"],
    }


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------


def cmd_kinds(args) -> int:
    default = [k["kind"] for k in KINDS if k.get("default")]
    emit(
        {
            "ok": True,
            "tool_version": TOOL_VERSION,
            "default_kind": default[0] if default else "agent",
            "default_note": "When the user is vague about which kind they want, say the default out "
            "loud and let them redirect.",
            "kinds": KINDS,
        }
    )
    return 0


def cmd_questions(args) -> int:
    bank = QUESTIONS[args.kind]
    emit(
        {
            "ok": True,
            "kind": args.kind,
            "count": len(bank),
            "budget": "ask at most ten; skip any the user already answered",
            "questions": bank,
        }
    )
    return 0


def cmd_scaffold(args) -> int:
    answers_path = Path(args.answers).expanduser()
    if not answers_path.exists():
        emit({"ok": False, "error": "no answers file at %s" % answers_path})
        return 1
    try:
        answers = json.loads(read_utf8(answers_path))
    except ValueError as exc:
        emit({"ok": False, "error": "answers file is not valid JSON: %s" % exc})
        return 1
    if not isinstance(answers, dict):
        emit({"ok": False, "error": "the answers file must hold a JSON object"})
        return 1

    kind = args.kind or str(answers.get("kind") or "")
    if kind not in SCAFFOLDERS:
        emit({"ok": False, "error": "kind must be one of %s" % ", ".join(sorted(SCAFFOLDERS))})
        return 2
    out = Path(args.out).expanduser()
    try:
        result = SCAFFOLDERS[kind](answers, out, args.force)
    except ValueError as exc:
        emit({"ok": False, "kind": kind, "error": str(exc)})
        return 1

    payload = {
        "ok": True,
        "kind": kind,
        "name": result["spec_name"],
        "out": str(out),
        "written": result["written"],
        "skipped": result["skipped"],
        "notes": result["notes"],
        "next": "validate every written artifact before calling this done",
    }
    emit(payload)
    return 0


def cmd_validate(args) -> int:
    path = Path(args.path).expanduser()
    kind, findings = validate_file(path)
    emit(
        {
            "ok": not findings,
            "path": str(path),
            "kind": kind,
            "finding_count": len(findings),
            "findings": findings,
        }
    )
    return 1 if findings else 0


def cmd_render(args) -> int:
    path = Path(args.spec).expanduser()
    if not path.exists():
        emit({"ok": False, "error": "no spec at %s" % path})
        return 1
    try:
        spec = json.loads(read_utf8(path))
    except ValueError as exc:
        emit({"ok": False, "error": "spec is not valid JSON: %s" % exc})
        return 1
    findings = validate_agent_spec(spec)
    table = render_stage_table(spec)
    if args.md:
        sys.stdout.write(table)
        return 1 if findings else 0
    emit({"ok": not findings, "markdown": table, "findings": findings})
    return 1 if findings else 0


def cmd_runs(args) -> int:
    if args.action == "list":
        payload = runs_list()
    elif args.action == "start":
        if not args.name:
            emit({"ok": False, "error": "runs start needs --name"})
            return 2
        payload = runs_start(args.name)
    else:
        if not args.name:
            emit({"ok": False, "error": "runs finish needs --name"})
            return 2
        payload = runs_finish(args.name, args.status)
    emit(payload)
    return 0 if payload.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workflow_tool.py",
        description="Scaffold, validate, and track the three kinds of workflow KaiOS builds.",
    )
    parser.add_argument("--version", action="version", version="workflow_tool " + TOOL_VERSION)
    subs = parser.add_subparsers(dest="command")

    kinds = subs.add_parser("kinds", help="list the three kinds and when to use each")
    kinds.add_argument("--json", action="store_true", help="JSON output (the default)")
    kinds.set_defaults(func=cmd_kinds)

    questions = subs.add_parser("questions", help="print the interview question bank for a kind")
    questions.add_argument("--kind", required=True, choices=sorted(QUESTIONS))
    questions.add_argument("--json", action="store_true", help="JSON output (the default)")
    questions.set_defaults(func=cmd_questions)

    scaffold = subs.add_parser("scaffold", help="write the artifacts for a kind from an answers file")
    scaffold.add_argument("--kind", choices=sorted(SCAFFOLDERS), help="defaults to the kind in the answers file")
    scaffold.add_argument("--answers", required=True, help="path to the answers JSON")
    scaffold.add_argument("--out", required=True, help="repository root the artifacts are written under")
    scaffold.add_argument("--force", action="store_true", help="overwrite existing artifacts")
    scaffold.add_argument("--json", action="store_true", help="JSON output (the default)")
    scaffold.set_defaults(func=cmd_scaffold)

    validate = subs.add_parser("validate", help="validate a spec, an Actions workflow, or a bundle job")
    validate.add_argument("path")
    validate.add_argument("--json", action="store_true", help="JSON output (the default)")
    validate.set_defaults(func=cmd_validate)

    render = subs.add_parser("render", help="render the stage table for an agent workflow spec")
    render.add_argument("--spec", required=True)
    render.add_argument("--md", action="store_true", help="write markdown to stdout instead of JSON")
    render.add_argument("--json", action="store_true", help="JSON output (the default)")
    render.set_defaults(func=cmd_render)

    runs = subs.add_parser("runs", help="track workflow runs in the KaiOS state file")
    runs.add_argument("action", choices=("list", "start", "finish"))
    runs.add_argument("--name", help="workflow name")
    runs.add_argument("--status", choices=("ok", "failed"), default="ok")
    runs.add_argument("--json", action="store_true", help="JSON output (the default)")
    runs.set_defaults(func=cmd_runs)
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
