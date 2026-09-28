"""ISC-30: captures, search, digest, health, hot layer, and the knowledge archive."""

import json
import unittest

from kaios import isa as isa_mod
from kaios import memory as memory_mod
# Make the shared helper importable whether the runner puts this directory or
# the repository root on sys.path.
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from support import TempHomeCase, read


class CaptureTests(TempHomeCase):
    def test_capture_appends_one_json_line(self) -> None:
        memory_mod.capture(self.paths, "learning", "The wrapper swallows stderr.")
        memory_mod.capture(self.paths, "gotcha", "Timeouts are per event, not per hook.", {"event": "Stop"})

        lines = [line for line in read(self.paths.captures).split("\n") if line.strip()]
        self.assertEqual(len(lines), 2)
        second = json.loads(lines[1])
        self.assertEqual(second["kind"], "gotcha")
        self.assertEqual(second["meta"]["event"], "Stop")
        self.assertTrue(second["ts"].endswith("Z"))

    def test_every_documented_kind_is_accepted(self) -> None:
        for kind in memory_mod.KINDS:
            memory_mod.capture(self.paths, kind, "A %s." % kind)
        self.assertEqual(len(memory_mod.captures(self.paths)), len(memory_mod.KINDS))

    def test_unknown_kind_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            memory_mod.capture(self.paths, "vibes", "not a kind")

    def test_empty_text_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            memory_mod.capture(self.paths, "fact", "   ")

    def test_captures_can_be_filtered_and_limited(self) -> None:
        for index in range(5):
            memory_mod.capture(self.paths, "fact", "fact %d" % index)
        memory_mod.capture(self.paths, "decision", "one decision")
        self.assertEqual(len(memory_mod.captures(self.paths, kind="decision")), 1)
        self.assertEqual(len(memory_mod.captures(self.paths, limit=2)), 2)


class SearchTests(TempHomeCase):
    def test_finds_a_capture_by_substring_case_insensitively(self) -> None:
        memory_mod.capture(self.paths, "gotcha", "PowerShell 5.1 has no ternary operator.")
        hits = memory_mod.search(self.paths, "TERNARY")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["source"], "capture")
        self.assertIn("ternary", hits[0]["text"])

    def test_finds_a_knowledge_note(self) -> None:
        memory_mod.knowledge_add(self.paths, "Bundle Targets", "A target names an environment.", ["deploy"])
        hits = memory_mod.search(self.paths, "names an environment")
        self.assertEqual([h["source"] for h in hits], ["knowledge"])

    def test_finds_a_registered_isa_by_task(self) -> None:
        isa_mod.scaffold(slug="row-counts", goal="Prove every load lands.", paths=self.paths)
        hits = memory_mod.search(self.paths, "row-counts")
        self.assertTrue(any(h["source"] == "isa" for h in hits))

    def test_empty_query_finds_nothing(self) -> None:
        memory_mod.capture(self.paths, "fact", "something")
        self.assertEqual(memory_mod.search(self.paths, "   "), [])

    def test_limit_is_respected(self) -> None:
        for index in range(10):
            memory_mod.capture(self.paths, "fact", "repeated marker %d" % index)
        self.assertEqual(len(memory_mod.search(self.paths, "marker", limit=3)), 3)


class DigestTests(TempHomeCase):
    def test_digest_is_markdown_and_counts_by_kind(self) -> None:
        memory_mod.capture(self.paths, "learning", "First lesson.")
        memory_mod.capture(self.paths, "learning", "Second lesson.")
        memory_mod.capture(self.paths, "incident", "The deploy timed out.")
        out = memory_mod.digest(self.paths)
        self.assertIn("# Memory digest", out)
        self.assertIn("| learning | 2 |", out)
        self.assertIn("| incident | 1 |", out)
        self.assertIn("## Work", out)

    def test_digest_on_an_empty_home_says_so(self) -> None:
        out = memory_mod.digest(self.paths)
        self.assertIn("nothing captured in this window", out)

    def test_since_filters_older_records(self) -> None:
        memory_mod.capture(self.paths, "fact", "old news")
        out = memory_mod.digest(self.paths, "2999-01-01T00:00:00Z")
        self.assertIn("nothing captured in this window", out)


