"""Setup: see what the machine has, store the user's choices, render their files.

``detect`` never raises and never fails on a missing tool — everything outside
Python is optional. ``write_config`` merges choices into ``CONFIG/config.json``.
``render`` turns that config into the profile, the project table, per-project
instructions, a project ISA seed, an MCP config, and a user-level hook registry
with absolute paths.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import isa as isa_mod
from .events import (
    EVENTS,
    NESTED_REGISTRY_EVENTS,
    REGISTRY_EVENT_NAMES,
    REGISTRY_RELATIVE,
    registered_events,
)
from .paths import FRAMEWORK_DIR, Paths

PROBE_TIMEOUT = 10
COPILOT_DIRS = ("agents", "skills", "hooks", "instructions")
WRAPPER_RELATIVE = ".github/hooks/kaios.ps1"
SHELL_WRAPPER_RELATIVE = ".github/hooks/kaios.sh"

#: The checked-in registry path. Defined once, in ``kaios.events``.
HOOKS_REGISTRY_RELATIVE = REGISTRY_RELATIVE

CONFIG_SKELETON: dict = {
    "installed_at": None,
    "optional": {
        "mcp": {"github": False, "databricks": False},
        "databricks_cli": {"enabled": False, "profile": None},
        "apis": {},
    },
    "models": {},
    "user": {"name": "", "role": "", "team": "", "stack": []},
    "projects": [],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- detect


def _first_line(text: str) -> str | None:
    for line in str(text or "").replace("\r", "\n").split("\n"):
        if line.strip():
            return line.strip()
    return None


def probe(command: list[str], executable: str | None = None) -> dict:
    """Run one ``--version`` probe. Never raises; reports what happened."""
    name = command[0]
    resolved = executable or shutil.which(name)
    if resolved is None:
        return {"found": False, "version": None, "path": None, "reason": "not on PATH"}
    argv = [resolved] + list(command[1:])
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            timeout=PROBE_TIMEOUT,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"found": True, "version": None, "path": resolved, "reason": type(exc).__name__}
    out = (completed.stdout or b"").decode("utf-8", errors="replace")
    err = (completed.stderr or b"").decode("utf-8", errors="replace")
    version = _first_line(out) or _first_line(err)
    return {
        "found": True,
        "version": version,
        "path": resolved,
        "exit_code": completed.returncode,
    }


def detect(paths: Paths | None = None) -> dict:
    """Everything KaiOS can use, and whether this machine has it."""
    resolved = paths or Paths.resolve()

    tools: dict = {}
    tools["python"] = {
        "found": True,
        "version": sys.version.split()[0],
        "path": sys.executable,
        "supported": sys.version_info >= (3, 10),
    }
    tools["git"] = probe(["git", "--version"])
    tools["gh"] = probe(["gh", "--version"])
    tools["databricks"] = probe(["databricks", "--version"])
    tools["code"] = probe(["code", "--version"])

    shell = shutil.which("pwsh") or shutil.which("powershell")
    if shell is None:
        tools["powershell"] = {"found": False, "version": None, "path": None, "reason": "not on PATH"}
    else:
        tools["powershell"] = probe(
            [Path(shell).name, "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            executable=shell,
        )

    return {
        "generated": now_iso(),
        "home": str(resolved.home),
        "home_exists": resolved.home.is_dir(),
        "repo": str(resolved.repo) if resolved.repo else None,
        "tools": tools,
        "mcp_json": _detect_mcp(resolved),
        "copilot_dirs": _detect_copilot_dirs(),
        "config": {
            "path": str(resolved.config_file),
            "present": resolved.config_file.is_file(),
        },
        "missing": sorted(name for name, info in tools.items() if not info.get("found")),
    }


def _detect_mcp(paths: Paths) -> dict:
    candidates = []
    if paths.repo is not None:
        candidates.append(paths.repo / ".vscode" / "mcp.json")
    if paths.cwd is not None:
        candidates.append(paths.cwd / ".vscode" / "mcp.json")
    for candidate in candidates:
        if not candidate.is_file():
            continue
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return {"present": True, "path": str(candidate), "servers": [], "error": str(exc)}
        servers = data.get("servers") if isinstance(data, dict) else None
        names = sorted(servers.keys()) if isinstance(servers, dict) else []
        return {"present": True, "path": str(candidate), "servers": names}
    fallback = candidates[0] if candidates else None
    return {"present": False, "path": str(fallback) if fallback else None, "servers": []}


def _detect_copilot_dirs() -> dict:
    root = Path(os.path.expanduser("~")) / ".copilot"
    out: dict = {"root": str(root), "exists": root.is_dir()}
    for name in COPILOT_DIRS:
        out[name] = (root / name).is_dir()
    return out


# ---------------------------------------------------------------- config


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def load_config(paths: Paths | None = None) -> dict:
    resolved = paths or Paths.resolve()
    base = json.loads(json.dumps(CONFIG_SKELETON))
    if not resolved.config_file.is_file():
        return base
    try:
        stored = json.loads(resolved.config_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return base
    if not isinstance(stored, dict):
        return base
    return _deep_merge(base, stored)


def parse_answers(json_str_or_path: str | dict | Path | None) -> dict:
    """Accept a dict, a path to a JSON file, a JSON string, or ``-`` for stdin."""
    if json_str_or_path is None:
        return {}
    if isinstance(json_str_or_path, dict):
        return dict(json_str_or_path)
    raw = str(json_str_or_path)
    if raw.strip() == "-":
        return json.loads(sys.stdin.read() or "{}")
    candidate = Path(raw)
    stripped = raw.strip()
    if not stripped.startswith("{") and candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def write_config(json_str_or_path: str | dict | Path, paths: Paths | None = None) -> dict:
    """Merge answers into ``CONFIG/config.json`` and return the stored config."""
    resolved = paths or Paths.resolve()
    overlay = parse_answers(json_str_or_path)
    merged = _deep_merge(load_config(resolved), overlay)
    if not merged.get("installed_at"):
        merged["installed_at"] = now_iso()
    merged["projects"] = [_normalize_project(p) for p in (merged.get("projects") or [])]
    resolved.config_file.parent.mkdir(parents=True, exist_ok=True)
    resolved.config_file.write_text(
        json.dumps(merged, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return merged


def _normalize_project(project: dict) -> dict:
    if not isinstance(project, dict):
        return {"name": str(project), "path": "", "url": "", "deploy": "", "stack": [], "aliases": []}
    stack = project.get("stack") or []
    if isinstance(stack, str):
        stack = [part.strip() for part in stack.split(",") if part.strip()]
    aliases = project.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [part.strip() for part in aliases.split(",") if part.strip()]
    out = dict(project)
    out["name"] = str(project.get("name") or "").strip()
    out["path"] = str(project.get("path") or "").strip()
    out["url"] = str(project.get("url") or "").strip()
    out["deploy"] = str(project.get("deploy") or "").strip()
    out["stack"] = [str(s).strip() for s in stack if str(s).strip()]
    out["aliases"] = [str(a).strip() for a in aliases if str(a).strip()]
    return out


# ---------------------------------------------------------------- render


def _template(paths: Paths, name: str) -> str:
    directory = paths.templates_dir
    if directory is None:
        raise FileNotFoundError("no TEMPLATES directory found; is the checkout reachable?")
    target = directory / name
    if not target.is_file():
        raise FileNotFoundError(str(target))
    return target.read_text(encoding="utf-8")


def _fill(body: str, values: dict) -> str:
    out = body
    for key, value in values.items():
        out = out.replace("{{%s}}" % key, "" if value is None else str(value))
    return out


def _json_fill(body: str, values: dict) -> str:
    """Substitute into a JSON template, escaping so Windows paths stay valid JSON."""
    out = body
    for key, value in values.items():
        text = "" if value is None else str(value)
        out = out.replace("{{%s}}" % key, json.dumps(text)[1:-1])
    return out


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return str(path)


def _bullets(items, empty: str = "- (none recorded)") -> str:
    """Render a list as markdown bullets; a string is one bullet, never split.

    Splitting a string on commas would turn one sentence into several broken
    ones, so prose stays whole and only a real list becomes several bullets.
    """
    candidates = [items] if isinstance(items, str) else list(items or [])
    values = [str(item).strip() for item in candidates if str(item).strip()]
    return "\n".join("- %s" % value for value in values) if values else empty


def _prose(value, empty: str = "(not stated)") -> str:
    """Render a field that may be a sentence or a list as one paragraph."""
    if isinstance(value, (list, tuple)):
        joined = " ".join(str(item).strip() for item in value if str(item).strip())
    else:
        joined = str(value or "").strip()
    return joined or empty


def project_slug(name: str) -> str:
    return isa_mod.slugify(name)


def project_goal(project: dict, name: str | None = None) -> str:
    """The seed goal for a project ISA, from whatever the interview captured."""
    label = name or project.get("name") or "this project"
    for key in ("goal", "done_means", "purpose"):
        candidate = _prose(project.get(key), "")
        if candidate:
            return candidate
    return "State what done looks like for %s, as falsifiable claims." % label


def project_glob(project: dict) -> str:
    explicit = str(project.get("glob") or "").strip()
    if explicit:
        return explicit
    path = str(project.get("path") or "").strip().replace("\\", "/").rstrip("/")
    if path:
        tail = path.split("/")[-1]
        if tail:
            return "**/%s/**" % tail
    return "**/%s/**" % project_slug(project.get("name") or "project")


def render(
    answers_path: str | dict | Path | None = None,
    paths: Paths | None = None,
    write: bool = True,
) -> dict:
    """Render every user-facing file from the config, optionally merged with answers."""
    resolved = (paths or Paths.resolve()).ensure()
    config = load_config(resolved)
    if answers_path is not None:
        config = _deep_merge(config, parse_answers(answers_path))
    config["projects"] = [_normalize_project(p) for p in (config.get("projects") or [])]

    stamp = now_iso()
    written: list[str] = []
    result: dict = {
        "generated": stamp,
        "home": str(resolved.home),
        "written": written,
        "projects": [],
        "config_used": str(resolved.config_file),
        "dry_run": not write,
    }

    user = config.get("user") or {}
    optional = config.get("optional") or {}

    profile_text = _fill(
        _template(resolved, "PROFILE.md"),
        {
            "now": stamp,
            "name": user.get("name") or "(not stated)",
            "role": user.get("role") or "(not stated)",
            "team": user.get("team") or "(not stated)",
            "stack_list": _bullets(user.get("stack"), "- (no stack recorded)"),
            "preferences": _bullets(user.get("preferences"), "- (none recorded)"),
            "integrations": _integration_lines(optional),
        },
    )
    if write:
        written.append(_write(resolved.profile, profile_text))

    projects = config["projects"]
    rows = [
        "| %s | `%s` | %s | `%s` | %s |"
        % (
            p.get("name") or "-",
            p.get("path") or "-",
            p.get("url") or "-",
            p.get("deploy") or "-",
            ", ".join(p.get("stack") or []) or "-",
        )
        for p in projects
    ]
    aliases = [
        "| %s | %s |" % (alias, p.get("name"))
        for p in projects
        for alias in (p.get("aliases") or [])
    ]
    projects_text = _fill(
        _template(resolved, "PROJECTS.md"),
        {
            "now": stamp,
            "project_rows": "\n".join(rows) if rows else "| (none yet) | - | - | - | - |",
            "alias_rows": "\n".join(aliases) if aliases else "| (none yet) | - |",
        },
    )
    if write:
        written.append(_write(resolved.projects, projects_text))

    instructions_template = _template(resolved, "PROJECT_INSTRUCTIONS.md")
    for project in projects:
        name = project.get("name") or "project"
        slug = project_slug(name)
        entry: dict = {"name": name, "slug": slug}

        text = _fill(
            instructions_template,
            {
                "now": stamp,
                "name": name,
                "slug": slug,
                "glob": project_glob(project),
                "path": project.get("path") or "(not stated)",
                "url": project.get("url") or "(not stated)",
                "deploy": project.get("deploy") or "(not stated)",
                "stack": ", ".join(project.get("stack") or []) or "(not stated)",
                "purpose": _prose(project.get("purpose"), "(not stated)"),
                "done_means": _bullets(project.get("done_means"), "- (not stated yet)"),
                "pain_points": _bullets(project.get("pain_points"), "- (none recorded yet)"),
                "rules": _bullets(project.get("rules"), "- (none recorded yet)"),
            },
        )
        instructions_path = resolved.projects_dir / ("%s.instructions.md" % slug)
        if write:
            entry["instructions"] = _write(instructions_path, text)
            written.append(entry["instructions"])
        else:
            entry["instructions"] = str(instructions_path)

        isa_path = resolved.projects_dir / slug / "ISA.md"
        if write:
            written_isa = isa_mod.scaffold(
                slug=slug,
                goal=project_goal(project, name),
                paths=resolved,
                task="Work on %s" % name,
                dest=isa_path,
                overwrite=True,
            )
            entry["isa"] = str(written_isa)
            written.append(entry["isa"])
        else:
            entry["isa"] = str(isa_path)
        result["projects"].append(entry)

    mcp_text, mcp_servers = render_mcp(resolved, config)
    result["mcp_servers"] = mcp_servers
    if write:
        written.append(_write(resolved.mcp_json, mcp_text))
    result["mcp_json"] = str(resolved.mcp_json)

    hooks_text, hooks_meta = render_hooks(resolved)
    result["hooks"] = hooks_meta
    if write:
        written.append(_write(resolved.hooks_json, hooks_text))
    result["hooks_json"] = str(resolved.hooks_json)

    return result


def _integration_lines(optional: dict) -> str:
    mcp = optional.get("mcp") or {}
    cli = optional.get("databricks_cli") or {}
    apis = optional.get("apis") or {}
    lines = [
        "- MCP servers enabled: %s"
        % (", ".join(sorted(name for name, on in mcp.items() if on)) or "none"),
        "- Databricks CLI: %s"
        % ("profile %s" % (cli.get("profile") or "default") if cli.get("enabled") else "not linked"),
        "- API keys: %s" % (", ".join(_api_line(n, e) for n, e in sorted(apis.items())) or "none linked"),
    ]
    return "\n".join(lines)


def _api_line(name: str, entry) -> str:
    """One API's env-var name and, when stated, what it is for. Never the key."""
    fields = entry or {}
    env_var = fields.get("env_var") or "(env var not named)"
    purpose = str(fields.get("purpose") or "").strip()
    return "%s via %s%s" % (name, env_var, " for %s" % purpose if purpose else "")


