"""The Ideal State Artifact: parse it, check it, and say what is takeable now.

An ISA is markdown. Frontmatter carries ``phase`` and ``progress``; H2 blocks
carry the prose; ``### F<n>`` blocks group claims; a claim is a checkbox bullet
whose id is ``ISC-<n>``. Anti-claims are ``- A<n>:`` bullets. Everything here is
tolerant of formatting drift and strict about the five things that make a claim
falsifiable.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .paths import Paths

COMPLETE_PHASES = ("complete", "completed", "closed", "done", "shipped")

#: A claim line. The id may be nested (``ISC-7.1``), so the number part takes
#: dotted segments before the colon separator is consumed.
_CLAIM_RE = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(ISC[-_ ]?(\d+(?:\.\d+)*))\s*[:.·]?\s*(.*)$")
_ANTI_ID_RE = re.compile(r"^\s*[-*]\s*(?:\[[ xX]\]\s*)?(A(\d+))\s*[:.]\s*(.*)$")
_ANTI_WORD_RE = re.compile(r"^\s*[-*]\s*Anti\s*[:.]\s*(.*)$", re.IGNORECASE)
_BARE_BULLET_RE = re.compile(r"^\s*[-*]\s+(?!\[)(.+)$")
_FEATURE_RE = re.compile(r"^###\s+(F\d+)\s*(?:[·:\-–—]\s*)?(.*)$")
_WHY_RE = re.compile(r"^\s*Why\s*:\s*(.*)$", re.IGNORECASE)
#: The edge: the last parenthetical of the body, with an optional trailing
#: period. Leaving the period out silently dropped the edge, which blinded the
#: unknown-prerequisite, self-reference and cycle checks.
_AFTER_RE = re.compile(r"\(\s*after\s*:\s*([^)]*)\)\s*\.?\s*$", re.IGNORECASE)

#: The separator that introduces an evidence stub: em dash, en dash, or hyphen.
#: Matched as a separator rather than end-anchored so the LAST one wins.
_EVIDENCE_SEP_RE = re.compile(r"(?:—|–|-{1,2})\s*evidence\s*:\s*", re.IGNORECASE)

#: The falsifier separator, in the one spelling the format defines.
FALSIFIER_TOKEN = "Falsifier:"

_DROPPED_RE = re.compile(r"\[\s*DROPPED\s*:?\s*([^\]]*)\]", re.IGNORECASE)
_ISC_REF_RE = re.compile(r"(?:ISC[-_ ]?)?(\d+(?:\.\d+)*)")
_CODE_SPAN_RE = re.compile(r"`[^`]*`")
_PROGRESS_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d+)\s*$")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_claim_id(raw: str) -> str:
    match = _ISC_REF_RE.search(raw)
    return "ISC-" + match.group(1) if match else raw.strip()


# ---------------------------------------------------------------- data


@dataclass
class Claim:
    id: str
    text: str
    checked: bool = False
    dropped: bool = False
    after: list[str] = field(default_factory=list)
    evidence: str | None = None
    feature: str | None = None
    anti: bool = False
    num: int = 0
    line: int = 0
    raw: str = ""
    section: str | None = None
    statement: str = ""
    falsifier: str | None = None
    order: tuple = ()

    @property
    def open(self) -> bool:
        return not self.checked and not self.dropped

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "statement": self.statement,
            "falsifier": self.falsifier,
            "checked": self.checked,
            "dropped": self.dropped,
            "after": list(self.after),
            "evidence": self.evidence,
            "feature": self.feature,
            "anti": self.anti,
            "num": self.num,
            "line": self.line,
        }


@dataclass
class Feature:
    id: str
    name: str
    why: str = ""
    claims: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "why": self.why, "claims": list(self.claims)}


@dataclass
class Finding:
    level: str  # ERROR | WARN
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message}


@dataclass
class ISA:
    path: Path | None
    frontmatter: dict
    title: str
    sections: dict
    claims: list[Claim] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    text: str = ""

    @property
    def slug(self) -> str:
        value = str(self.frontmatter.get("slug") or "").strip()
        if value:
            return value
        if self.path is not None:
            parent = self.path.parent.name
            if parent and parent not in (".", "/"):
                return parent
            return self.path.stem
        return "isa"

    @property
    def phase(self) -> str:
        return str(self.frontmatter.get("phase") or "").strip()

    @property
    def complete(self) -> bool:
        return self.phase.lower() in COMPLETE_PHASES

    def isc(self) -> list[Claim]:
        return [c for c in self.claims if not c.anti]

    def anti(self) -> list[Claim]:
        return [c for c in self.claims if c.anti]

    def by_id(self, claim_id: str) -> Claim | None:
        for claim in self.claims:
            if claim.id == claim_id:
                return claim
        return None

    def section(self, name: str) -> str | None:
        wanted = name.strip().lower()
        for key, body in self.sections.items():
            if key.strip().lower() == wanted:
                return body
        return None


# ---------------------------------------------------------------- frontmatter


def parse_frontmatter(lines: list[str]) -> tuple[dict, int]:
    """Flat ``key: value`` YAML plus simple lists. Returns (mapping, body_start)."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    end = 0
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end == 0:
        return {}, 0

    data: dict = {}
    pending_key: str | None = None
    for raw in lines[1:end]:
        line = raw.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        item = re.match(r"^\s*-\s+(.*)$", line)
        if item and pending_key:
            data.setdefault(pending_key, [])
            if isinstance(data[pending_key], list):
                data[pending_key].append(_scalar(item.group(1)))
            continue
        pair = re.match(r"^([A-Za-z0-9_.-]+)\s*:\s*(.*)$", line)
        if not pair:
            continue
        key, value = pair.group(1), pair.group(2).strip()
        if not value:
            pending_key = key
            data[key] = []
            continue
        pending_key = None
        data[key] = _inline(value)
    return data, end + 1


