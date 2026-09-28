"""ISC-31: the version file and the append-only change registry."""

import json
import unittest

from kaios import ledger as ledger_mod
from tests.support import TempHomeCase, read, write


class VersionTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.root = self.fake_repo()
        write(self.root / "SYSTEM" / "VERSION", "1.2.3\n")

    def test_version_reads_the_shipped_file(self) -> None:
        self.assertEqual(ledger_mod.version(self.paths, root=self.root), "1.2.3")
        self.assertEqual(
            ledger_mod.version_file(self.paths, root=self.root), self.root / "SYSTEM" / "VERSION"
        )

    def test_version_falls_back_to_a_flat_layout(self) -> None:
        flat = self.fake_repo("flat")
        write(flat / "VERSION", "0.4.0\n")
        self.assertEqual(ledger_mod.version(self.paths, root=flat), "0.4.0")

    def test_missing_version_reads_as_zero(self) -> None:
        empty = self.fake_repo("empty")
        self.assertEqual(ledger_mod.version(self.paths, root=empty), "0.0.0")

    def test_bump_patch(self) -> None:
        result = ledger_mod.bump("patch", paths=self.paths, root=self.root)
        self.assertEqual(result["previous"], "1.2.3")
        self.assertEqual(result["version"], "1.2.4")
        self.assertEqual(read(self.root / "SYSTEM" / "VERSION").strip(), "1.2.4")

    def test_bump_minor_resets_patch(self) -> None:
        self.assertEqual(ledger_mod.bump("minor", paths=self.paths, root=self.root)["version"], "1.3.0")

    def test_bump_major_resets_the_rest(self) -> None:
        self.assertEqual(ledger_mod.bump("major", paths=self.paths, root=self.root)["version"], "2.0.0")

    def test_bump_refuses_an_unknown_part(self) -> None:
        with self.assertRaises(ValueError):
            ledger_mod.bump("epoch", paths=self.paths, root=self.root)
        self.assertEqual(read(self.root / "SYSTEM" / "VERSION").strip(), "1.2.3")

    def test_bump_refuses_a_malformed_version(self) -> None:
        write(self.root / "SYSTEM" / "VERSION", "one point two\n")
        with self.assertRaises(ValueError):
            ledger_mod.bump("patch", paths=self.paths, root=self.root)

    def test_bump_appends_to_the_registry(self) -> None:
        ledger_mod.bump("patch", paths=self.paths, root=self.root)
        entries = ledger_mod.log(paths=self.paths)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "version")
        self.assertEqual(entries[0]["meta"]["version"], "1.2.4")
        self.assertEqual(entries[0]["meta"]["previous"], "1.2.3")

    def test_bump_carries_a_summary(self) -> None:
        ledger_mod.bump("patch", paths=self.paths, root=self.root, summary="Shipped the core.")
        self.assertEqual(ledger_mod.log(paths=self.paths)[0]["summary"], "Shipped the core.")


class RecordTests(TempHomeCase):
    def test_record_then_log_round_trip(self) -> None:
        ledger_mod.record("deploy", "Pushed the hook registry.", {"target": "dev"}, paths=self.paths)
        entries = ledger_mod.log(paths=self.paths)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["kind"], "deploy")
        self.assertEqual(entries[0]["meta"]["target"], "dev")
        self.assertTrue(entries[0]["ts"].endswith("Z"))

    def test_log_is_newest_first_and_limited(self) -> None:
        for index in range(5):
            ledger_mod.record("change", "change %d" % index, paths=self.paths)
        entries = ledger_mod.log(limit=2, paths=self.paths)
        self.assertEqual([e["summary"] for e in entries], ["change 4", "change 3"])

    def test_log_on_an_empty_home_is_empty(self) -> None:
        self.assertEqual(ledger_mod.log(paths=self.paths), [])

    def test_record_needs_a_kind_and_a_summary(self) -> None:
        with self.assertRaises(ValueError):
            ledger_mod.record("", "no kind", paths=self.paths)
        with self.assertRaises(ValueError):
            ledger_mod.record("change", "   ", paths=self.paths)

    def test_a_corrupt_line_does_not_break_the_log(self) -> None:
        ledger_mod.record("change", "good line", paths=self.paths)
        with open(self.paths.ledger, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("{not json at all\n")
        ledger_mod.record("change", "another good line", paths=self.paths)
        entries = ledger_mod.log(paths=self.paths)
        self.assertEqual([e["summary"] for e in entries], ["another good line", "good line"])

    def test_every_line_is_one_json_object(self) -> None:
        ledger_mod.record("change", "one", paths=self.paths)
        ledger_mod.record("change", "two", paths=self.paths)
        lines = [line for line in read(self.paths.ledger).split("\n") if line.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertIsInstance(json.loads(line), dict)


if __name__ == "__main__":
    unittest.main()
