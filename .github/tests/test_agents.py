"""Schema tests for the Copilot custom agents under .github/agents.

Every agent file is a Markdown document with YAML frontmatter followed by a
role marker comment. The marker is what `python -m kaios models apply` reads
when it rewrites each agent's ``model:`` list from the registry, so a missing
or misspelled marker silently drops that agent out of model routing.

These tests use a deliberately small frontmatter reader rather than a YAML
parser, because the whole package is standard library only.
"""

import re
import unittest
from pathlib import Path

# The framework lives under .github, so this file is two levels below the
# checkout root: <repo>/.github/tests/<this file>.
REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO_ROOT / ".github" / "agents"

VALID_ROLES = frozenset({"max", "high", "medium", "cross", "third", "research"})

ROLE_MARKER = re.compile(r"^<!--\s*kaios-role:\s*([a-z]+)\s*-->$")
KEY_LINE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*):(?P<rest>.*)$")

# Agents whose whole purpose is to look without touching. A write tool on any
# of these breaks the separation the system depends on.
READ_ONLY_AGENTS = ("Planner", "Reviewer", "Auditor", "ThirdOpinion", "Researcher")

KAI_SUBAGENTS = ("Planner", "Builder", "Reviewer", "Auditor", "Researcher", "Verifier")

MINIMUM_AGENT_COUNT = 9


