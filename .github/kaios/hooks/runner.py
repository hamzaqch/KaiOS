"""The dispatcher: read one event, run every module for it, emit one JSON object.

Rule: the runner always writes valid JSON and always exits 0, and a hook module
that raises is logged and skipped rather than allowed to break the session.
Falsifier: ``.github/tests/test_hooks.py`` injects a module that raises and asserts the
output is still JSON with ``continue: true`` and an error line in
``hook-events.jsonl``.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import EVENTS, canonical, event_dir
from .. import isa as isa_mod
from ..paths import Paths

#: Never write more than this many characters of one payload to the event log.
PAYLOAD_CAP = 16000

#: Most restrictive first; a lower index wins a merge.
_DECISIONS = ("deny", "ask", "allow")

_HOOKS_ROOT = Path(__file__).resolve().parent


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Context:
    """What every hook module is handed alongside the raw event."""

    paths: Paths
    config: dict = field(default_factory=dict)
    active_isa: Path | None = None
    repo: Path | None = None
    now: str = ""
    event: str = ""
    session_id: str = "unknown"
    scratch: dict = field(default_factory=dict)

    @property
    def home(self) -> Path:
        return self.paths.home

    @property
    def doctrine(self) -> Path:
        """The doctrine tree to point at: the checkout's when inside one."""
        repo_doctrine = self.paths.repo_doctrine
        return repo_doctrine if repo_doctrine is not None else self.paths.doctrine

    def flag(self, name: str, default=None):
        value = self.config.get(name)
        return default if value is None else value


# ---------------------------------------------------------------- input


def read_stdin(stream=None) -> tuple:
    """All of stdin as a dict. Returns ``(payload, error)``; never raises."""
    handle = sys.stdin if stream is None else stream
    raw = ""
    try:
        if handle is None:
            return {}, None
        # A terminal has nothing piped into it; reading would block until EOF.
        if stream is None and hasattr(handle, "isatty") and handle.isatty():
            return {}, None
        raw = handle.read() or ""
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return {}, "stdin unreadable: %s" % exc
    if not raw.strip():
        return {}, None
    try:
        parsed = json.loads(raw)
    except ValueError as exc:
        return {}, "stdin is not JSON: %s" % exc
    if isinstance(parsed, dict):
        return parsed, None
    return {}, "stdin is JSON but not an object: %s" % type(parsed).__name__