def render_mcp(paths: Paths, config: dict) -> tuple[str, list[str]]:
    """Keep only the servers flagged true, strip every template marker."""
    data = json.loads(_template(paths, "mcp.json"))
    flags = ((config.get("optional") or {}).get("mcp")) or {}
    servers = data.get("servers") or {}
    kept: dict = {}
    for name, entry in servers.items():
        marker = (entry or {}).get("x-kaios") or {}
        flag = str(marker.get("flag") or name)
        if not flags.get(flag):
            continue
        clean = {key: value for key, value in (entry or {}).items() if key != "x-kaios"}
        kept[name] = clean
    out = {"servers": kept}
    return json.dumps(out, indent=2, sort_keys=True) + "\n", sorted(kept.keys())


#: Interpreter names a repo registry may use before absolute paths are rendered.
PYTHON_TOKENS = ("python", "python3", "py", "python.exe", "python3.exe")


def package_root() -> Path:
    """The directory ``import kaios`` resolves from for THIS copy of the package.

    The package ships at ``.github/kaios``, so its parent is the framework
    directory. An installed copy lives at ``$KAIOS_HOME/lib/kaios``, and the same
    rule gives ``$KAIOS_HOME/lib``.
    """
    return Path(__file__).resolve().parent.parent


def framework_dir(repo: Path | None = None) -> Path:
    """Where ``import kaios`` resolves from for one checkout.

    ``<repo>/.github`` in the shipped layout. A checkout made before the framework
    moved under ``.github`` keeps the package at its root, so that is probed too;
    with no checkout at all, this copy's own import root answers.
    """
    if repo is None:
        return package_root()
    for candidate in (Path(repo) / FRAMEWORK_DIR, Path(repo)):
        if (candidate / "kaios" / "__init__.py").is_file():
            return candidate
    return Path(repo) / FRAMEWORK_DIR


