"""Integrity gates: containment, doc cross-references, version drift, imports.

Each check returns ``(ok, findings)``. A finding is a dict with ``level``
(``error`` or ``warn``), ``code``, ``file``, and ``message``; ``ok`` is false
when any error-level finding exists. The CLI turns that into exit code 1.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from .paths import (
    DOCTRINE_DIR,
    FRAMEWORK_DIR,
    LEGACY_DOCTRINE_DIRS,
    repo_doctrine_candidates,
)

SKIP_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        ".venv",
        "venv",
        ".idea",
        ".tox",
    }
)
MAX_TEXT_BYTES = 2 * 1024 * 1024
#: Where the containment term list lives under a checkout root, current layout
#: first. The flat form is a checkout made before the framework moved under
#: ``.github``; probing both means the gate never silently checks nothing.
TERMS_FILES = (FRAMEWORK_DIR + "/tests/containment.txt", "tests/containment.txt")

#: The shipped location, for a caller that needs a single name.
TERMS_FILE = TERMS_FILES[0]
EXTRA_TERMS_ENV = "KAIOS_CONTAINMENT_EXTRA"
FRESHNESS_KEYS = ("version", "last_updated", "convention")

#: Doctrine tree names this gate recognises: the current one, then the legacy
#: name, so a checkout made before the rename still reports honestly.
DOCTRINE_DIR_NAMES = (DOCTRINE_DIR,) + LEGACY_DOCTRINE_DIRS

#: Where documentation lives, for the docs gate. ``.github`` carries the whole
#: framework now, the doctrine tree included; the bare doctrine names stay so a
#: checkout made before the move is still scanned.
DOC_AREAS = DOCTRINE_DIR_NAMES + (FRAMEWORK_DIR,)
_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*([^)\s]+)")
_BADGE_VERSION_RE = re.compile(r"\b(\d+\.\d+\.\d+)\b")


def _finding(level: str, code: str, file: str, message: str, **extra) -> dict:
    out = {"level": level, "code": code, "file": file, "message": message}
    out.update(extra)
    return out


def _ok(findings: list[dict]) -> bool:
    return not any(f.get("level") == "error" for f in findings)


def _walk(root: Path):
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(current) / name


def _read_text(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return None
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------- containment


def load_terms(terms_file: Path | None, extra_terms_file: Path | None = None) -> list[str]:
    terms: list[str] = []
    for source in (terms_file, extra_terms_file):
        if source is None or not Path(source).is_file():
            continue
        try:
            raw = Path(source).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in raw.split("\n"):
            term = line.strip()
            if not term or term.startswith("#"):
                continue
            if term not in terms:
                terms.append(term)
    return terms


def terms_file_for(root: Path | str) -> Path:
    """The term list a checkout carries, or where the shipped one belongs."""
    base = Path(root)
    candidates = [base / name for name in TERMS_FILES]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def containment(
    root: Path | str,
    terms_file: Path | str | None = None,
    extra_terms_file: Path | str | None = None,
) -> tuple[bool, list[dict]]:
    """Fixed-string, case-insensitive scan for every forbidden term."""
    base = Path(root).resolve()
    primary = Path(terms_file).resolve() if terms_file else terms_file_for(base).resolve()
    extra_raw = extra_terms_file or os.environ.get(EXTRA_TERMS_ENV) or None
    extra = Path(extra_raw).resolve() if extra_raw else None

    findings: list[dict] = []
    terms = load_terms(primary if primary.is_file() else None, extra)
    if not terms:
        findings.append(
            _finding(
                "warn",
                "W_NO_TERMS",
                _relative(primary, base),
                "no containment terms found; nothing was checked",
            )
        )
        return _ok(findings), findings

    lowered = [(term, term.lower()) for term in terms]
    excluded = {primary}
    if extra is not None:
        excluded.add(extra)

    for path in _walk(base):
        if path.resolve() in excluded:
            continue
        text = _read_text(path)
        if text is None:
            continue
        relative = _relative(path, base)
        for number, line in enumerate(text.split("\n"), start=1):
            haystack = line.lower()
            for term, needle in lowered:
                if needle in haystack:
                    findings.append(
                        _finding(
                            "error",
                            "E_CONTAINMENT",
                            relative,
                            "line %d contains a forbidden term" % number,
                            line=number,
                            term=term,
                        )
                    )
    return _ok(findings), findings


# ---------------------------------------------------------------- docs


def _frontmatter_keys(text: str) -> list[str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return []
    keys: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if match:
            keys.append(match.group(1).lower())
    return keys


def _doctrine_relative(posix: str) -> str | None:
    """The path inside the doctrine tree, or ``None`` when it is elsewhere.

    The doctrine tree lives at ``.github/SYSTEM``; the bare ``SYSTEM`` form is
    still recognised so a checkout made before the framework moved under
    ``.github`` reports the same way.
    """
    for prefix in (FRAMEWORK_DIR + "/", ""):
        if not posix.startswith(prefix):
            continue
        tail = posix[len(prefix) :]
        if tail.split("/", 1)[0] in DOCTRINE_DIR_NAMES:
            return tail
    return None


def _required_keys(relative: str) -> list[str]:
    posix = relative.replace("\\", "/")
    doctrine = _doctrine_relative(posix)
    if doctrine is not None:
        if doctrine.split("/")[1:2] == ["TEMPLATES"]:
            # A template carries the frontmatter of the thing it renders, not
            # the freshness frontmatter of a doc.
            return []
        return list(FRESHNESS_KEYS)
    if re.fullmatch(r"\.github/skills/[^/]+/SKILL\.md", posix):
        return ["name", "description"]
    if posix.startswith(".github/agents/") and posix.endswith(".agent.md"):
        return ["name", "description", "tools", "model"]
    if posix.startswith(".github/instructions/") and posix.endswith(".instructions.md"):
        return ["applyto"]
    return []


def docs(root: Path | str) -> tuple[bool, list[dict]]:
    """Frontmatter where the blueprint requires it, and links that resolve."""
    base = Path(root).resolve()
    findings: list[dict] = []
    targets: list[Path] = []
    for area in DOC_AREAS:
        directory = base / area
        if not directory.is_dir():
            continue
        for path in _walk(directory):
            if path.suffix.lower() == ".md":
                targets.append(path)

    if not targets:
        findings.append(
            _finding("warn", "W_NO_DOCS", ".", "no markdown found under %s" % " or ".join(DOC_AREAS))
        )
        return _ok(findings), findings

    for path in sorted(targets):
        relative = _relative(path, base)
        text = _read_text(path)
        if text is None:
            findings.append(_finding("error", "E_UNREADABLE", relative, "file is not utf-8 text"))
            continue

        required = _required_keys(relative)
        if required:
            present = _frontmatter_keys(text)
            missing = [key for key in required if key not in present]
            if missing:
                findings.append(
                    _finding(
                        "error",
                        "E_FRONTMATTER",
                        relative,
                        "frontmatter is missing %s" % ", ".join(missing),
                    )
                )

        for target in _LINK_RE.findall(_strip_code(text)):
            link = target.strip().strip("<>")
            if not link or link.startswith("#"):
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", link):
                continue
            cleaned = link.split("#", 1)[0].split("?", 1)[0]
            if not cleaned:
                continue
            if not _resolves(cleaned, path, base):
                findings.append(
                    _finding(
                        "error",
                        "E_DEAD_LINK",
                        relative,
                        "relative link does not resolve: %s" % link,
                    )
                )
    return _ok(findings), findings


def _resolves(link: str, source: Path, base: Path) -> bool:
    """Does a relative markdown link point at something that exists?

    Both conventions count: relative to the file, and written from the repo root
    (``.github/SYSTEM/DOCUMENTATION/X.md``), which docs in this repo use freely.
    """
    if link.startswith("/"):
        return (base / link.lstrip("/")).exists()
    return (source.parent / link).exists() or (base / link).exists()


def _strip_code(text: str) -> str:
    without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`\n]*`", "", without_fences)


# ---------------------------------------------------------------- versions


def version_locations(root: Path | str) -> list[Path]:
    """VERSION locations under a checkout root, current layout first."""
    base = Path(root)
    return [candidate / "VERSION" for candidate in repo_doctrine_candidates(base)] + [
        base / "VERSION"
    ]


def algorithm_dir(root: Path | str) -> Path:
    """The doctrine ALGORITHM directory, preferring one that exists."""
    for candidate in repo_doctrine_candidates(root):
        if (candidate / "ALGORITHM").is_dir():
            return candidate / "ALGORITHM"
    return Path(root) / FRAMEWORK_DIR / DOCTRINE_DIR / "ALGORITHM"


def version_location(root: Path | str) -> Path:
    """The VERSION file a checkout actually carries, or where it belongs."""
    candidates = version_locations(root)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def docs_version(root: Path | str) -> str | None:
    for candidate in version_locations(root):
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            return text.splitlines()[0].strip() if text else None
    return None


def versions(root: Path | str, package_version: str | None = None) -> tuple[bool, list[dict]]:
    """VERSION, the package, and the README badge must agree."""
    base = Path(root).resolve()
    findings: list[dict] = []

    version_label = _relative(version_location(base), base)
    shipped = docs_version(base)
    if shipped is None:
        findings.append(_finding("error", "E_NO_VERSION", version_label, "VERSION file is missing"))
    elif not re.fullmatch(r"\d+\.\d+\.\d+", shipped):
        findings.append(
            _finding("error", "E_VERSION_FORMAT", version_label, "%r is not major.minor.patch" % shipped)
        )

    if package_version is None:
        try:
            from . import __version__ as package_version  # type: ignore
        except ImportError:
            package_version = None
    if shipped is not None and package_version is not None and shipped != package_version:
        findings.append(
            _finding(
                "error",
                "E_VERSION_DRIFT",
                FRAMEWORK_DIR + "/kaios/__init__.py",
                "package reports %s but VERSION says %s" % (package_version, shipped),
            )
        )

    readme = base / "README.md"
    if readme.is_file() and shipped is not None:
        text = _read_text(readme) or ""
        badge_line = None
        for line in text.split("\n"):
            lowered = line.lower()
            if "version" in lowered and _BADGE_VERSION_RE.search(line):
                badge_line = line
                break
        if badge_line is not None:
            found = _BADGE_VERSION_RE.search(badge_line)
            if found and found.group(1) != shipped:
                findings.append(
                    _finding(
                        "error",
                        "E_README_VERSION",
                        "README.md",
                        "README names %s but VERSION says %s" % (found.group(1), shipped),
                    )
                )

    algorithm = algorithm_dir(base)
    latest = algorithm / "LATEST"
    latest_label = _relative(latest, base)
    if not latest.is_file():
        findings.append(
            _finding("error", "E_NO_LATEST", latest_label, "the doctrine pointer is missing")
        )
    else:
        named = (_read_text(latest) or "").strip().splitlines()
        pointer = named[0].strip() if named else ""
        if not pointer:
            findings.append(_finding("error", "E_EMPTY_LATEST", latest_label, "the pointer is empty"))
        else:
            stem = pointer[1:] if pointer.startswith("v") else pointer
            candidates = [
                algorithm / pointer,
                algorithm / ("%s.md" % pointer),
                algorithm / ("v%s" % stem),
                algorithm / ("v%s.md" % stem),
            ]
            if not any(c.is_file() for c in candidates):
                findings.append(
                    _finding(
                        "error",
                        "E_LATEST_TARGET",
                        latest_label,
                        "points at %r, which does not exist" % pointer,
                    )
                )
    return _ok(findings), findings


# ---------------------------------------------------------------- imports


def _local_names(directory: Path, roots, cache: dict) -> set:
    """Top-level names importable from a file's own directory or an import root.

    This is what keeps the rule honest: the ban is on third-party packages, not
    on a test module importing its own helper from beside it. ``.github`` is an
    import root as well as the checkout, because that is where the package and
    the test package live and what ``PYTHONPATH`` points at.
    """
    key = str(directory)
    if key in cache:
        return cache[key]
    names: set = set()
    for base in (directory,) + tuple(roots):
        if not base.is_dir():
            continue
        try:
            children = list(base.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_file() and child.suffix == ".py":
                names.add(child.stem)
            elif child.is_dir() and (child / "__init__.py").is_file():
                names.add(child.name)
    cache[key] = names
    return names


def imports(root: Path | str) -> tuple[bool, list[dict]]:
    """Every .py file may import only the standard library and local modules."""
    base = Path(root).resolve()
    findings: list[dict] = []
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    stdlib.add("kaios")
    local_cache: dict = {}
    import_roots = (base, base / FRAMEWORK_DIR)

    checked = 0
    for path in _walk(base):
        if path.suffix != ".py":
            continue
        text = _read_text(path)
        relative = _relative(path, base)
        if text is None:
            findings.append(_finding("error", "E_UNREADABLE", relative, "file is not utf-8 text"))
            continue
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            findings.append(
                _finding("error", "E_SYNTAX", relative, "cannot parse: line %s %s" % (exc.lineno, exc.msg))
            )
            continue
        checked += 1
        allowed = stdlib | _local_names(path.parent, import_roots, local_cache)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top not in allowed:
                        findings.append(
                            _finding(
                                "error",
                                "E_NON_STDLIB",
                                relative,
                                "line %d imports %s, which is not in the standard library"
                                % (node.lineno, top),
                                module=top,
                                line=node.lineno,
                            )
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    continue
                top = (node.module or "").split(".")[0]
                if top and top not in allowed:
                    findings.append(
                        _finding(
                            "error",
                            "E_NON_STDLIB",
                            relative,
                            "line %d imports from %s, which is not in the standard library"
                            % (node.lineno, top),
                            module=top,
                            line=node.lineno,
                        )
                    )
    if checked == 0:
        findings.append(_finding("warn", "W_NO_PYTHON", ".", "no python files found to check"))
    return _ok(findings), findings


# ---------------------------------------------------------------- reporting


CHECKS = ("containment", "docs", "versions", "imports")


def run(name: str, root: Path | str, **kwargs) -> dict:
    """Run one named check and return a JSON-ready report.

    Findings carry the time the scan ran and, per file, when that file was last
    written. A finding quoted somewhere else is otherwise undatable: in a tree
    where nothing is committed there is no revision to anchor it to, so a report
    read an hour later cannot be told apart from a current one.
    """
    if name not in CHECKS:
        raise ValueError("unknown check %r; expected one of %s" % (name, ", ".join(CHECKS)))
    function = {"containment": containment, "docs": docs, "versions": versions, "imports": imports}[name]
    base = Path(root).resolve()
    ok, findings = function(root, **kwargs)
    for finding in findings:
        stamp = _modified(base, finding.get("file"))
        if stamp is not None:
            finding["file_modified"] = stamp
    return {
        "check": name,
        "root": str(base),
        "generated": _now_iso(),
        "ok": bool(ok),
        "errors": len([f for f in findings if f.get("level") == "error"]),
        "warnings": len([f for f in findings if f.get("level") == "warn"]),
        "findings": findings,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _modified(root: Path, relative) -> str | None:
    """When the file a finding names was last written, if it still exists."""
    if not relative or relative in (".", ""):
        return None
    try:
        stat = (root / str(relative)).stat()
    except OSError:
        return None
    return datetime.fromtimestamp(stat.st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_markdown(report: dict) -> str:
    lines = [
        "# integrity %s" % report.get("check"),
        "",
        "%s — %d error(s), %d warning(s)"
        % ("OK" if report.get("ok") else "FAILED", report.get("errors", 0), report.get("warnings", 0)),
        "",
    ]
    if report.get("generated"):
        lines += ["Scanned `%s` at %s." % (report.get("root"), report["generated"]), ""]
    findings = report.get("findings") or []
    if findings:
        lines += ["| level | code | file | file written | message |", "|---|---|---|---|---|"]
        for finding in findings:
            lines.append(
                "| %s | %s | `%s` | %s | %s |"
                % (
                    finding.get("level"),
                    finding.get("code"),
                    finding.get("file"),
                    finding.get("file_modified") or "-",
                    str(finding.get("message") or "").replace("|", "\\|"),
                )
            )
        lines.append("")
    else:
        lines += ["No findings.", ""]
    return "\n".join(lines)


def as_json(report: dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True)