class HotLayerTests(TempHomeCase):
    def test_says_when_there_is_no_active_isa(self) -> None:
        block = memory_mod.hot_layer(self.paths)
        self.assertIn("No active ISA", block)

    def test_includes_the_active_isa_and_recent_captures(self) -> None:
        isa_mod.scaffold(slug="hot", goal="Prove the hot layer works.", paths=self.paths)
        memory_mod.capture(self.paths, "decision", "Hooks stay in Python.")
        block = memory_mod.hot_layer(self.paths)
        self.assertIn("Active ISA hot", block)
        self.assertIn("frontier", block)
        self.assertIn("Hooks stay in Python.", block)

    def test_stays_small_enough_to_inject(self) -> None:
        isa_mod.scaffold(slug="hot", goal="Prove the hot layer works.", paths=self.paths)
        for index in range(50):
            memory_mod.capture(self.paths, "fact", "capture number %d " % index + "x" * 400)
        block = memory_mod.hot_layer(self.paths)
        self.assertLess(len(block), 6000, "the hot layer must fit inside the injection budget")


class HealthTests(TempHomeCase):
    def test_reports_an_empty_home_without_failing(self) -> None:
        report = memory_mod.health(self.paths)
        self.assertEqual(report["captures"], 0)
        self.assertIsNone(report["last_capture"])
        self.assertEqual(report["missing_dirs"], [])
        self.assertEqual(report["sizes_bytes"]["captures"], 0)

    def test_reports_sizes_and_recency_after_a_capture(self) -> None:
        memory_mod.capture(self.paths, "fact", "something worth keeping")
        report = memory_mod.health(self.paths)
        self.assertEqual(report["captures"], 1)
        self.assertIsNotNone(report["last_capture"])
        self.assertTrue(report["sizes_bytes"]["captures"] > 0)
        self.assertEqual(report["last_capture_age_days"], 0.0)

    def test_missing_directories_are_named(self) -> None:
        import shutil

        shutil.rmtree(self.paths.knowledge)
        self.assertIn(str(self.paths.knowledge), memory_mod.health(self.paths)["missing_dirs"])


class KnowledgeTests(TempHomeCase):
    def test_add_writes_typed_frontmatter(self) -> None:
        written = memory_mod.knowledge_add(
            self.paths, "Bundle deploy targets", "A target names an environment.", "deploy, databricks"
        )
        self.assertEqual(written.name, "BundleDeployTargets.md")
        body = read(written)
        self.assertIn("type: fact", body)
        self.assertIn("tags: [deploy, databricks]", body)
        self.assertIn("convention: kaios-freshness-v1", body)
        self.assertIn("# Bundle deploy targets", body)

    def test_add_twice_keeps_the_original_created_stamp(self) -> None:
        first = memory_mod.knowledge_add(self.paths, "Repeated", "One.", [])
        created = [line for line in read(first).split("\n") if line.startswith("created:")][0]
        second = memory_mod.knowledge_add(self.paths, "Repeated", "Two.", [])
        self.assertEqual(first, second)
        self.assertIn(created, read(second))
        self.assertIn("Two.", read(second))

    def test_empty_title_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            memory_mod.knowledge_add(self.paths, "  ", "body", [])

    def test_find_returns_metadata(self) -> None:
        memory_mod.knowledge_add(self.paths, "Hook Timeouts", "Twenty seconds per event.", ["hooks"])
        hits = memory_mod.knowledge_find(self.paths, "twenty seconds")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["title"], "Hook Timeouts")
        self.assertEqual(hits[0]["tags"], ["hooks"])
        self.assertEqual(hits[0]["type"], "fact")

    def test_find_with_no_query_lists_everything(self) -> None:
        memory_mod.knowledge_add(self.paths, "One", "a", [])
        memory_mod.knowledge_add(self.paths, "Two", "b", [])
        self.assertEqual(len(memory_mod.knowledge_find(self.paths, "")), 2)

    def test_slug_is_pascal_case(self) -> None:
        self.assertEqual(memory_mod.knowledge_slug("a mixed-case title!"), "AMixedCaseTitle")
        self.assertEqual(memory_mod.knowledge_slug("***"), "Note")


if __name__ == "__main__":
    unittest.main()