def repo_hooks_registry(paths: Paths) -> Path | None:
    """The checked-in hook registry, which is the source of truth for events."""
    if paths.repo is None:
        return None
    candidate = paths.repo / HOOKS_REGISTRY_RELATIVE
    return candidate if candidate.is_file() else None


def _absolute_command(command: str, interpreter: str) -> str:
    """Point a ``python -m kaios.hooks <Event>`` command at a known interpreter."""
    parts = str(command or "").split()
    if not parts:
        return command
    head = parts[0]
    if Path(head).name.lower() in PYTHON_TOKENS:
        parts[0] = interpreter
        return " ".join(parts)
    return command


def _absolute_windows(command: str, wrapper: Path) -> str:
    """Rewrite the path after ``-File`` to the absolute wrapper location."""
    parts = str(command or "").split()
    for index, token in enumerate(parts):
        if token.lower() == "-file" and index + 1 < len(parts):
            parts[index + 1] = str(wrapper)
            return " ".join(parts)
    return command


def _absolute_bash(command: str, wrapper: Path) -> str:
    """Rewrite the path a ``sh <path> <Event>`` line runs to an absolute one."""
    parts = str(command or "").split()
    for index, token in enumerate(parts):
        if Path(token).name.lower() in ("sh", "bash", "sh.exe", "bash.exe"):
            if index + 1 < len(parts):
                parts[index + 1] = str(wrapper)
                return " ".join(parts)
            return command
    return command


