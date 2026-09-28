"""The role-to-model registry, and rendering it into agent frontmatter.

Model names live in exactly one place: ``SYSTEM/CONFIG/models.json`` in the
checkout, overridden by ``$KAIOS_HOME/CONFIG/models.json`` when the user has
picked from what their organization enabled. Agents declare a role with a
``kaios-role:`` line, as either ``# kaios-role: max`` or
``<!-- kaios-role: max -->``; ``apply`` rewrites their ``model:`` list from the
registry so a lineup change never edits prose.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import Paths, doctrine_candidates

DEFAULT_AGENTS_DIR = ".github/agents"

#: Matches the role marker in either comment style, anywhere in the file.
ROLE_RE = re.compile(r"kaios-role\s*:\s*([A-Za-z0-9_-]+)")
_MODEL_KEY_RE = re.compile(r"^(\s*)model\s*:\s*(.*)$")
_LIST_ITEM_RE = re.compile(r"^\s+-\s+")
_ANY_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+\s*:")

FALLBACK_REGISTRY: dict = {
    "convention": "kaios-models-v1",
    "roles": {
        "max": {"purpose": "judgment, planning, review, audits, meta work", "models": []},
        "high": {"purpose": "execution of scoped work", "models": []},
        "medium": {"purpose": "trivial execution, formatting, summaries", "models": []},
        "cross": {"purpose": "second look from a different vendor family", "models": []},
        "third": {"purpose": "third-vendor opinion, very long context", "models": []},
        "research": {"purpose": "web/doc research", "models": []},
    },
    "families": {},
}


def registry_candidates(paths: Paths | None = None) -> list[Path]:
    """Registry locations, highest precedence first."""
    resolved = paths or Paths.resolve()
    out = [resolved.models_file]
    if resolved.repo is not None:
        out += [base / "CONFIG" / "models.json" for base in doctrine_candidates(resolved.repo)]
    package_parent = Path(__file__).resolve().parent.parent
    out += [base / "CONFIG" / "models.json" for base in doctrine_candidates(package_parent)]
    out.append(resolved.doctrine / "CONFIG" / "models.json")
    return out


def registry_path(paths: Paths | None = None) -> Path | None:
    for candidate in registry_candidates(paths):
        if candidate.is_file():
            return candidate
    return None


def load(paths: Paths | None = None) -> dict:
    """The effective registry. Never raises on a missing file; raises on bad JSON."""
    path = registry_path(paths)
    if path is None:
        data = json.loads(json.dumps(FALLBACK_REGISTRY))
        data["source"] = None
        return data
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("roles"), dict):
        raise ValueError("%s has no roles object" % path)
    data["source"] = str(path)
    return data


def show(paths: Paths | None = None) -> dict:
    data = load(paths)
    roles = data.get("roles") or {}
    out = {
        "source": data.get("source"),
        "convention": data.get("convention"),
        "families": data.get("families") or {},
        "roles": {},
        "candidates": [str(c) for c in registry_candidates(paths)],
    }
    for role in sorted(roles):
        entry = roles[role] or {}
        models = [str(m) for m in (entry.get("models") or [])]
        out["roles"][role] = {
            "purpose": entry.get("purpose"),
            "models": models,
            "families": [family_of(m, data) for m in models],
        }
    return out


def models_for(role: str, paths: Paths | None = None, data: dict | None = None) -> list[str]:
    registry = data if data is not None else load(paths)
    entry = (registry.get("roles") or {}).get(str(role).strip().lower())
    if not entry:
        return []
    return [str(m) for m in (entry.get("models") or [])]


def family_of(model_name: str, data: dict | None = None, paths: Paths | None = None) -> str | None:
    """Which vendor family a model name belongs to, by name prefix."""
    registry = data if data is not None else load(paths)
    families = registry.get("families") or {}
    name = str(model_name or "").strip().lower()
    if not name:
        return None
    best: tuple[int, str] | None = None
    for family, prefixes in families.items():
        for prefix in prefixes or []:
            token = str(prefix).strip().lower()
            if token and name.startswith(token):
                if best is None or len(token) > best[0]:
                    best = (len(token), family)
    return best[1] if best else None


def set_role(
    role: str,
    models: list | str,
    paths: Paths | None = None,
    purpose: str | None = None,
) -> dict:
    """Write a role's model list to the user registry in KAIOS_HOME."""
    resolved = paths or Paths.resolve()
    name = str(role or "").strip().lower()
    if not name:
        raise ValueError("set needs a role name")
    if isinstance(models, str):
        wanted = [m.strip() for m in models.split(",") if m.strip()]
    else:
        wanted = [str(m).strip() for m in models if str(m).strip()]
    if not wanted:
        raise ValueError("set needs at least one model name")

    if resolved.models_file.is_file():
        data = json.loads(resolved.models_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    else:
        base = load(resolved)
        base.pop("source", None)
        data = base
    data.setdefault("convention", "kaios-models-v1")
    data.setdefault("roles", {})
    data.setdefault("families", (load(resolved).get("families") or {}))
    entry = data["roles"].get(name) or {}
    if purpose:
        entry["purpose"] = purpose
    entry.setdefault("purpose", "")
    entry["models"] = wanted
    data["roles"][name] = entry

    resolved.models_file.parent.mkdir(parents=True, exist_ok=True)
    resolved.models_file.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return {"role": name, "models": wanted, "file": str(resolved.models_file)}


#: ``kaios models set`` reads better than ``set_role`` from the CLI.
set = set_role  # noqa: A001 - deliberate public alias matching the CLI verb


def format_model_line(models: list[str]) -> str:
    inner = ", ".join("'%s'" % str(m).replace("'", "\\'") for m in models)
    return "model: [%s]" % inner


def role_of(text: str) -> str | None:
    match = ROLE_RE.search(text)
    return match.group(1).strip().lower() if match else None


def rewrite_model(text: str, models: list[str]) -> str:
    """Replace the frontmatter ``model:`` value, preserving every other byte."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("file has no frontmatter block")
    end = 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end == 0:
        raise ValueError("frontmatter block is not closed")

    crlf = lines[0].endswith("\r")
    new_line = format_model_line(models) + ("\r" if crlf else "")

    start = None
    stop = None
    for index in range(1, end):
        if _MODEL_KEY_RE.match(lines[index].rstrip("\r")):
            start = index
            stop = index + 1
            while stop < end:
                candidate = lines[stop].rstrip("\r")
                if _LIST_ITEM_RE.match(candidate) and not _ANY_KEY_RE.match(candidate.strip()):
                    stop += 1
                    continue
                break
            break

    if start is None:
        insert_at = end
        for index in range(1, end):
            if lines[index].rstrip("\r").lower().startswith("name:"):
                insert_at = index + 1
                break
        updated = lines[:insert_at] + [new_line] + lines[insert_at:]
    else:
        updated = lines[:start] + [new_line] + lines[stop:]
    return "\n".join(updated)


def agents_directory(agents_dir: Path | str | None = None, paths: Paths | None = None) -> Path:
    if agents_dir is not None:
        return Path(agents_dir)
    resolved = paths or Paths.resolve()
    base = resolved.repo if resolved.repo is not None else (resolved.cwd or Path.cwd())
    return base / DEFAULT_AGENTS_DIR


def apply(
    agents_dir: Path | str | None = None,
    paths: Paths | None = None,
    dry_run: bool = False,
) -> dict:
    """Rewrite every role-tagged agent's ``model:`` from the registry."""
    resolved = paths or Paths.resolve()
    directory = agents_directory(agents_dir, resolved)
    data = load(resolved)

    result: dict = {
        "agents_dir": str(directory),
        "source": data.get("source"),
        "changed": [],
        "unchanged": [],
        "skipped": [],
        "errors": [],
        "dry_run": bool(dry_run),
    }
    if not directory.is_dir():
        result["skipped"].append({"file": str(directory), "reason": "agents directory not found"})
        return result

    for path in sorted(directory.glob("*.agent.md")):
        name = path.name
        try:
            # newline="" so a CRLF file stays CRLF: the body must survive byte
            # for byte, and only the model line may change.
            with open(path, "r", encoding="utf-8", newline="") as handle:
                text = handle.read()
        except OSError as exc:
            result["errors"].append({"file": name, "reason": str(exc)})
            continue
        role = role_of(text)
        if role is None:
            result["skipped"].append({"file": name, "reason": "no kaios-role line"})
            continue
        models = models_for(role, data=data)
        if not models:
            result["errors"].append({"file": name, "reason": "role %r has no models" % role})
            continue
        try:
            updated = rewrite_model(text, models)
        except ValueError as exc:
            result["errors"].append({"file": name, "reason": str(exc)})
            continue
        if updated == text:
            result["unchanged"].append({"file": name, "role": role, "models": models})
            continue
        if not dry_run:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(updated)
        result["changed"].append({"file": name, "role": role, "models": models})

    return result
