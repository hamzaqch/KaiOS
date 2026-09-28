"""ISC-28: doctor reports every check and only FAIL is fatal."""

import unittest

from kaios import doctor as doctor_mod
from kaios import memory as memory_mod
# Make the shared helper importable whether the runner puts this directory or
# the repository root on sys.path.
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from support import TempHomeCase, repo_root, write

EXPECTED_CHECKS = (
    "python",
    "home writable",
    "config",
    "doctrine",
    "models registry",
    "hooks registry",
    "active ISA",
    "memory",
    "containment",
    "stdlib only",
)


class FreshHomeTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.report = doctor_mod.run(self.paths)

    def test_a_fresh_home_is_healthy(self) -> None:
        failures = [c for c in self.report["checks"] if c["status"] == doctor_mod.FAIL]
        self.assertEqual(failures, [], "a fresh home must not FAIL anything")
        self.assertTrue(self.report["ok"])

    def test_every_check_is_reported_with_a_known_status(self) -> None:
        names = [c["name"] for c in self.report["checks"]]
        for expected in EXPECTED_CHECKS:
            self.assertIn(expected, names)
        for check in self.report["checks"]:
            self.assertIn(check["status"], (doctor_mod.PASS, doctor_mod.WARN, doctor_mod.FAIL))
            self.assertTrue(str(check["detail"]).strip(), "%s has no detail" % check["name"])

    def test_python_and_home_pass(self) -> None:
        by_name = {c["name"]: c for c in self.report["checks"]}
        self.assertEqual(by_name["python"]["status"], doctor_mod.PASS)
        self.assertEqual(by_name["home writable"]["status"], doctor_mod.PASS)

    def test_absent_optional_pieces_only_warn(self) -> None:
        by_name = {c["name"]: c for c in self.report["checks"]}
        for name in ("config", "hooks registry", "active ISA", "memory"):
            self.assertEqual(by_name[name]["status"], doctor_mod.WARN, name)

    def test_counts_add_up(self) -> None:
        counts = self.report["counts"]
        self.assertEqual(sum(counts.values()), len(self.report["checks"]))

    def test_doctor_creates_the_home_it_checks(self) -> None:
        self.assertTrue(self.paths.home.is_dir())
        self.assertTrue(self.paths.memory.is_dir())

    def test_markdown_lists_every_check(self) -> None:
        out = doctor_mod.to_markdown(self.report)
        self.assertIn("# kaios doctor", out)
        self.assertIn("| check | status | detail |", out)
        for check in self.report["checks"]:
            self.assertIn("| %s |" % check["name"], out)


class PopulatedHomeTests(TempHomeCase):
    def test_a_populated_home_passes_more_checks(self) -> None:
        write(self.paths.config_file, "{}\n")
        write(self.paths.hooks_json, "{}\n")
        write(self.paths.doctrine / "ALGORITHM" / "LATEST", "1.0.0\n")
        memory_mod.capture(self.paths, "learning", "Something worth keeping.")
        report = doctor_mod.run(self.paths)
        by_name = {c["name"]: c for c in report["checks"]}
        for name in ("config", "hooks registry", "doctrine", "memory"):
            self.assertEqual(by_name[name]["status"], doctor_mod.PASS, name)
        self.assertTrue(report["ok"])

    def test_an_unparseable_registry_is_fatal(self) -> None:
        write(self.paths.models_file, "{not json")
        report = doctor_mod.run(self.paths)
        by_name = {c["name"]: c for c in report["checks"]}
        self.assertEqual(by_name["models registry"]["status"], doctor_mod.FAIL)
        self.assertFalse(report["ok"])

    def test_an_unparseable_active_isa_is_reported_not_raised(self) -> None:
        repo = self.fake_repo()
        target = repo / "ISA.md"
        target.write_bytes(b"\xff\xfe not text at all")
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        report = doctor_mod.run(paths)
        by_name = {c["name"]: c for c in report["checks"]}
        self.assertEqual(by_name["active ISA"]["status"], doctor_mod.FAIL)

    def test_an_isa_with_check_errors_warns(self) -> None:
        repo = self.fake_repo()
        write(repo / "ISA.md", "---\nphase: climbing\nprogress: 0/1\n---\n\n# Bad\n\n- [ ] ISC-1: no falsifier.\n")
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        report = doctor_mod.run(paths)
        by_name = {c["name"]: c for c in report["checks"]}
        self.assertEqual(by_name["active ISA"]["status"], doctor_mod.WARN)
        self.assertIn("E_NO_GOAL", by_name["active ISA"]["detail"])


class RepoScopedTests(TempHomeCase):
    def test_with_no_checkout_the_repo_gates_only_warn(self) -> None:
        report = doctor_mod.run(self.paths)
        by_name = {c["name"]: c for c in report["checks"]}
        self.assertEqual(by_name["containment"]["status"], doctor_mod.WARN)
        self.assertEqual(by_name["stdlib only"]["status"], doctor_mod.WARN)

    def test_a_seeded_containment_hit_is_fatal(self) -> None:
        repo = self.fake_repo()
        write(repo / "tests" / "containment.txt", "seeded-forbidden-marker\n")
        write(repo / "doc.md", "seeded-forbidden-marker\n")
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        report = doctor_mod.run(paths)
        by_name = {c["name"]: c for c in report["checks"]}
        self.assertEqual(by_name["containment"]["status"], doctor_mod.FAIL)
        self.assertFalse(report["ok"])

    def test_this_checkout_reports_a_real_stdlib_verdict(self) -> None:
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        report = doctor_mod.run(paths)
        by_name = {c["name"]: c for c in report["checks"]}
        self.assertEqual(
            by_name["stdlib only"]["status"],
            doctor_mod.PASS,
            by_name["stdlib only"]["detail"],
        )


if __name__ == "__main__":
    unittest.main()
