"""Doctor: one pass over everything that has to be true for KaiOS to work.

Each check reports PASS, WARN, or FAIL. Only FAIL is fatal, because almost
everything in KaiOS is optional — a fresh install with nothing linked is healthy.
"""

from __future__ import annotations

import sys

from . import __version__, integrity
from . import isa as isa_mod
from . import memory as memory_mod
from . import models as models_mod
from .paths import Paths

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


def _check(name: str, status: str, detail: str) -> dict:
    return {"name": name, "status": status, "detail": detail}


def run(paths: Paths | None = None) -> dict:
    resolved = paths or Paths.resolve()
    checks: list[dict] = []

    checks.append(_python())
    checks.append(_home(resolved))
    checks.append(_config(resolved))
    checks.append(_doctrine(resolved))
    checks.append(_models(resolved))
    checks.append(_hooks(resolved))
    checks.append(_active_isa(resolved))
    checks.append(_memory(resolved))
    checks.extend(_repo_checks(resolved))

    counts = {PASS: 0, WARN: 0, FAIL: 0}
    for check in checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    return {
        "version": __version__,
        "home": str(resolved.home),
        "repo": str(resolved.repo) if resolved.repo else None,
        "ok": counts[FAIL] == 0,
        "counts": counts,
        "checks": checks,
    }


def _python() -> dict:
    version = sys.version.split()[0]
    if sys.version_info >= (3, 10):
        return _check("python", PASS, "%s (3.10+ required)" % version)
    return _check("python", FAIL, "%s is older than the required 3.10" % version)


def _home(paths: Paths) -> dict:
    try:
        paths.ensure()
    except OSError as exc:
        return _check("home writable", FAIL, "cannot create %s: %s" % (paths.home, exc))
    probe = paths.state / ".doctor-write-probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return _check("home writable", FAIL, "%s is not writable: %s" % (paths.home, exc))
    return _check("home writable", PASS, str(paths.home))


def _config(paths: Paths) -> dict:
    if paths.config_file.is_file():
        return _check("config", PASS, str(paths.config_file))
    return _check(
        "config",
        WARN,
        "no config yet at %s; run the setup interview" % paths.config_file,
    )


def _doctrine(paths: Paths) -> dict:
    installed = paths.doctrine / "ALGORITHM" / "LATEST"
    if installed.is_file():
        return _check("doctrine", PASS, "installed at %s" % installed)
    repo_doctrine = paths.repo_doctrine
    if repo_doctrine is not None and (repo_doctrine / "ALGORITHM").is_dir():
        return _check("doctrine", WARN, "not installed; reachable in the checkout at %s" % repo_doctrine)
    if repo_doctrine is not None:
        return _check("doctrine", WARN, "checkout found at %s but no ALGORITHM directory yet" % repo_doctrine)
    return _check("doctrine", WARN, "not installed and no checkout reachable from here")


def _models(paths: Paths) -> dict:
    path = models_mod.registry_path(paths)
    if path is None:
        return _check("models registry", WARN, "no registry found; roles fall back to empty lists")
    try:
        data = models_mod.load(paths)
    except (OSError, ValueError) as exc:
        return _check("models registry", FAIL, "%s does not parse: %s" % (path, exc))
    roles = data.get("roles") or {}
    empty = sorted(role for role, entry in roles.items() if not (entry or {}).get("models"))
    if empty:
        return _check(
            "models registry",
            WARN,
            "%s parses; roles with no models: %s" % (path, ", ".join(empty)),
        )
    return _check("models registry", PASS, "%d roles from %s" % (len(roles), path))


def _hooks(paths: Paths) -> dict:
    candidates = [paths.hooks_json]
    if paths.repo is not None:
        candidates.append(paths.repo / ".github" / "hooks" / "kaios.json")
    found = [str(c) for c in candidates if c.is_file()]
    if found:
        return _check("hooks registry", PASS, ", ".join(found))
    return _check(
        "hooks registry",
        WARN,
        "no hook registry at %s" % " or ".join(str(c) for c in candidates),
    )