def _scalar(value: str):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    lowered = value.lower()
    if lowered in ("true", "yes"):
        return True
    if lowered in ("false", "no"):
        return False
    if lowered in ("null", "~", "none"):
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _inline(value: str):
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in inner.split(",") if part.strip()]
    return _scalar(value)


# ---------------------------------------------------------------- parse


def parse(path: Path | str) -> ISA:
    target = Path(path)
    return parse_text(target.read_text(encoding="utf-8"), path=target)


def parse_text(text: str, path: Path | None = None) -> ISA:
    lines = text.split("\n")
    frontmatter, start = parse_frontmatter(lines)

    title = ""
    sections: dict = {}
    section_name: str | None = None
    section_lines: list[str] = []
    features: list[Feature] = []
    feature: Feature | None = None
    claims: list[Claim] = []
    anti_counter = 0
    await_why = False

    def close_section() -> None:
        if section_name is not None:
            sections[section_name] = "\n".join(section_lines).strip("\n")

    for offset in range(start, len(lines)):
        line = lines[offset].rstrip("\r")
        number = offset + 1

        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            close_section()
            section_name = line[3:].strip()
            section_lines = []
            feature = None
            await_why = False
            continue
        if section_name is not None:
            section_lines.append(line)

        feature_match = _FEATURE_RE.match(line)
        if feature_match:
            feature = Feature(id=feature_match.group(1), name=feature_match.group(2).strip())
            features.append(feature)
            await_why = True
            continue
        if await_why:
            why = _WHY_RE.match(line)
            if why:
                if feature is not None:
                    feature.why = why.group(1).strip()
                await_why = False
                continue
            if line.strip():
                await_why = False

        claim_match = _CLAIM_RE.match(line)
        if claim_match:
            claim = _build_claim(
                claim_id=_norm_claim_id(claim_match.group(2)),
                body=claim_match.group(4),
                checked=claim_match.group(1).lower() == "x",
                raw=line,
                line=number,
                feature=feature.id if feature else None,
                section=section_name,
            )
            claims.append(claim)
            if feature is not None:
                feature.claims.append(claim.id)
            continue

        anti_match = _ANTI_ID_RE.match(line)
        if anti_match:
            anti_counter += 1
            claims.append(
                _build_claim(
                    claim_id=anti_match.group(1),
                    body=anti_match.group(3),
                    checked=False,
                    raw=line,
                    line=number,
                    feature=feature.id if feature else None,
                    section=section_name,
                    anti=True,
                )
            )
            continue

        word_match = _ANTI_WORD_RE.match(line)
        if word_match:
            anti_counter += 1
            claims.append(
                _build_claim(
                    claim_id="A%d" % anti_counter,
                    body=word_match.group(1),
                    checked=False,
                    raw=line,
                    line=number,
                    feature=feature.id if feature else None,
                    section=section_name,
                    anti=True,
                )
            )
            continue

        if section_name and "anti" in section_name.lower():
            bare = _BARE_BULLET_RE.match(line)
            if bare:
                anti_counter += 1
                claims.append(
                    _build_claim(
                        claim_id="A%d" % anti_counter,
                        body=bare.group(1),
                        checked=False,
                        raw=line,
                        line=number,
                        feature=feature.id if feature else None,
                        section=section_name,
                        anti=True,
                    )
                )

    close_section()
    return ISA(
        path=path,
        frontmatter=frontmatter,
        title=title,
        sections=sections,
        claims=claims,
        features=features,
        text=text,
    )