def _load_config(paths: Paths) -> dict:
    try:
        data = json.loads(paths.config_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def build_context(event: dict, event_name: str, home: str | None = None) -> Context:
    """Resolve paths, config, and the active ISA for one hook run."""
    where = event.get("cwd") or event.get("workspaceFolder") or event.get("workspace_folder")
    if not isinstance(where, str) or not where.strip():
        try:
            where = os.getcwd()
        except OSError:
            where = "."
    paths = Paths.resolve(cwd=where, home=home)
    active = None
    try:
        active = isa_mod.find_active(paths)
    except (OSError, ValueError):
        active = None
    from .util import session_id as _session_id

    return Context(
        paths=paths,
        config=_load_config(paths),
        active_isa=active,
        repo=paths.repo,
        now=now_iso(),
        event=event_name,
        session_id=_session_id(event),
    )


# ---------------------------------------------------------------- logging


def _append(path: Path, record: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    except OSError:
        pass


def _capped(payload: dict) -> object:
    try:
        blob = json.dumps(payload, sort_keys=True, default=str)
    except (TypeError, ValueError):
        blob = str(payload)
    if len(blob) <= PAYLOAD_CAP:
        return payload
    return {"truncated": True, "chars": len(blob), "head": blob[:PAYLOAD_CAP]}


def log_event(paths: Paths, event_name: str, payload: dict) -> None:
    _append(
        paths.hook_events,
        {"ts": now_iso(), "event": event_name, "payload": _capped(payload)},
    )


def log_error(paths: Paths, event_name: str, hook: str, exc: BaseException) -> None:
    _append(
        paths.hook_events,
        {
            "ts": now_iso(),
            "event": event_name,
            "hook": hook,
            "error": "%s: %s" % (type(exc).__name__, exc),
            "traceback": "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )[-4000:],
        },
    )


def log_note(paths: Paths, event_name: str, note: str) -> None:
    _append(paths.hook_events, {"ts": now_iso(), "event": event_name, "note": str(note)})


# ---------------------------------------------------------------- discovery


def hook_dir(event_name: str) -> Path:
    return _HOOKS_ROOT / event_dir(event_name)


def discover(event_name: str) -> list:
    """Module stems under the event directory, alphabetical, private skipped."""
    directory = hook_dir(event_name)
    if not directory.is_dir():
        return []
    names = []
    for candidate in sorted(directory.glob("*.py"), key=lambda p: p.name):
        if candidate.name.startswith("_"):
            continue
        names.append(candidate.stem)
    return names


def inventory() -> dict:
    """Every event mapped to the hook modules registered under it."""
    return {name: discover(name) for name in EVENTS}


def _import(event_name: str, stem: str):
    return importlib.import_module("%s.%s.%s" % (__package__, event_dir(event_name), stem))


# ---------------------------------------------------------------- merge


def merge(event_name: str, results: list) -> dict:
    """Fold every hook result into the single object the harness reads.

    Every decision is written twice, once in each dialect Copilot reads. The VS
    Code engine takes a tool decision from ``hookSpecificOutput`` and a stop from
    ``continue``/``stopReason``; the Copilot CLI engine takes the same two from
    top-level ``permissionDecision`` and from ``decision``/``reason``. Both sets
    say the same thing, so whichever engine is reading finds its own keys and the
    other engine's keys are inert to it. ``additionalContext`` is the one field
    both spell the same way. ``decision`` appears only on a block, because the
    CLI engine reads the bare presence of that key as the verdict.
    """
    contexts: list = []
    decision: str | None = None
    reasons: dict = {}
    stop_reasons: list = []
    blocked = False
    updated_input = None
    suppress = False

    for result in results:
        if not isinstance(result, dict):
            continue
        text = result.get("additionalContext")
        if isinstance(text, str) and text.strip():
            contexts.append(text.strip())

        raw_decision = result.get("permissionDecision")
        if isinstance(raw_decision, str) and raw_decision.lower() in _DECISIONS:
            candidate = raw_decision.lower()
            reason = str(result.get("permissionDecisionReason") or "").strip()
            reasons.setdefault(candidate, [])
            if reason:
                reasons[candidate].append(reason)
            if decision is None or _DECISIONS.index(candidate) < _DECISIONS.index(decision):
                decision = candidate

        if result.get("continue") is False:
            blocked = True
            reason = str(result.get("stopReason") or "").strip()
            if reason:
                stop_reasons.append(reason)

        if isinstance(result.get("updatedInput"), dict):
            updated_input = result["updatedInput"]

        if result.get("suppressOutput") is True:
            suppress = True

    out: dict = {"continue": not blocked}
    if blocked:
        out["decision"] = "block"
        if stop_reasons:
            joined = "; ".join(stop_reasons)
            out["stopReason"] = joined
            out["reason"] = joined
    if contexts:
        out["additionalContext"] = "\n\n".join(contexts)
    if decision is not None:
        reason = "; ".join(reasons.get(decision) or []) or "no reason given"
        out["hookSpecificOutput"] = {
            "hookEventName": event_name,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
        out["permissionDecision"] = decision
        out["permissionDecisionReason"] = reason
    if updated_input is not None:
        out["updatedInput"] = updated_input
    if suppress:
        out["suppressOutput"] = True
    return out


# ---------------------------------------------------------------- dispatch


def dispatch(event_name: str, event: dict, home: str | None = None, log: bool = True) -> dict:
    """Run every module for one event and return the merged decision."""
    name = canonical(event_name) or str(event_name)
    payload = event if isinstance(event, dict) else {}
    try:
        ctx = build_context(payload, name, home=home)
    except Exception:  # noqa: BLE001 - a broken context must not break the session
        return {"continue": True}

    if log:
        log_event(ctx.paths, name, payload)

    if canonical(event_name) is None:
        log_note(ctx.paths, name, "unknown event; nothing dispatched")
        return {"continue": True}

    results: list = []
    for stem in discover(name):
        try:
            module = _import(name, stem)
            entry = getattr(module, "run", None)
            if entry is None:
                log_note(ctx.paths, name, "%s has no run(event, ctx)" % stem)
                continue
            result = entry(payload, ctx)
        except Exception as exc:  # noqa: BLE001 - ISC-13: a raising hook is logged, not fatal
            log_error(ctx.paths, name, stem, exc)
            continue
        if result:
            results.append(result)
    return merge(name, results)


def run_event(event_name: str, stream=None, home: str | None = None, out=None) -> int:
    """Read stdin, dispatch, print one JSON object. Always returns 0."""
    handle = sys.stdout if out is None else out
    payload: dict = {}
    error = None
    try:
        payload, error = read_stdin(stream)
    except Exception:  # noqa: BLE001
        payload, error = {}, "stdin failed"
    decision = {"continue": True}
    try:
        decision = dispatch(event_name, payload, home=home)
        if error:
            try:
                paths = Paths.resolve(home=home)
                log_note(paths, str(event_name), error)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001 - nothing below this line may escape
        decision = {"continue": True}
    try:
        handle.write(json.dumps(decision, sort_keys=True, default=str) + "\n")
        handle.flush()
    except (OSError, ValueError):
        pass
    return 0
