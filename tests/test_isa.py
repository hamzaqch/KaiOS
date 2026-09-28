"""ISC-29: scaffold, check, frontier, status, render, list, and the parser itself."""

import unittest

from kaios import isa as isa_mod
# Make the shared helper importable whether the runner puts this directory or
# the repository root on sys.path.
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from support import TempHomeCase, fixtures, read, write


class ParseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.good = isa_mod.parse(fixtures() / "isa-good.md")
        self.bad = isa_mod.parse(fixtures() / "isa-bad.md")

    def test_frontmatter_scalars_and_lists(self) -> None:
        front = self.good.frontmatter
        self.assertEqual(front["phase"], "climbing")
        self.assertEqual(front["progress"], "1/4")
        self.assertEqual(front["slug"], "good")
        self.assertTrue(str(front["task"]).startswith("Fixture with features"))
        self.assertEqual(front["owners"], ["core", "hooks"])

    def test_title_and_sections(self) -> None:
        self.assertEqual(self.good.title, "Good Fixture ISA")
        self.assertIsNotNone(self.good.section("Goal"))
        self.assertIsNotNone(self.good.section("Anti-claims"))
        self.assertIn("pipe tables", self.good.section("Features"))
        self.assertIsNone(self.good.section("Nonexistent"))

    def test_features_group_their_claims(self) -> None:
        self.assertEqual([f.id for f in self.good.features], ["F1", "F2"])
        first, second = self.good.features
        self.assertEqual(first.name, "Parsing")
        self.assertTrue(first.why.startswith("the parser must read"))
        self.assertEqual(first.claims, ["ISC-1", "ISC-2", "ISC-3"])
        self.assertEqual(second.claims, ["ISC-4", "ISC-5"])
        self.assertEqual(self.good.by_id("ISC-4").feature, "F2")

    def test_claim_fields(self) -> None:
        self.assertEqual([c.id for c in self.good.isc()], ["ISC-1", "ISC-2", "ISC-3", "ISC-4", "ISC-5"])
        one = self.good.by_id("ISC-1")
        self.assertTrue(one.checked)
        self.assertFalse(one.dropped)
        self.assertIn("mapping", one.evidence)
        self.assertNotIn("evidence:", one.text)
        self.assertEqual(one.num, 1)
        self.assertTrue(one.line > 0)

    def test_tombstone(self) -> None:
        three = self.good.by_id("ISC-3")
        self.assertTrue(three.dropped)
        self.assertFalse(three.checked)
        self.assertFalse(three.open)

    def test_after_edges_parse_and_leave_text_clean(self) -> None:
        four = self.good.by_id("ISC-4")
        self.assertEqual(four.after, ["ISC-2", "ISC-3"])
        self.assertNotIn("after:", four.text)
        self.assertEqual(self.good.by_id("ISC-5").after, ["ISC-3"])
        self.assertEqual(self.good.by_id("ISC-1").after, [])

    def test_anti_claims_are_not_isc(self) -> None:
        anti = self.good.anti()
        self.assertEqual([c.id for c in anti], ["A1", "A2"])
        self.assertTrue(all(c.anti for c in anti))
        self.assertEqual(len(self.good.isc()), 5)

    def test_phase_and_completion(self) -> None:
        self.assertEqual(self.good.phase, "climbing")
        self.assertFalse(self.good.complete)
        closed = isa_mod.parse_text("---\nphase: complete\nprogress: 1/1\n---\n\n# Done\n")
        self.assertTrue(closed.complete)


class CheckTests(unittest.TestCase):
    def test_good_fixture_is_clean(self) -> None:
        findings = isa_mod.check(isa_mod.parse(fixtures() / "isa-good.md"))
        self.assertEqual([f.to_dict() for f in findings], [], "clean fixture produced findings")

    def test_bad_fixture_seeds_every_error(self) -> None:
        findings = isa_mod.check(isa_mod.parse(fixtures() / "isa-bad.md"))
        codes = {f.code for f in findings}
        for expected in (
            "E_FRONTMATTER_PHASE",
            "E_NO_GOAL",
            "E_NO_FALSIFIER",
            "E_DUPLICATE_ID",
            "E_UNKNOWN_AFTER",
            "E_SELF_AFTER",
            "E_CYCLE",
            "E_ID_ORDER",
            "E_NO_ANTICLAIM",
            "W_NO_EVIDENCE",
            "W_PROGRESS_MISMATCH",
        ):
            self.assertIn(expected, codes)
        self.assertTrue(isa_mod.errors(findings))

    def test_no_claims_is_an_error(self) -> None:
        parsed = isa_mod.parse_text("---\nphase: scoping\nprogress: 0/0\n---\n\n# Empty\n\n## Goal\n\nNothing yet.\n")
        codes = {f.code for f in isa_mod.check(parsed)}
        self.assertIn("E_NO_CLAIMS", codes)
        self.assertIn("E_NO_ANTICLAIM", codes)

    def test_test_strategy_row_substitutes_for_a_falsifier(self) -> None:
        body = (
            "---\nphase: climbing\nprogress: 0/1\n---\n\n# T\n\n## Goal\n\nG.\n\n"
            "## Features\n\n### F1 · One\nWhy: because.\n\n- [ ] ISC-1: no falsifier word here.\n\n"
            "## Anti-claims\n\n- A1: nothing breaks.\n\n"
            "## Test Strategy\n\n| ISC | probe | type |\n|---|---|---|\n| 1 | a command | bash |\n"
        )
        codes = {f.code for f in isa_mod.check(isa_mod.parse_text(body))}
        self.assertNotIn("E_NO_FALSIFIER", codes)


class FrontierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.isa = isa_mod.parse(fixtures() / "isa-good.md")

    def test_frontier_respects_edges_and_tombstones(self) -> None:
        ids = [c.id for c in isa_mod.frontier(self.isa)]
        self.assertEqual(ids, ["ISC-2", "ISC-5"])

    def test_checked_and_dropped_never_appear(self) -> None:
        ids = [c.id for c in isa_mod.frontier(self.isa)]
        self.assertNotIn("ISC-1", ids)
        self.assertNotIn("ISC-3", ids)

    def test_unknown_blocker_blocks(self) -> None:
        body = (
            "---\nphase: climbing\nprogress: 0/1\n---\n\n# T\n\n## Goal\n\nG.\n\n"
            "- [ ] ISC-1: waits on a ghost. Falsifier: a probe. (after: ISC-99)\n\n"
            "## Anti-claims\n\n- A1: nothing breaks.\n"
        )
        self.assertEqual(isa_mod.frontier(isa_mod.parse_text(body)), [])

    def test_status_counts(self) -> None:
        info = isa_mod.status(self.isa)
        self.assertEqual(info["claims_total"], 5)
        self.assertEqual(info["claims_live"], 4)
        self.assertEqual(info["claims_done"], 1)
        self.assertEqual(info["claims_open"], 3)
        self.assertEqual(info["claims_dropped"], 1)
        self.assertEqual(info["anti_claims"], 2)
        self.assertEqual(info["counted"], "1/4")
        self.assertEqual(info["progress"], "1/4")
        self.assertEqual(info["frontier"], ["ISC-2", "ISC-5"])
        self.assertEqual(info["blocked"], ["ISC-4"])
        self.assertFalse(info["complete"])

    def test_render_is_markdown_with_a_table(self) -> None:
        out = isa_mod.render(self.isa)
        self.assertIn("| field | value |", out)
        self.assertIn("| phase | climbing |", out)
        self.assertIn("## Frontier", out)
        self.assertIn("ISC-5", out)
        self.assertIn("| F1 | Parsing | 3 | 1 |", out)


class ScaffoldTests(TempHomeCase):
    def test_scaffold_writes_a_checkable_isa(self) -> None:
        written = isa_mod.scaffold(
            slug="Nightly Load",
            goal="The nightly load is proven complete by a row count.",
            paths=self.paths,
        )
        self.assertTrue(written.is_file())
        self.assertEqual(written, self.paths.work / "nightly-load" / "ISA.md")

        parsed = isa_mod.parse(written)
        self.assertEqual(parsed.frontmatter["slug"], "nightly-load")
        self.assertIn("row count", parsed.section("Goal"))
        self.assertNotIn("{{", read(written))

        findings = isa_mod.check(parsed)
        self.assertEqual(
            [f.to_dict() for f in isa_mod.errors(findings)], [], "a scaffolded ISA must pass check"
        )

    def test_scaffold_registers_the_isa(self) -> None:
        isa_mod.scaffold(slug="alpha", goal="Do the thing.", paths=self.paths)
        entries = isa_mod.registry(self.paths)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["slug"], "alpha")
        self.assertEqual(entries[0]["claims_done"], 0)
        self.assertTrue(entries[0]["claims_open"] >= 1)

    def test_scaffold_refuses_to_clobber(self) -> None:
        isa_mod.scaffold(slug="alpha", goal="First.", paths=self.paths)
        with self.assertRaises(FileExistsError):
            isa_mod.scaffold(slug="alpha", goal="Second.", paths=self.paths)
        written = isa_mod.scaffold(slug="alpha", goal="Third.", paths=self.paths, overwrite=True)
        self.assertIn("Third.", read(written))

    def test_scaffold_to_an_explicit_destination(self) -> None:
        target = self.scratch / "elsewhere" / "ISA.md"
        written = isa_mod.scaffold(slug="beta", goal="Somewhere else.", paths=self.paths, dest=target)
        self.assertEqual(written, target)
        self.assertTrue(target.is_file())

    def test_project_scaffold_needs_a_repo(self) -> None:
        with self.assertRaises(ValueError):
            isa_mod.scaffold(slug="gamma", goal="No repo here.", paths=self.paths, project=True)


class ActiveIsaTests(TempHomeCase):
    def test_none_when_nothing_is_open(self) -> None:
        self.assertIsNone(isa_mod.find_active(self.paths))

    def test_repo_isa_wins_when_open(self) -> None:
        repo = self.fake_repo()
        write(repo / "ISA.md", read(fixtures() / "isa-good.md"))
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        isa_mod.scaffold(slug="task", goal="A task ISA.", paths=paths)
        self.assertEqual(isa_mod.find_active(paths), repo / "ISA.md")

    def test_completed_repo_isa_is_skipped(self) -> None:
        repo = self.fake_repo()
        write(repo / "ISA.md", "---\nphase: complete\nprogress: 1/1\n---\n\n# Shipped\n")
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        task = isa_mod.scaffold(slug="task", goal="A task ISA.", paths=paths)
        self.assertEqual(isa_mod.find_active(paths), task)

    def test_registry_survives_a_resync(self) -> None:
        written = isa_mod.scaffold(slug="delta", goal="Sync me.", paths=self.paths)
        entry = isa_mod.sync(self.paths, written)
        self.assertEqual(entry["slug"], "delta")
        self.assertEqual(len(isa_mod.registry(self.paths)), 1)


class SlugTests(unittest.TestCase):
    def test_slugify(self) -> None:
        self.assertEqual(isa_mod.slugify("Nightly Load v2"), "nightly-load-v2")
        self.assertEqual(isa_mod.slugify("  ***  "), "task")

    def test_titleize(self) -> None:
        self.assertEqual(isa_mod.titleize("nightly-load"), "Nightly Load")


if __name__ == "__main__":
    unittest.main()