def _build_claim(
    claim_id: str,
    body: str,
    checked: bool,
    raw: str,
    line: int,
    feature: str | None,
    section: str | None,
    anti: bool = False,
) -> Claim:
    text = body.strip()

    # The format fixes the order these come off the line: evidence stub, then
    # the edge, then the falsifier. Code spans are masked first so a claim can
    # quote the syntax in backticks without the quote parsing as real.
    evidence: str | None = None
    masked = _mask_code_spans(text)
    separators = list(_EVIDENCE_SEP_RE.finditer(masked))
    if separators:
        last = separators[-1]
        evidence = text[last.end():].strip() or None
        text = text[: last.start()].rstrip()

    after: list[str] = []
    after_match = _AFTER_RE.search(_mask_code_spans(text))
    if after_match:
        for token in re.split(r"[,;]+|\s{2,}", after_match.group(1)):
            token = token.strip()
            if not token:
                continue
            for ref in re.findall(r"(?:ISC[-_ ]?)?\d+(?:\.\d+)*", token):
                after.append(_norm_claim_id(ref))
        text = text[: after_match.start()].rstrip()

    statement, falsifier = _split_falsifier(text)

    dropped_match = _DROPPED_RE.search(raw)
    dropped = dropped_match is not None

    return Claim(
        id=claim_id,
        text=text,
        checked=checked,
        dropped=dropped,
        after=after,
        evidence=evidence,
        feature=feature,
        anti=anti,
        num=_major(claim_id),
        line=line,
        raw=raw,
        section=section,
        statement=statement,
        falsifier=falsifier,
        order=_order_key(claim_id),
    )


def _mask_code_spans(text: str) -> str:
    """Blank out backtick spans, preserving length so offsets still line up."""
    return _CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), text)


def _split_falsifier(text: str) -> tuple[str, str | None]:
    """Split on the first ``Falsifier:``, in exactly that spelling."""
    masked = _mask_code_spans(text)
    at = masked.find(FALSIFIER_TOKEN)
    if at < 0:
        return text.strip(), None
    statement = text[:at].strip()
    falsifier = text[at + len(FALSIFIER_TOKEN):].strip()
    return statement, falsifier or None


def _order_key(claim_id: str) -> tuple:
    """A sortable key for an id, so ``ISC-7.2`` orders after ``ISC-7.1``."""
    return tuple(int(part) for part in re.findall(r"\d+", claim_id))


def _major(claim_id: str) -> int:
    key = _order_key(claim_id)
    return key[0] if key else 0


# ---------------------------------------------------------------- check


def _test_strategy_ids(isa: ISA) -> set:
    """Claim numbers named in the Test Strategy table's first column."""
    body = isa.section("Test Strategy") or ""
    covered: set = set()
    for line in body.split("\n"):
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells:
            continue
        first = cells[0]
        if not first or set(first) <= set("-: "):
            continue
        for token in re.split(r"[,\s]+", first):
            token = token.strip()
            span = re.fullmatch(r"(?:ISC[-_ ]?)?(\d+)\s*[–—-]\s*(?:ISC[-_ ]?)?(\d+)", token)
            if span:
                for number in range(int(span.group(1)), int(span.group(2)) + 1):
                    covered.add("ISC-%d" % number)
                continue
            if re.fullmatch(r"(?:ISC[-_ ]?)?\d+(?:\.\d+)*", token):
                covered.add(_norm_claim_id(token))
    return covered


