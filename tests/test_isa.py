"""ISC-29: scaffold, check, frontier, status, render, list, and the parser itself."""

import unittest

from kaios import isa as isa_mod
from tests.support import TempHomeCase, fixtures, read, write


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

    def test_every_dash_style_introduces_an_evidence_stub(self) -> None:
        for dash in ("—", "–", "--", "-"):
            body = (
                "---\nphase: climbing\nprogress: 1/1\n---\n\n# T\n\n## Goal\n\nG.\n\n"
                "- [x] ISC-1: done. Falsifier: a probe. %s evidence: the probe printed OK\n\n"
                "## Anti-claims\n\n- A1: nothing breaks.\n"
            ) % dash
            claim = isa_mod.parse_text(body).by_id("ISC-1")
            self.assertEqual(claim.evidence, "the probe printed OK", "dash %r failed" % dash)
            self.assertNotIn("evidence", claim.text.lower())

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


class EdgeParseOrderTests(unittest.TestCase):
    """The four-step strip order, and the ways an edge used to vanish silently.

    A lost edge is the worst kind of parse bug: it blinds E_UNKNOWN_AFTER,
    E_SELF_AFTER, cycle detection and the frontier at once, with no error shown.
    """

    def _one(self, line: str) -> isa_mod.Claim:
        return isa_mod.parse_text(self._isa(line)).isc()[0]

    def _isa(self, *lines: str) -> str:
        return (
            "---\nphase: climbing\nprogress: 0/1\n---\n\n# T\n\n## Goal\n\nG.\n\n"
            + "\n".join(lines)
            + "\n\n## Anti-claims\n\n- A1: nothing breaks.\n"
        )

    def test_an_edge_before_an_evidence_stub_survives(self) -> None:
        claim = self._one(
            "- [x] ISC-1: Step one holds. Falsifier: it does not. (after: ISC-99) — evidence: abc123"
        )
        self.assertEqual(claim.after, ["ISC-99"])
        self.assertEqual(claim.evidence, "abc123")
        self.assertEqual(claim.statement, "Step one holds.")
        self.assertEqual(claim.falsifier, "it does not.")

    def test_that_lost_edge_is_reported_by_check(self) -> None:
        body = self._isa(
            "- [x] ISC-1: Step one holds. Falsifier: it does not. (after: ISC-99) — evidence: abc123"
        )
        self.assertIn("E_UNKNOWN_AFTER", {f.code for f in isa_mod.check(isa_mod.parse_text(body))})

    def test_a_trailing_period_after_the_edge_is_allowed(self) -> None:
        self.assertEqual(self._one("- [ ] ISC-2: Two. Falsifier: no. (after: ISC-1).").after, ["ISC-1"])

    def test_a_trailing_period_and_an_evidence_stub_together(self) -> None:
        claim = self._one("- [x] ISC-4: Four. Falsifier: no. (after: ISC-2). — evidence: ok")
        self.assertEqual(claim.after, ["ISC-2"])
        self.assertEqual(claim.evidence, "ok")

    def test_a_backticked_edge_is_never_a_real_edge(self) -> None:
        claim = self._one("- [ ] ISC-3: Falsifier: no. Declare it as `(after: ISC-9)`")
        self.assertEqual(claim.after, [], "a quoted example must not become an edge")

    def test_a_backticked_example_does_not_hide_a_real_edge(self) -> None:
        claim = self._one("- [ ] ISC-5: Write `(after: ISC-9)` here. Falsifier: no. (after: ISC-1)")
        self.assertEqual(claim.after, ["ISC-1"])

    def test_a_backticked_evidence_stub_is_never_a_real_stub(self) -> None:
        self.assertIsNone(self._one("- [ ] ISC-8: Close with `— evidence: s`. Falsifier: no.").evidence)

    def test_the_last_evidence_stub_wins(self) -> None:
        claim = self._one("- [x] ISC-6: Six. Falsifier: no. — evidence: first — evidence: second")
        self.assertEqual(claim.evidence, "second")

    def test_a_nested_id_keeps_its_id_and_its_text(self) -> None:
        claim = self._one("- [ ] ISC-7.1: A leaf claim. Falsifier: no. (after: ISC-7)")
        self.assertEqual(claim.id, "ISC-7.1")
        self.assertEqual(claim.statement, "A leaf claim.")
        self.assertEqual(claim.after, ["ISC-7"])
        self.assertEqual(claim.num, 7)
        self.assertEqual(claim.order, (7, 1))

    def test_nested_ids_order_by_segment(self) -> None:
        parsed = isa_mod.parse_text(
            self._isa(
                "- [ ] ISC-7: Parent. Falsifier: no.",
                "- [ ] ISC-7.1: First leaf. Falsifier: no.",
                "- [ ] ISC-7.2: Second leaf. Falsifier: no.",
                "- [ ] ISC-8: Next. Falsifier: no.",
            )
        )
        self.assertEqual([c.id for c in parsed.isc()], ["ISC-7", "ISC-7.1", "ISC-7.2", "ISC-8"])
        self.assertNotIn("E_ID_ORDER", {f.code for f in isa_mod.check(parsed)})

    def test_a_backwards_nested_id_is_still_caught(self) -> None:
        body = self._isa(
            "- [ ] ISC-7.2: Second leaf. Falsifier: no.",
            "- [ ] ISC-7.1: First leaf. Falsifier: no.",
        )
        self.assertIn("E_ID_ORDER", {f.code for f in isa_mod.check(isa_mod.parse_text(body))})

    def test_a_test_strategy_row_can_name_a_nested_id(self) -> None:
        body = (
            "---\nphase: climbing\nprogress: 0/1\n---\n\n# T\n\n## Goal\n\nG.\n\n"
            "- [ ] ISC-7.1: A leaf with no falsifier word.\n\n"
            "## Anti-claims\n\n- A1: nothing breaks.\n\n"
            "## Test Strategy\n\n| ISC | probe | type |\n|---|---|---|\n| 7.1 | a command | bash |\n"
        )
        self.assertNotIn("E_NO_FALSIFIER", {f.code for f in isa_mod.check(isa_mod.parse_text(body))})

    def test_the_falsifier_spelling_is_case_sensitive(self) -> None:
        self.assertIsNone(self._one("- [ ] ISC-8: Eight. falsifier: no.").falsifier)

    def test_a_wrong_case_falsifier_says_so(self) -> None:
        body = self._isa("- [ ] ISC-1: Eight. falsifier: no.")
        findings = [f for f in isa_mod.check(isa_mod.parse_text(body)) if f.code == "E_NO_FALSIFIER"]
        self.assertEqual(len(findings), 1)
        self.assertIn("wrong case", findings[0].message)


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

    def test_scaffold_records_the_stated_goal_in_frontmatter(self) -> None:
        written = isa_mod.scaffold(
            slug="quoted",
            goal='The load is "complete"\nwhen the row count matches.',
            paths=self.paths,
        )
        parsed = isa_mod.parse(written)
        stated = str(parsed.frontmatter.get("stated_goal") or "")
        self.assertIn("row count matches", stated)
        self.assertNotIn('"', stated, "a double quote would break the frontmatter value")
        self.assertNotIn("\n", stated)
        self.assertEqual([f.to_dict() for f in isa_mod.errors(isa_mod.check(parsed))], [])

    def test_scaffold_uses_the_documented_section_order(self) -> None:
        written = isa_mod.scaffold(slug="ordered", goal="Prove the order holds.", paths=self.paths)
        self.assertEqual(
            list(isa_mod.parse(written).sections.keys()),
            [
                "Problem",
                "Vision",
                "Out of Scope",
                "Language",
                "Principles",
                "Constraints",
                "Dependencies",
                "Goal",
                "Features",
                "Not yet specified",
                "Anti-claims",
                "Test Strategy",
                "Decisions",
                "Log",
                "Remaining Work",
            ],
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


class EdgeAndEvidenceOrderTests(unittest.TestCase):
    """Regression: an evidence stub after the (after:) edge must not hide the edge."""

    def test_edge_survives_trailing_evidence_stub(self) -> None:
        text = (
            "---\nphase: climbing\nprogress: 1/1\n---\n# T\n\n## Goal\n\ng\n\n## Claims\n\n"
            "- [x] ISC-1: Step one holds. Falsifier: it does not. (after: ISC-99) — evidence: abc123\n\n"
            "## Anti-claims\n\n- A1: none\n"
        )
        parsed = isa_mod.parse_text(text)
        claim = parsed.claims[0]
        self.assertEqual(claim.after, ["ISC-99"])
        self.assertEqual(claim.evidence, "abc123")
        codes = [f.code for f in isa_mod.check(parsed)]
        self.assertIn("E_UNKNOWN_AFTER", codes)

