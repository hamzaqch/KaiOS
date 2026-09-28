#!/usr/bin/env python3
"""Tally recurring themes in memory captures and rank candidate skills.

Reads capture JSONL files and the work registry under the memory tree, counts
recurring kinds and keywords, marks anything an existing skill already covers,
and prints ranked candidates. Proposal only — it writes nothing. Standard
library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from pathlib import Path

WORD = re.compile(r"[a-z][a-z0-9+#._-]{3,}")
FRICTION = (
    "again",
    "still",
    "keeps",
    "repeat",
    "third time",
    "second time",
    "same problem",
    "stuck",
    "wasted",
    "manual",
    "by hand",
    "every time",
    "tedious",
    "forgot",
    "regressed",
)
STOPWORDS = {
    "that", "this", "with", "from", "have", "were", "will", "would", "could",
    "should", "been", "when", "then", "than", "them", "they", "your", "just",
    "about", "there", "their", "what", "which", "into", "some", "more", "most",
    "only", "also", "other", "after", "before", "because", "while", "where",
    "here", "over", "under", "much", "many", "make", "made", "does", "done",
    "need", "needs", "want", "like", "took", "take", "very", "well", "back",
    "even", "same", "such", "each", "both", "being", "does", "said", "says",
    "work", "working", "thing", "things", "stuff", "note", "notes", "kind",
    "text", "time", "times", "using", "used", "than", "were", "into",
}


FRICTION_WORDS = {w for marker in FRICTION for w in marker.split()}


def default_home() -> Path:
    env = os.environ.get("KAIOS_HOME")
    if env:
        return Path(env)
    return Path.home() / ".kaios"


def read_jsonl(path: Path) -> list[dict]:
    records: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return records
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            records.append(parsed)
    return records


def collect_captures(memory: Path) -> tuple[list[dict], list[str]]:
    records: list[dict] = []
    sources: list[str] = []
    if not memory.is_dir():
        return records, sources
    for path in sorted(memory.rglob("*.jsonl")):
        if "observability" in str(path).lower():
            continue
        found = read_jsonl(path)
        if found:
            records.extend(found)
            sources.append(str(path))
    return records, sources


def collect_work(memory: Path) -> tuple[list[dict], list[str]]:
    entries: list[dict] = []
    sources: list[str] = []
    candidate = memory / "STATE" / "work.json"
    if not candidate.is_file():
        return entries, sources
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return entries, sources
    sources.append(str(candidate))
    if isinstance(data, dict):
        raw = data.get("tasks") or data.get("work") or list(data.values())
    else:
        raw = data
    if isinstance(raw, list):
        entries = [item for item in raw if isinstance(item, dict)]
    return entries, sources


def text_of(record: dict) -> str:
    parts = []
    for key in ("text", "title", "goal", "task", "summary", "slug", "note"):
        value = record.get(key)
        if isinstance(value, str):
            parts.append(value)
    tags = record.get("tags")
    if isinstance(tags, list):
        parts.extend(str(t) for t in tags)
    return " ".join(parts)


def friction_score(blob: str, record: dict) -> int:
    score = sum(1 for marker in FRICTION if marker in blob)
    rating = record.get("rating")
    if isinstance(rating, (int, float)) and rating <= 2:
        score += 2
    if record.get("kind") in {"incident", "frustration", "rework"}:
        score += 2
    return score


def existing_skill_names(skills_dir: Path) -> set[str]:
    names: set[str] = set()
    if not skills_dir.is_dir():
        return names
    for skill in sorted(skills_dir.glob("*/SKILL.md")):
        names.add(skill.parent.name.lower())
        for line in skill.read_text(encoding="utf-8", errors="replace").splitlines()[:30]:
            if line.startswith("name:"):
                names.add(line.split(":", 1)[1].strip().strip("'\"").lower())
                break
    return names


def covered_by(term: str, names: set[str]) -> str | None:
    flat = term.replace(" ", "-")
    for name in names:
        if flat in name or name in flat or flat.replace("-", "") == name.replace("-", ""):
            return name
    return None


def rank(records: list[dict], work: list[dict], names: set[str], min_count: int) -> list[dict]:
    keyword_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    friction: Counter[str] = Counter()
    samples: dict[str, str] = {}

    for record in records + work:
        blob = text_of(record).lower()
        kind = str(record.get("kind") or record.get("type") or "").strip().lower()
        if kind:
            kind_counts[kind] += 1
        pain = friction_score(blob, record)
        seen = set()
        for word in WORD.findall(blob):
            if word in STOPWORDS or word in FRICTION_WORDS or word in seen:
                continue
            seen.add(word)
            keyword_counts[word] += 1
            friction[word] += pain
            samples.setdefault(word, blob[:160])

    candidates = []
    for term, count in keyword_counts.items():
        if count < min_count:
            continue
        pain = friction[term]
        cover = covered_by(term, names)
        score = count * 2 + pain * 3 - (count if cover else 0)
        candidates.append(
            {
                "term": term,
                "occurrences": count,
                "friction": pain,
                "score": score,
                "covered_by": cover,
                "sample": samples.get(term, ""),
            }
        )
    candidates.sort(key=lambda c: (-c["score"], -c["occurrences"], c["term"]))
    for candidate in candidates:
        candidate["kinds"] = [k for k, _ in kind_counts.most_common(5)]
    return candidates


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="suggest_skills.py",
        description="Rank candidate skills from recurring themes in memory captures.",
    )
    parser.add_argument("--home", default=None, help="memory root (defaults to the configured home)")
    parser.add_argument("--skills-dir", default=".github/skills", help="existing skills directory")
    parser.add_argument("--top", type=int, default=10, help="how many candidates to print")
    parser.add_argument("--min-count", type=int, default=3, help="minimum occurrences to qualify")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args(argv)

    home = Path(args.home) if args.home else default_home()
    memory = home / "MEMORY" if (home / "MEMORY").is_dir() else home
    records, capture_sources = collect_captures(memory)
    work, work_sources = collect_work(memory)
    names = existing_skill_names(Path(args.skills_dir))
    candidates = rank(records, work, names, args.min_count)
    top = candidates[: max(0, args.top)]

    report = {
        "memory": str(memory),
        "sources": capture_sources + work_sources,
        "captures": len(records),
        "work_items": len(work),
        "existing_skills": len(names),
        "candidates": top,
        "note": "" if records or work else "no captures found — nothing to propose yet",
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    print("memory: {0}".format(report["memory"]))
    print("captures: {0}   work items: {1}   existing skills: {2}".format(
        report["captures"], report["work_items"], report["existing_skills"]))
    if report["note"]:
        print(report["note"])
        return 0
    if not top:
        print("nothing recurred at least {0} times — raise --min-count or capture more".format(args.min_count))
        return 0
    print("")
    print("{0:<22} {1:>5} {2:>8} {3:>6}  {4}".format("term", "count", "friction", "score", "covered by"))
    print("-" * 72)
    for candidate in top:
        print("{0:<22} {1:>5} {2:>8} {3:>6}  {4}".format(
            candidate["term"][:22],
            candidate["occurrences"],
            candidate["friction"],
            candidate["score"],
            candidate["covered_by"] or "-",
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