def _absolute_entry(entry: dict, interpreter: str, wrapper: Path, shell_wrapper: Path) -> dict:
    """One registry entry with every wrapper path in it made absolute.

    Both entry shapes pass through here. A flat entry carries the command lines
    the Copilot CLI engine reads under ``bash`` and ``powershell``; a Claude
    nested entry carries one under ``hooks[].command``. ``command`` and
    ``windows`` are the older flat spellings and are still rewritten, so a
    hand-edited registry in the previous shape still renders correctly.
    """
    out = dict(entry or {})
    nested = out.get("hooks")
    if isinstance(nested, list):
        out["hooks"] = [
            _absolute_entry(item, interpreter, wrapper, shell_wrapper)
            if isinstance(item, dict)
            else item
            for item in nested
        ]
        return out
    if "command" in out:
        line = _absolute_command(out["command"], interpreter)
        out["command"] = _absolute_windows(line, wrapper)
    if "windows" in out:
        out["windows"] = _absolute_windows(out["windows"], wrapper)
    if "powershell" in out:
        out["powershell"] = _absolute_windows(out["powershell"], wrapper)
    if "bash" in out:
        out["bash"] = _absolute_bash(out["bash"], shell_wrapper)
    return out


def render_hooks(
    paths: Paths,
    python: str | None = None,
    wrapper: str | None = None,
    shell_wrapper: str | None = None,
) -> tuple[str, dict]:
    """The user-level hook registry, with absolute paths for this machine.

    The checked-in ``.github/hooks/kaios.json`` is the source of truth when it
    exists: its event keys, entry shapes and timeouts are preserved exactly, and
    only the wrapper paths become absolute. That matters more than it sounds —
    the key spelling and the entry shape are what decide whether each of
    Copilot's two hook engines can read the file at all, so rendering must not
    normalise either. The shipped template is the fallback for an install with no
    checkout beside it.
    """
    # Wrapper paths are workspace-relative, so they hang off the checkout root.
    # PYTHONPATH is an import root, which is the framework directory inside it —
    # the package is at .github/kaios, not beside the repository root.
    repo = paths.repo or package_root().parent
    framework = framework_dir(paths.repo)
    wrapper_path = Path(wrapper) if wrapper else (repo / WRAPPER_RELATIVE)
    shell_path = Path(shell_wrapper) if shell_wrapper else (repo / SHELL_WRAPPER_RELATIVE)
    interpreter = python or sys.executable or "python"

    source = repo_hooks_registry(paths)
    if source is not None:
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data.get("hooks"), dict):
            raise ValueError("%s has no hooks object" % source)
        hooks: dict = {}
        for event, entries in data["hooks"].items():
            rendered = []
            for entry in entries or []:
                out = _absolute_entry(entry or {}, interpreter, wrapper_path, shell_path)
                # ``env`` belongs to the Copilot CLI engine's own entry schema, so
                # it goes on flat entries only. A Claude nested entry has no such
                # field, and the wrappers find the package from KAIOS_REPO or
                # KAIOS_HOME without it.
                if "hooks" not in out:
                    env = dict(out.get("env") or {})
                    env.setdefault("PYTHONPATH", str(framework))
                    env.setdefault("KAIOS_HOME", str(paths.home))
                    out["env"] = env
                rendered.append(out)
            hooks[event] = rendered
        data["hooks"] = hooks
        data.setdefault("version", 1)
        data["cwd"] = str(repo)
        data["generated"] = now_iso()
        data.pop("x-kaios", None)
    else:
        filled = _json_fill(
            _template(paths, "hooks.json"),
            {
                "now": now_iso(),
                "python": interpreter,
                "repo": str(repo),
                "framework": str(framework),
                "home": str(paths.home),
                "wrapper": str(wrapper_path),
                "shell_wrapper": str(shell_path),
            },
        )
        data = json.loads(filled)
        data.pop("x-kaios", None)
        patterns = data.get("hooks") or {}
        flat = patterns.get("{{event}}")
        nested = patterns.get("{{nested_event}}")
        if flat is None or nested is None:
            raise ValueError("hooks.json template lost its {{event}} entries")
        expanded: dict = {}
        for event in EVENTS:
            key = REGISTRY_EVENT_NAMES[event]
            pattern = nested if event in NESTED_REGISTRY_EVENTS else flat
            marker = "{{nested_event}}" if event in NESTED_REGISTRY_EVENTS else "{{event}}"
            expanded[key] = json.loads(json.dumps(pattern).replace(marker, key))
        data["hooks"] = expanded
        data.setdefault("version", 1)

    events = registered_events(data["hooks"])
    meta = {
        "events": events,
        "event_count": len(events),
        "source": str(source) if source is not None else "template",
        "python": interpreter,
        "repo": str(repo),
        "framework": str(framework),
        "wrapper": str(wrapper_path),
        "wrapper_exists": wrapper_path.is_file(),
        "shell_wrapper": str(shell_path),
        "shell_wrapper_exists": shell_path.is_file(),
        "absolute": os.path.isabs(interpreter) and os.path.isabs(str(wrapper_path)),
        "missing_events": sorted(set(EVENTS) - set(events)),
    }
    return json.dumps(data, indent=2, sort_keys=True) + "\n", meta