def check(isa: ISA) -> list[Finding]:
    """Every rule that makes an ISA usable. ERROR blocks, WARN informs."""
    findings: list[Finding] = []

    def error(code: str, message: str) -> None:
        findings.append(Finding("ERROR", code, message))

    def warn(code: str, message: str) -> None:
        findings.append(Finding("WARN", code, message))

    if not str(isa.frontmatter.get("phase") or "").strip():
        error("E_FRONTMATTER_PHASE", "frontmatter is missing phase")
    if not str(isa.frontmatter.get("progress") or "").strip():
        error("E_FRONTMATTER_PROGRESS", "frontmatter is missing progress")
    if isa.section("Goal") is None:
        error("E_NO_GOAL", "no ## Goal section: the outcome is not written down")

    isc = isa.isc()
    if not isc:
        error("E_NO_CLAIMS", "no ISC claims: done is not articulated")
    if not isa.anti():
        error("E_NO_ANTICLAIM", "no anti-claims: nothing states what must not happen")

    covered = _test_strategy_ids(isa)
    for claim in isc:
        if claim.dropped or claim.checked:
            continue
        if claim.falsifier:
            continue
        if claim.id in covered:
            continue
        if FALSIFIER_TOKEN.lower() in claim.text.lower():
            # The word is there in the wrong case, which the format does not
            # accept. Say so, rather than claiming no falsifier was written.
            error(
                "E_NO_FALSIFIER",
                "%s spells the falsifier in the wrong case: it must be %r"
                % (claim.id, FALSIFIER_TOKEN),
            )
            continue
        error("E_NO_FALSIFIER", "%s has no Falsifier and no Test Strategy row" % claim.id)

    seen: dict = {}
    for claim in isc:
        if claim.id in seen:
            error(
                "E_DUPLICATE_ID",
                "%s appears twice (lines %d and %d)" % (claim.id, seen[claim.id], claim.line),
            )
        else:
            seen[claim.id] = claim.line

    highest: tuple = ()
    highest_id = ""
    for claim in isc:
        if claim.order and highest and claim.order < highest:
            error(
                "E_ID_ORDER",
                "%s is out of order after %s: ids must only increase" % (claim.id, highest_id),
            )
        if claim.order and claim.order > highest:
            highest, highest_id = claim.order, claim.id

    known = {claim.id for claim in isa.claims}
    for claim in isc:
        for blocker in claim.after:
            if blocker == claim.id:
                error("E_SELF_AFTER", "%s lists itself as a prerequisite" % claim.id)
            elif blocker not in known:
                error("E_UNKNOWN_AFTER", "%s waits on %s, which does not exist" % (claim.id, blocker))
    for cycle in _cycles(isc):
        error("E_CYCLE", "prerequisite cycle: %s" % " -> ".join(cycle))

    for claim in isc:
        if claim.checked and not claim.evidence:
            warn("W_NO_EVIDENCE", "%s is checked but carries no evidence stub" % claim.id)

    counted_total = len([c for c in isc if not c.dropped])
    counted_done = len([c for c in isc if c.checked and not c.dropped])
    stated = _PROGRESS_RE.match(str(isa.frontmatter.get("progress") or ""))
    if stated:
        if (int(stated.group(1)), int(stated.group(2))) != (counted_done, counted_total):
            warn(
                "W_PROGRESS_MISMATCH",
                "frontmatter says %s/%s; the claims count %d/%d"
                % (stated.group(1), stated.group(2), counted_done, counted_total),
            )
    elif str(isa.frontmatter.get("progress") or "").strip():
        warn("W_PROGRESS_FORMAT", "progress is not in done/total form")

    return findings


def _cycles(claims: list[Claim]) -> list[list[str]]:
    edges = {claim.id: [b for b in claim.after] for claim in claims}
    found: list[list[str]] = []
    seen_cycles: set = set()
    state: dict = {}

    def walk(node: str, trail: list[str]) -> None:
        state[node] = 1
        for nxt in edges.get(node, []):
            if nxt not in edges:
                continue
            if state.get(nxt) == 1:
                cycle = trail[trail.index(nxt):] + [nxt] if nxt in trail else [nxt, node, nxt]
                key = tuple(sorted(set(cycle)))
                if key not in seen_cycles:
                    seen_cycles.add(key)
                    found.append(cycle)
            elif state.get(nxt, 0) == 0:
                walk(nxt, trail + [nxt])
        state[node] = 2

    for claim in claims:
        if state.get(claim.id, 0) == 0:
            walk(claim.id, [claim.id])
    return found


def errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.level == "ERROR"]


# ---------------------------------------------------------------- frontier / status


def frontier(isa: ISA) -> list[Claim]:
    """Claims takeable right now: open, not tombstoned, prerequisites settled."""
    settled = {c.id for c in isa.claims if c.checked or c.dropped}
    out: list[Claim] = []
    for claim in isa.isc():
        if claim.checked or claim.dropped:
            continue
        if all(blocker in settled for blocker in claim.after):
            out.append(claim)
    return out


def status(isa: ISA) -> dict:
    isc = isa.isc()
    live = [c for c in isc if not c.dropped]
    done = [c for c in live if c.checked]
    takeable = frontier(isa)
    blocked = [c for c in live if not c.checked and c not in takeable]
    return {
        "path": str(isa.path) if isa.path else None,
        "slug": isa.slug,
        "title": isa.title,
        "task": isa.frontmatter.get("task"),
        "phase": isa.phase or None,
        "progress": isa.frontmatter.get("progress"),
        "counted": "%d/%d" % (len(done), len(live)),
        "claims_total": len(isc),
        "claims_live": len(live),
        "claims_done": len(done),
        "claims_open": len(live) - len(done),
        "claims_dropped": len([c for c in isc if c.dropped]),
        "anti_claims": len(isa.anti()),
        "features": [f.id for f in isa.features],
        "frontier": [c.id for c in takeable],
        "blocked": [c.id for c in blocked],
        "complete": isa.complete,
    }


def render(isa: ISA) -> str:
    """A markdown status table plus the frontier, for a human or a hook."""
    info = status(isa)
    lines = ["# %s" % (isa.title or info["slug"]), ""]
    if info["task"]:
        lines += ["> %s" % info["task"], ""]
    lines += [
        "| field | value |",
        "|---|---|",
        "| phase | %s |" % (info["phase"] or "-"),
        "| progress | %s (counted %s) |" % (info["progress"] or "-", info["counted"]),
        "| claims | %d live, %d done, %d open, %d dropped |"
        % (info["claims_live"], info["claims_done"], info["claims_open"], info["claims_dropped"]),
        "| anti-claims | %d |" % info["anti_claims"],
        "| frontier | %s |" % (", ".join(info["frontier"]) or "none"),
        "",
    ]
    if isa.features:
        lines += ["## Features", "", "| feature | name | claims | done |", "|---|---|---|---|"]
        for feature in isa.features:
            members = [isa.by_id(cid) for cid in feature.claims]
            members = [c for c in members if c is not None]
            done = len([c for c in members if c.checked])
            lines.append(
                "| %s | %s | %d | %d |" % (feature.id, feature.name or "-", len(members), done)
            )
        lines.append("")
    takeable = frontier(isa)
    lines += ["## Frontier", ""]
    if takeable:
        for claim in takeable:
            lines.append("- %s: %s" % (claim.id, _one_line(claim.text)))
    else:
        lines.append("- nothing takeable: every open claim is blocked or the ISA is closed")
    lines.append("")
    return "\n".join(lines)