def _strip_quotes(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def _split_flow_sequence(text):
    """Split the inside of a ``[a, b]`` flow sequence, honouring quotes."""
    items = []
    current = []
    quote = None
    for char in text:
        if quote:
            if char == quote:
                quote = None
            else:
                current.append(char)
            continue
        if char in ("'", '"'):
            quote = char
            continue
        if char == ",":
            items.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    tail = "".join(current).strip()
    if tail:
        items.append(tail)
    return [item for item in items if item]


def _parse_value(raw):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return _split_flow_sequence(raw[1:-1])
    return _strip_quotes(raw)


def parse_agent(path):
    """Return (frontmatter dict, body lines) for one agent file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise AssertionError("%s does not open with a YAML frontmatter fence" % path.name)
    try:
        end = lines.index("---", 1)
    except ValueError:
        raise AssertionError("%s has no closing frontmatter fence" % path.name)

    front = {}
    index = 1
    while index < end:
        line = lines[index]
        if not line.strip() or line.startswith("#"):
            index += 1
            continue
        match = KEY_LINE.match(line)
        if not match or line[:1].isspace():
            index += 1
            continue
        key = match.group("key")
        rest = match.group("rest").strip()
        if rest:
            front[key] = _parse_value(rest)
            index += 1
            continue
        # Block form: gather the indented lines that belong to this key.
        block = []
        index += 1
        while index < end and (not lines[index].strip() or lines[index][:1].isspace()):
            block.append(lines[index])
            index += 1
        simple = []
        for entry in block:
            stripped = entry.strip()
            if stripped.startswith("- ") and ":" not in stripped:
                simple.append(_strip_quotes(stripped[2:]))
            elif stripped:
                simple = None
                break
        front[key] = simple if simple else block
    return front, lines[end + 1 :]


def agent_files():
    return sorted(AGENT_DIR.glob("*.agent.md"))


class AgentDirectoryTests(unittest.TestCase):
    def test_agent_directory_exists(self):
        self.assertTrue(AGENT_DIR.is_dir(), "missing %s" % AGENT_DIR)

    def test_minimum_agent_count(self):
        found = agent_files()
        self.assertGreaterEqual(
            len(found),
            MINIMUM_AGENT_COUNT,
            "expected at least %d agents, found %d" % (MINIMUM_AGENT_COUNT, len(found)),
        )


class AgentSchemaTests(unittest.TestCase):
    def setUp(self):
        self.files = agent_files()
        self.assertTrue(self.files, "no agent files found under %s" % AGENT_DIR)

    def test_required_frontmatter_keys(self):
        for path in self.files:
            with self.subTest(agent=path.name):
                front, _ = parse_agent(path)
                for key in ("name", "description", "tools", "model"):
                    self.assertIn(key, front, "%s is missing %r" % (path.name, key))
                self.assertTrue(str(front["name"]).strip(), "%s has an empty name" % path.name)
                self.assertTrue(
                    str(front["description"]).strip(),
                    "%s has an empty description" % path.name,
                )

    def test_name_matches_filename(self):
        for path in self.files:
            with self.subTest(agent=path.name):
                front, _ = parse_agent(path)
                expected = path.name[: -len(".agent.md")]
                self.assertEqual(
                    front["name"],
                    expected,
                    "%s declares name %r" % (path.name, front["name"]),
                )

    def test_tools_is_a_list(self):
        for path in self.files:
            with self.subTest(agent=path.name):
                front, _ = parse_agent(path)
                tools = front["tools"]
                self.assertIsInstance(tools, list, "%s tools is not a list" % path.name)
                self.assertTrue(tools, "%s lists no tools" % path.name)
                for tool in tools:
                    self.assertTrue(
                        isinstance(tool, str) and tool.strip(),
                        "%s has a blank tool entry" % path.name,
                    )

    def test_model_is_list_or_string(self):
        for path in self.files:
            with self.subTest(agent=path.name):
                front, _ = parse_agent(path)
                model = front["model"]
                self.assertIsInstance(
                    model, (list, str), "%s model is neither a list nor a string" % path.name
                )
                if isinstance(model, list):
                    self.assertTrue(model, "%s has an empty model list" % path.name)
                    for entry in model:
                        self.assertTrue(
                            isinstance(entry, str) and entry.strip(),
                            "%s has a blank model entry" % path.name,
                        )
                else:
                    self.assertTrue(model.strip(), "%s has an empty model string" % path.name)

    def test_role_marker_follows_frontmatter(self):
        for path in self.files:
            with self.subTest(agent=path.name):
                _, body = parse_agent(path)
                first = None
                for line in body:
                    if line.strip():
                        first = line.strip()
                        break
                self.assertIsNotNone(first, "%s has an empty body" % path.name)
                match = ROLE_MARKER.match(first)
                self.assertIsNotNone(
                    match,
                    "%s first body line is %r, expected a kaios-role marker comment"
                    % (path.name, first),
                )
                role = match.group(1)
                self.assertIn(
                    role,
                    VALID_ROLES,
                    "%s declares unknown role %r" % (path.name, role),
                )


class AgentRoutingTests(unittest.TestCase):
    def _front(self, name):
        path = AGENT_DIR / ("%s.agent.md" % name)
        self.assertTrue(path.is_file(), "missing agent file %s" % path.name)
        front, _ = parse_agent(path)
        return front

    def test_kai_can_dispatch_subagents(self):
        front = self._front("Kai")
        self.assertIn("agents", front, "Kai declares no agents list")
        listed = front["agents"]
        self.assertIsInstance(listed, list, "Kai agents is not a list")
        for name in KAI_SUBAGENTS:
            self.assertIn(name, listed, "Kai cannot dispatch %s" % name)
        self.assertIn("agent", front["tools"], "Kai lacks the agent tool")

    def test_read_only_agents_cannot_edit(self):
        for name in READ_ONLY_AGENTS:
            with self.subTest(agent=name):
                front = self._front(name)
                self.assertNotIn(
                    "edit",
                    front["tools"],
                    "%s is a read-only seat but lists the edit tool" % name,
                )

    def test_every_dispatchable_subagent_exists(self):
        front = self._front("Kai")
        for name in front["agents"]:
            with self.subTest(agent=name):
                path = AGENT_DIR / ("%s.agent.md" % name)
                self.assertTrue(path.is_file(), "Kai dispatches missing agent %s" % name)


if __name__ == "__main__":
    unittest.main()
