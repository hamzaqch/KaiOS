"""ISC-23: the role registry, and rewriting agent frontmatter from it."""

import json
import unittest

from kaios import models as models_mod
from tests.support import TempHomeCase, read, repo_root, write

AGENT = """---
name: Planner
description: Turns a request into claims.
tools: ['search/codebase', 'edit']
model: ['Placeholder One', 'Placeholder Two']
agents: ['Builder']
---

# kaios-role: max

The body of this agent must survive a model rewrite byte for byte.

- a bullet
- another bullet with a model: colon in it
"""

AGENT_HTML_COMMENT = """---
name: Auditor
description: Reads without writing.
tools: ['search/codebase']
model: Placeholder
---

<!-- kaios-role: cross -->

Audit only.
"""

AGENT_NO_ROLE = """---
name: Stray
description: Has no role line.
tools: []
model: Something
---

Nothing to see here.
"""

AGENT_LIST_FORM = """---
name: Builder
description: Executes scoped work.
tools: []
model:
  - Placeholder One
  - Placeholder Two
after: keep me
---

# kaios-role: high

Body stays.
"""


class RegistryTests(TempHomeCase):
    def test_repo_default_loads(self) -> None:
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        data = models_mod.load(paths)
        self.assertEqual(
            sorted(data["roles"]), ["cross", "high", "max", "medium", "research", "third"]
        )
        self.assertTrue(data["roles"]["max"]["models"])
        self.assertIn("anthropic", data["families"])

    def test_show_annotates_families(self) -> None:
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        report = models_mod.show(paths)
        families = report["roles"]["max"]["families"]
        self.assertTrue(any(f is not None for f in families))

    def test_family_of_matches_by_prefix(self) -> None:
        data = {"families": {"anthropic": ["Claude"], "openai": ["GPT", "o3"], "google": ["Gemini"]}}
        self.assertEqual(models_mod.family_of("Claude Opus 4.5", data), "anthropic")
        self.assertEqual(models_mod.family_of("GPT-5.2", data), "openai")
        self.assertEqual(models_mod.family_of("Gemini 2.5 Pro", data), "google")
        self.assertIsNone(models_mod.family_of("Some Other Model", data))
        self.assertIsNone(models_mod.family_of("", data))

    def test_set_writes_the_user_registry_and_wins(self) -> None:
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        result = models_mod.set_role("max", "Model A, Model B", paths=paths)
        self.assertEqual(result["models"], ["Model A", "Model B"])
        self.assertTrue(paths.models_file.is_file())
        self.assertEqual(models_mod.models_for("max", paths=paths), ["Model A", "Model B"])
        self.assertEqual(models_mod.load(paths)["source"], str(paths.models_file))

    def test_set_accepts_a_list(self) -> None:
        models_mod.set_role("high", ["Only One"], paths=self.paths)
        self.assertEqual(models_mod.models_for("high", paths=self.paths), ["Only One"])

    def test_set_keeps_other_roles(self) -> None:
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        before = models_mod.models_for("high", paths=paths)
        models_mod.set_role("max", "Model A", paths=paths)
        self.assertEqual(models_mod.models_for("high", paths=paths), before)

    def test_set_refuses_empty_input(self) -> None:
        with self.assertRaises(ValueError):
            models_mod.set_role("max", "", paths=self.paths)
        with self.assertRaises(ValueError):
            models_mod.set_role("", "Model A", paths=self.paths)

    def test_the_cli_alias_is_the_same_function(self) -> None:
        self.assertIs(models_mod.set, models_mod.set_role)

    def test_unparseable_registry_raises(self) -> None:
        write(self.paths.models_file, "{not json")
        with self.assertRaises(ValueError):
            models_mod.load(self.paths)


class FormatTests(unittest.TestCase):
    def test_model_line_uses_single_quotes(self) -> None:
        self.assertEqual(models_mod.format_model_line(["A", "B"]), "model: ['A', 'B']")
        self.assertEqual(models_mod.format_model_line(["Only"]), "model: ['Only']")

    def test_role_is_read_from_either_comment_style(self) -> None:
        self.assertEqual(models_mod.role_of("# kaios-role: max\n"), "max")
        self.assertEqual(models_mod.role_of("<!-- kaios-role: cross -->\n"), "cross")
        self.assertEqual(models_mod.role_of("kaios-role:   Research\n"), "research")
        self.assertIsNone(models_mod.role_of("nothing here"))

    def test_rewrite_needs_frontmatter(self) -> None:
        with self.assertRaises(ValueError):
            models_mod.rewrite_model("no frontmatter here", ["A"])
        with self.assertRaises(ValueError):
            models_mod.rewrite_model("---\nname: x\nunclosed\n", ["A"])


class ApplyTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.agents = self.scratch / "agents"
        self.agents.mkdir(parents=True, exist_ok=True)
        write(
            self.paths.models_file,
            json.dumps(
                {
                    "roles": {
                        "max": {"purpose": "judgment", "models": ["Model A", "Model B"]},
                        "high": {"purpose": "execution", "models": ["Model C"]},
                        "cross": {"purpose": "second look", "models": ["Model D"]},
                        "empty": {"purpose": "nothing", "models": []},
                    },
                    "families": {"alpha": ["Model"]},
                },
                indent=2,
            )
            + "\n",
        )

    def test_apply_rewrites_the_model_list(self) -> None:
        target = write(self.agents / "Planner.agent.md", AGENT)
        result = models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual([c["file"] for c in result["changed"]], ["Planner.agent.md"])
        self.assertEqual(result["changed"][0]["role"], "max")
        self.assertIn("model: ['Model A', 'Model B']", read(target))
        self.assertNotIn("Placeholder One", read(target))

    def test_apply_preserves_the_body_byte_for_byte(self) -> None:
        target = write(self.agents / "Planner.agent.md", AGENT)
        before = read(target).split("---", 2)[2]
        models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual(read(target).split("---", 2)[2], before)

    def test_apply_preserves_every_other_frontmatter_key(self) -> None:
        target = write(self.agents / "Planner.agent.md", AGENT)
        models_mod.apply(self.agents, paths=self.paths)
        body = read(target)
        for line in ("name: Planner", "tools: ['search/codebase', 'edit']", "agents: ['Builder']"):
            self.assertIn(line, body)

    def test_apply_handles_an_html_comment_role(self) -> None:
        target = write(self.agents / "Auditor.agent.md", AGENT_HTML_COMMENT)
        result = models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual(result["changed"][0]["role"], "cross")
        self.assertIn("model: ['Model D']", read(target))

    def test_apply_collapses_a_multi_line_model_list(self) -> None:
        target = write(self.agents / "Builder.agent.md", AGENT_LIST_FORM)
        models_mod.apply(self.agents, paths=self.paths)
        body = read(target)
        self.assertIn("model: ['Model C']", body)
        self.assertNotIn("- Placeholder One", body)
        self.assertIn("after: keep me", body)

    def test_apply_skips_a_file_with_no_role(self) -> None:
        write(self.agents / "Stray.agent.md", AGENT_NO_ROLE)
        result = models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual([s["file"] for s in result["skipped"]], ["Stray.agent.md"])
        self.assertEqual(result["changed"], [])

    def test_apply_reports_a_role_with_no_models(self) -> None:
        write(self.agents / "Odd.agent.md", AGENT.replace("kaios-role: max", "kaios-role: empty"))
        result = models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual([e["file"] for e in result["errors"]], ["Odd.agent.md"])

    def test_apply_is_idempotent(self) -> None:
        write(self.agents / "Planner.agent.md", AGENT)
        models_mod.apply(self.agents, paths=self.paths)
        again = models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual(again["changed"], [])
        self.assertEqual([u["file"] for u in again["unchanged"]], ["Planner.agent.md"])

    def test_dry_run_changes_nothing_on_disk(self) -> None:
        target = write(self.agents / "Planner.agent.md", AGENT)
        before = read(target)
        result = models_mod.apply(self.agents, paths=self.paths, dry_run=True)
        self.assertEqual([c["file"] for c in result["changed"]], ["Planner.agent.md"])
        self.assertEqual(read(target), before)

    def test_crlf_endings_survive(self) -> None:
        target = write(self.agents / "Planner.agent.md", AGENT.replace("\n", "\r\n"), newline="")
        before = target.read_bytes()
        models_mod.apply(self.agents, paths=self.paths)
        raw = target.read_bytes()
        self.assertIn(b"model: ['Model A', 'Model B']\r\n", raw)
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"), "a bare LF was introduced")
        self.assertEqual(
            raw.split(b"---", 2)[2], before.split(b"---", 2)[2], "the body bytes changed"
        )

    def test_missing_agents_directory_is_reported_not_raised(self) -> None:
        result = models_mod.apply(self.scratch / "nope", paths=self.paths)
        self.assertEqual(result["changed"], [])
        self.assertTrue(result["skipped"])

    def test_an_empty_agents_directory_is_fine(self) -> None:
        result = models_mod.apply(self.agents, paths=self.paths)
        self.assertEqual(result["changed"], [])
        self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