def _one_line(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- scaffold


def slugify(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9]+", "-", str(value)).strip("-").lower()
    return out or "task"


def titleize(slug: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_]+", slug) if part) or slug


def template_path(paths: Paths | None = None, name: str = "ISA.md") -> Path | None:
    resolved = paths or Paths.resolve()
    directory = resolved.templates_dir
    if directory is None:
        return None
    candidate = directory / name
    return candidate if candidate.is_file() else None


DEFAULT_TEMPLATE = """---
phase: scoping
progress: 0/1
task: "{{task}}"
slug: {{slug}}
started: {{now}}
updated: {{now}}
stated_goal: "{{stated_goal}}"
---

# {{title}}

## Goal

{{goal}}

## Features

### F1 · First feature
Why: replace this with why the feature has to exist.

- [ ] ISC-1: state one observable outcome. Falsifier: the command that would show it is false.

## Anti-claims

- A1: state one thing that must not happen.

## Log

- {{now}}: scaffolded.
"""


def scaffold(
    slug: str,
    goal: str,
    paths: Paths | None = None,
    project: bool = False,
    task: str | None = None,
    dest: Path | str | None = None,
    overwrite: bool = False,
) -> Path:
    """Write a fresh ISA and register it. Returns the path written."""
    resolved = paths or Paths.resolve()
    clean = slugify(slug)

    if dest is not None:
        target = Path(dest)
    elif project:
        if resolved.repo is None:
            raise ValueError("no git repository found for a project ISA; pass dest=")
        target = resolved.repo / "ISA.md"
    else:
        target = resolved.work / clean / "ISA.md"

    if target.exists() and not overwrite:
        raise FileExistsError(str(target))

    source = template_path(resolved)
    body = source.read_text(encoding="utf-8") if source else DEFAULT_TEMPLATE
    stamp = now_iso()
    filled = render_template(
        body,
        {
            "slug": clean,
            "goal": goal,
            "stated_goal": frontmatter_scalar(goal),
            "task": frontmatter_scalar(task or goal),
            "now": stamp,
            "title": titleize(clean),
        },
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(filled, encoding="utf-8", newline="\n")
    try:
        sync(resolved, target)
    except OSError:
        pass
    return target


def render_template(body: str, values: dict) -> str:
    out = body
    for key, value in values.items():
        out = out.replace("{{%s}}" % key, "" if value is None else str(value))
    return out


def frontmatter_scalar(value: str, limit: int = 300) -> str:
    """Flatten text so it is safe inside a double-quoted frontmatter value."""
    flat = " ".join(str(value or "").split()).replace('"', "'")
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- registry


def _load_work(paths: Paths) -> dict:
    try:
        data = json.loads(paths.work_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"isas": {}}
    if not isinstance(data, dict):
        return {"isas": {}}
    data.setdefault("isas", {})
    if not isinstance(data["isas"], dict):
        data["isas"] = {}
    return data


def sync(paths: Paths, isa_path: Path | str) -> dict:
    """Upsert this ISA's registry entry in ``MEMORY/STATE/work.json``."""
    target = Path(isa_path)
    parsed = parse(target)
    info = status(parsed)
    entry = {
        "slug": parsed.slug,
        "path": str(target),
        "task": parsed.frontmatter.get("task") or parsed.title or parsed.slug,
        "phase": parsed.phase or "unknown",
        "progress": parsed.frontmatter.get("progress") or info["counted"],
        "updated": now_iso(),
        "claims_open": info["claims_open"],
        "claims_done": info["claims_done"],
    }
    data = _load_work(paths)
    data["isas"][parsed.slug] = entry
    data["updated"] = entry["updated"]
    paths.work_json.parent.mkdir(parents=True, exist_ok=True)
    paths.work_json.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    return entry


def registry(paths: Paths) -> list[dict]:
    """Every registered ISA, newest first."""
    entries = list(_load_work(paths)["isas"].values())
    entries.sort(key=lambda item: str(item.get("updated") or ""), reverse=True)
    return entries


def find_active(paths: Paths) -> Path | None:
    """The repo ISA if it is open, else the newest open task ISA."""
    repo_isa = paths.repo_isa
    if repo_isa is not None:
        try:
            if not parse(repo_isa).complete:
                return repo_isa
        except (OSError, ValueError):
            pass

    for entry in registry(paths):
        candidate = Path(str(entry.get("path") or ""))
        if not candidate.is_file():
            continue
        if str(entry.get("phase") or "").lower() in COMPLETE_PHASES:
            continue
        try:
            if not parse(candidate).complete:
                return candidate
        except (OSError, ValueError):
            continue

    found: list[tuple[float, Path]] = []
    if paths.work.is_dir():
        for candidate in sorted(paths.work.glob("*/ISA.md")):
            try:
                if parse(candidate).complete:
                    continue
                found.append((candidate.stat().st_mtime, candidate))
            except (OSError, ValueError):
                continue
    if found:
        found.sort(reverse=True)
        return found[0][1]
    return None