def _active_isa(paths: Paths) -> dict:
    # A repo ISA that exists but cannot be read is a failure, not an absence:
    # find_active would skip it and the problem would never surface.
    repo_isa = paths.repo_isa
    if repo_isa is not None:
        try:
            isa_mod.parse(repo_isa)
        except (OSError, ValueError) as exc:
            return _check("active ISA", FAIL, "%s does not parse: %s" % (repo_isa, exc))

    try:
        active = isa_mod.find_active(paths)
    except OSError as exc:
        return _check("active ISA", FAIL, "could not look for one: %s" % exc)
    if active is None:
        return _check("active ISA", WARN, "none open; scaffold one before building")
    try:
        parsed = isa_mod.parse(active)
    except (OSError, ValueError) as exc:
        return _check("active ISA", FAIL, "%s does not parse: %s" % (active, exc))
    findings = isa_mod.check(parsed)
    errors = isa_mod.errors(findings)
    info = isa_mod.status(parsed)
    if errors:
        return _check(
            "active ISA",
            WARN,
            "%s parses but has %d check error(s): %s"
            % (active.name, len(errors), "; ".join(f.code for f in errors[:4])),
        )
    return _check(
        "active ISA",
        PASS,
        "%s — %s, frontier %s" % (info["slug"], info["counted"], ", ".join(info["frontier"][:3]) or "none"),
    )


def _memory(paths: Paths) -> dict:
    try:
        report = memory_mod.health(paths)
    except OSError as exc:
        return _check("memory", FAIL, "unreadable: %s" % exc)
    if report["missing_dirs"]:
        return _check("memory", WARN, "missing: %s" % ", ".join(report["missing_dirs"]))
    if not report["captures"]:
        return _check("memory", WARN, "no captures yet at %s" % paths.captures)
    return _check(
        "memory",
        PASS,
        "%d capture(s), %d note(s), last %s"
        % (report["captures"], report["knowledge_notes"], report["last_capture"]),
    )


def _repo_checks(paths: Paths) -> list[dict]:
    if paths.repo is None:
        return [
            _check("containment", WARN, "no checkout reachable from here; nothing to scan"),
            _check("stdlib only", WARN, "no checkout reachable from here; nothing to scan"),
        ]
    root = paths.repo
    out: list[dict] = []

    try:
        ok, findings = integrity.containment(root)
    except OSError as exc:
        out.append(_check("containment", FAIL, "scan failed: %s" % exc))
    else:
        hits = [f for f in findings if f.get("level") == "error"]
        if ok and not hits:
            out.append(_check("containment", PASS, "no forbidden terms in %s" % root))
        elif hits:
            detail = "%d hit(s), first: %s line %s" % (
                len(hits),
                hits[0].get("file"),
                hits[0].get("line"),
            )
            out.append(_check("containment", FAIL, detail))
        else:
            out.append(_check("containment", FAIL, "the scan reported a failure with no hits"))

    try:
        ok, findings = integrity.imports(root)
    except OSError as exc:
        out.append(_check("stdlib only", FAIL, "scan failed: %s" % exc))
    else:
        bad = [f for f in findings if f.get("level") == "error"]
        if ok and not bad:
            out.append(_check("stdlib only", PASS, "every import is in the standard library"))
        elif bad:
            detail = "%d finding(s), first: %s %s" % (
                len(bad),
                bad[0].get("file"),
                bad[0].get("message"),
            )
            out.append(_check("stdlib only", FAIL, detail))
        else:
            out.append(_check("stdlib only", FAIL, "the scan reported a failure with no findings"))
    return out


def to_markdown(report: dict) -> str:
    lines = [
        "# kaios doctor",
        "",
        "KaiOS %s — %s (%d pass, %d warn, %d fail)"
        % (
            report.get("version"),
            "healthy" if report.get("ok") else "needs attention",
            report["counts"].get(PASS, 0),
            report["counts"].get(WARN, 0),
            report["counts"].get(FAIL, 0),
        ),
        "",
        "| check | status | detail |",
        "|---|---|---|",
    ]
    for check in report.get("checks") or []:
        lines.append(
            "| %s | %s | %s |"
            % (check["name"], check["status"], str(check["detail"]).replace("|", "\\|"))
        )
    lines.append("")
    return "\n".join(lines)
