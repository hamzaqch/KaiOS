"""Schema and hygiene tests for every bundled skill.

Checks the frontmatter contract Copilot enforces (name shape, description
length, routing tokens), the ideal-state prompting rule that long numbered
choreography needs an explicit keep tag, and that every bundled script
answers --help with exit 0. Standard library only.

Set KAIOS_SKILLS_PARTIAL=1 to skip the completeness check while the skill set
is still being built in parallel.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

# The framework lives under .github, so this file is two levels below the
# checkout root: <repo>/.github/tests/<this file>.
REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".github" / "skills"

NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")
KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$")
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+\S")
KEEP_RE = re.compile(r"<!--\s*keep:")
BLOCK_SCALAR_RE = re.compile(r"^[|>][-+]?\d*$")

DESCRIPTION_LIMIT = 1024
STEP_LIMIT = 8
KEEP_LOOKBACK = 10
HELP_TIMEOUT = 20

# ISC-20. Names other builders own are included; presence is asserted once,
# at the end, with the missing ones listed.
REQUIRED_NAMES = {
    "isa",
    "algorithm",
    "cortex",
    "create-skill",
    "red-team",
    "council",
    "first-principles",
    "science",
    "iterative-depth",
    "aperture-oscillation",
    "root-cause-analysis",
    "systems-thinking",
    "bitter-pill",
    "prompting",
    "evals",
    "hardening",
    "research",
    "fabric",
    "html-report",
    "trim",
    "upgrade",
    "suggest-skills",
    "loop",
    "optimize",
    "kaios-setup",
    "databricks",
    "pr-review",
    "verify",
}


def skill_files() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict, str, int]:
    """Return (frontmatter, body, body_line_offset).

    Tolerant of quoted scalars, block scalars, and indented continuation
    lines, which is all the shapes a SKILL.md legitimately uses.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text, 0
    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            end = index
            break
    if end is None:
        return {}, text, 0

    data: dict[str, str] = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = KEY_RE.match(raw)
        if match and not raw[0].isspace():
            key = match.group(1)
            value = unquote(match.group(2))
            # a block scalar indicator is not content; the folded lines follow
            data[key] = "" if BLOCK_SCALAR_RE.match(value) else value
        elif key is not None and raw[0].isspace():
            data[key] = (data[key] + " " + raw.strip()).strip()
    return data, "\n".join(lines[end + 1:]), end + 1


def numbered_runs(body: str) -> list[dict]:
    """Find runs of numbered list items. Blank lines and indented
    continuations do not break a run; any other non-numbered line does."""
    lines = body.splitlines()
    total = len(lines)
    runs: list[dict] = []
    index = 0
    while index < total:
        if not NUMBERED_RE.match(lines[index]):
            index += 1
            continue
        start = index
        count = 0
        cursor = index
        while cursor < total:
            if NUMBERED_RE.match(lines[cursor]):
                count += 1
                cursor += 1
                continue
            if lines[cursor].strip() == "" or lines[cursor][:1].isspace():
                look = cursor
                while look < total and (
                    lines[look].strip() == "" or lines[look][:1].isspace()
                ):
                    look += 1
                if look < total and NUMBERED_RE.match(lines[look]):
                    cursor = look
                    continue
            break
        window = lines[max(0, start - KEEP_LOOKBACK):start]
        runs.append(
            {
                "start": start,
                "items": count,
                "keep_tag": any(KEEP_RE.search(line) for line in window),
            }
        )
        index = max(cursor, start + 1)
    return runs


def skill_scripts() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(
        path
        for path in SKILLS_DIR.rglob("*.py")
        if "__pycache__" not in path.parts
    )


class TestSkillFrontmatter(unittest.TestCase):
    def setUp(self) -> None:
        self.skills = skill_files()

    def test_skills_directory_has_skills(self) -> None:
        self.assertTrue(
            self.skills,
            "no SKILL.md files found under {0}".format(SKILLS_DIR),
        )

    def test_frontmatter_parses(self) -> None:
        for path in self.skills:
            with self.subTest(skill=path.parent.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(
                    text.startswith("---"),
                    "{0} does not open with a frontmatter fence".format(path),
                )
                front, _, _ = parse_frontmatter(text)
                self.assertTrue(front, "{0} has an unparseable frontmatter block".format(path))
                for key in ("name", "description"):
                    self.assertIn(key, front, "{0} is missing {1}".format(path, key))

    def test_name_shape(self) -> None:
        for path in self.skills:
            with self.subTest(skill=path.parent.name):
                front, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
                name = front.get("name", "")
                self.assertRegex(
                    name,
                    NAME_RE,
                    "{0} name {1!r} must be lowercase letters, digits and hyphens, 64 chars or fewer".format(
                        path, name
                    ),
                )

    def test_description_contract(self) -> None:
        for path in self.skills:
            with self.subTest(skill=path.parent.name):
                front, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
                description = front.get("description", "")
                self.assertLessEqual(
                    len(description),
                    DESCRIPTION_LIMIT,
                    "{0} description is {1} chars, limit is {2}".format(
                        path, len(description), DESCRIPTION_LIMIT
                    ),
                )
                self.assertIn(
                    "USE WHEN",
                    description,
                    "{0} description must contain the literal token USE WHEN".format(path),
                )
                self.assertIn(
                    "NOT FOR",
                    description,
                    "{0} description must contain the literal token NOT FOR".format(path),
                )

    def test_names_are_unique(self) -> None:
        seen: dict[str, Path] = {}
        for path in self.skills:
            front, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            name = front.get("name", "")
            if not name:
                continue
            self.assertNotIn(
                name,
                seen,
                "name {0!r} is used by both {1} and {2}".format(name, seen.get(name), path),
            )
            seen[name] = path


class TestSkillBodyStyle(unittest.TestCase):
    def test_no_long_step_choreography(self) -> None:
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                _, body, offset = parse_frontmatter(path.read_text(encoding="utf-8"))
                offenders = [
                    run
                    for run in numbered_runs(body)
                    if run["items"] > STEP_LIMIT and not run["keep_tag"]
                ]
                detail = ", ".join(
                    "line {0} ({1} items)".format(run["start"] + 1 + offset, run["items"])
                    for run in offenders
                )
                self.assertFalse(
                    offenders,
                    "{0} has numbered step choreography over {1} items without a "
                    "<!-- keep: ... --> tag above it — {2}".format(path, STEP_LIMIT, detail),
                )


class TestSkillScripts(unittest.TestCase):
    def test_every_script_answers_help(self) -> None:
        for path in skill_scripts():
            with self.subTest(script=str(path.relative_to(REPO_ROOT))):
                result = subprocess.run(
                    [sys.executable, str(path), "--help"],
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=HELP_TIMEOUT,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    "{0} --help exited {1}\nstdout: {2}\nstderr: {3}".format(
                        path, result.returncode, result.stdout[-500:], result.stderr[-500:]
                    ),
                )
                self.assertTrue(
                    result.stdout.strip(),
                    "{0} --help printed nothing".format(path),
                )


class TestSkillSetCompleteness(unittest.TestCase):
    def test_required_names_present(self) -> None:
        if os.environ.get("KAIOS_SKILLS_PARTIAL") == "1":
            self.skipTest("KAIOS_SKILLS_PARTIAL=1 — skill set still being built in parallel")
        present = set()
        for path in skill_files():
            front, _, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            if front.get("name"):
                present.add(front["name"])
        missing = sorted(REQUIRED_NAMES - present)
        self.assertFalse(
            missing,
            "{0} required skill names are missing — {1}".format(len(missing), ", ".join(missing)),
        )


if __name__ == "__main__":
    unittest.main()
