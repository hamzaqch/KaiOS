"""Shared readers and result builders for hook modules.

Rule: every field a hook reads from an event is optional and may arrive under a
Copilot-style or a Claude-style name, so nothing reads ``event[...]`` directly.
Falsifier: a hook that raises ``KeyError`` on the sample payloads in
``.github/kaios/hooks/samples.py``.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

#: The first visible line of every response; hooks quote it, never print it.
BANNER = "════ KaiOS ═══════════════════════"

#: The closer the response format contract requires as the last line.
CLOSER = "\U0001f5e3️ Kai:"

_WRITE_TOKENS = ("edit", "write", "create", "patch", "replace", "insert", "notebook", "apply")
_PATH_KEYS = ("filePath", "file_path", "path", "filename", "file", "uri", "notebook_path")
_CONTENT_KEYS = ("content", "newString", "new_string", "text", "code", "patch", "edits")
_PROMPT_KEYS = ("prompt", "user_prompt", "message", "userPrompt", "text")
_RESULT_KEYS = (
    "tool_response",
    "tool_result",
    "toolResponse",
    "toolResult",
    "output",
    "result",
    "stdout",
)


def tool_name(event: dict) -> str:
    for key in ("tool_name", "toolName", "tool", "name"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def tool_input(event: dict) -> dict:
    # ``toolArgs`` is the Copilot CLI engine's name for this; without it every
    # guard sees an argument-less tool call and waves the call through.
    for key in ("tool_input", "toolInput", "toolArgs", "input", "arguments", "params"):
        value = event.get(key)
        if isinstance(value, dict):
            return value
    return {}


def command(event: dict) -> str:
    data = tool_input(event)
    for key in ("command", "commandLine", "command_line", "script", "cmd"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return " ".join(str(part) for part in value)
    return ""


def file_path(event: dict) -> str:
    data = tool_input(event)
    for key in _PATH_KEYS:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def content(event: dict) -> str:
    data = tool_input(event)
    chunks: list = []
    for key in _CONTENT_KEYS:
        value = data.get(key)
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, (list, dict)):
            try:
                chunks.append(json.dumps(value, sort_keys=True))
            except (TypeError, ValueError):
                chunks.append(str(value))
    return "\n".join(chunks)


def prompt(event: dict) -> str:
    for key in _PROMPT_KEYS:
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def tool_result(event: dict) -> str:
    for key in _RESULT_KEYS:
        if key not in event:
            continue
        value = event.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return str(value)
    return ""


def session_id(event: dict) -> str:
    for key in ("session_id", "sessionId", "conversation_id", "conversationId", "thread_id"):
        value = event.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int):
            return str(value)
    return "unknown"


def is_write(event: dict) -> bool:
    """True when this tool call looks like it writes a file."""
    name = tool_name(event).lower()
    if any(token in name for token in _WRITE_TOKENS):
        return True
    data = tool_input(event)
    if not file_path(event):
        return False
    return any(key in data for key in _CONTENT_KEYS)


def touches_file(event: dict) -> str:
    """The path this call names, write or read; empty when it names none."""
    return file_path(event)


def input_hash(event: dict) -> str:
    """A stable digest of tool name plus input, for repeat detection."""
    try:
        blob = json.dumps(
            {"tool": tool_name(event), "input": tool_input(event)}, sort_keys=True, default=str
        )
    except (TypeError, ValueError):
        blob = "%s|%s" % (tool_name(event), tool_input(event))
    return hashlib.sha256(blob.encode("utf-8", "replace")).hexdigest()[:16]


def clip(text: str, limit: int = 200) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


def display(path: Path | str | None, base: Path | None = None) -> str:
    """A short path for a message: relative to ``base`` when it is under it."""
    if path is None:
        return ""
    target = Path(str(path))
    if base is not None:
        try:
            return target.resolve().relative_to(Path(base).resolve()).as_posix()
        except (OSError, ValueError):
            pass
    return target.as_posix()


def posix(path: Path | str) -> str:
    """A forward-slash spelling of a path, so Windows input compares cleanly."""
    return str(path).replace("\\", "/")


# ---------------------------------------------------------------- results


def context(text: str) -> dict | None:
    body = str(text or "").strip()
    return {"additionalContext": body} if body else None


def deny(reason: str) -> dict:
    return {"permissionDecision": "deny", "permissionDecisionReason": str(reason)}


def ask(reason: str) -> dict:
    return {"permissionDecision": "ask", "permissionDecisionReason": str(reason)}


def block(reason: str) -> dict:
    return {"continue": False, "stopReason": str(reason)}


# ---------------------------------------------------------------- streams


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_jsonl(path: Path, record: dict) -> bool:
    """Append one JSON line. Returns False instead of raising on an OS error."""
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    except OSError:
        return False
    return True


def read_text(path: Path) -> str:
    """A file's text, or an empty string when it cannot be read."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
