"""ISC-32: every integrity gate must fire on a seeded violation."""

import json
import os
import unittest

from kaios import integrity
# Make the shared helper importable whether the runner puts this directory or
# the repository root on sys.path.
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from support import TempHomeCase, write

MARKER = "seeded-forbidden-marker"


class ContainmentTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.root = self.scratch / "tree"
        self.terms = write(self.root / "tests" / "containment.txt", "%s\nsecond-marker\n" % MARKER)

    def test_a_clean_tree_passes(self) -> None:
        write(self.root / "docs" / "clean.md", "Nothing forbidden here.\n")
        ok, findings = integrity.containment(self.root)
        self.assertTrue(ok)
        self.assertEqual(findings, [])

    def test_a_seeded_hit_fails_and_names_the_line(self) -> None:
        write(self.root / "docs" / "dirty.md", "line one\nthis line has %s in it\n" % MARKER)
        ok, findings = integrity.containment(self.root)
        self.assertFalse(ok)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["code"], "E_CONTAINMENT")
        self.assertEqual(findings[0]["file"], "docs/dirty.md")
        self.assertEqual(findings[0]["line"], 2)
        self.assertEqual(findings[0]["term"], MARKER)

    def test_the_match_is_case_insensitive(self) -> None:
        write(self.root / "a.md", MARKER.upper() + "\n")
        ok, _ = integrity.containment(self.root)
        self.assertFalse(ok)

    def test_the_terms_file_is_not_scanned_against_itself(self) -> None:
        ok, findings = integrity.containment(self.root)
        self.assertTrue(ok, findings)

    def test_git_and_cache_directories_are_skipped(self) -> None:
        write(self.root / ".git" / "COMMIT_EDITMSG", MARKER + "\n")
        write(self.root / "__pycache__" / "x.txt", MARKER + "\n")
        ok, _ = integrity.containment(self.root)
        self.assertTrue(ok)

    def test_binary_files_are_skipped(self) -> None:
        target = self.root / "blob.bin"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(MARKER.encode("utf-8") + b"\x00\x01\x02")
        ok, _ = integrity.containment(self.root)
        self.assertTrue(ok)

    def test_an_extra_terms_file_adds_terms(self) -> None:
        extra = write(self.scratch / "extra.txt", "bonus-marker\n# a comment\n")
        write(self.root / "a.md", "bonus-marker\n")
        ok, findings = integrity.containment(self.root, extra_terms_file=extra)
        self.assertFalse(ok)
        self.assertEqual(findings[0]["term"], "bonus-marker")

    def test_extra_terms_can_come_from_the_environment(self) -> None:
        extra = write(self.scratch / "env-extra.txt", "env-marker\n")
        write(self.root / "a.md", "env-marker\n")
        previous = os.environ.get(integrity.EXTRA_TERMS_ENV)
        os.environ[integrity.EXTRA_TERMS_ENV] = str(extra)
        try:
            ok, findings = integrity.containment(self.root)
        finally:
            if previous is None:
                os.environ.pop(integrity.EXTRA_TERMS_ENV, None)
            else:
                os.environ[integrity.EXTRA_TERMS_ENV] = previous
        self.assertFalse(ok)
        self.assertEqual(findings[0]["term"], "env-marker")

    def test_no_terms_file_warns_rather_than_passing_silently(self) -> None:
        bare = self.scratch / "bare"
        write(bare / "a.md", "anything\n")
        ok, findings = integrity.containment(bare)
        self.assertTrue(ok)
        self.assertEqual(findings[0]["code"], "W_NO_TERMS")


class DocsTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.root = self.scratch / "tree"

    def _freshness(self, body: str = "Body.\n") -> str:
        return "---\nversion: 1.0.0\nlast_updated: 2026-01-01T00:00:00Z\nconvention: kaios-freshness-v1\n---\n\n%s" % body

    def test_a_clean_tree_passes(self) -> None:
        write(self.root / "KAIOS" / "RULES" / "Verification.md", self._freshness())
        ok, findings = integrity.docs(self.root)
        self.assertTrue(ok, findings)

    def test_a_doctrine_doc_without_freshness_frontmatter_fails(self) -> None:
        write(self.root / "KAIOS" / "RULES" / "Verification.md", "# No frontmatter\n")
        ok, findings = integrity.docs(self.root)
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_FRONTMATTER")
        self.assertIn("version", findings[0]["message"])

    def test_a_skill_needs_name_and_description(self) -> None:
        write(self.root / ".github" / "skills" / "isa" / "SKILL.md", "---\nname: isa\n---\n\nBody.\n")
        ok, findings = integrity.docs(self.root)
        self.assertFalse(ok)
        self.assertIn("description", findings[0]["message"])

    def test_an_agent_needs_its_four_keys(self) -> None:
        write(self.root / ".github" / "agents" / "Kai.agent.md", "---\nname: Kai\n---\n\nBody.\n")
        ok, findings = integrity.docs(self.root)
        self.assertFalse(ok)
        self.assertIn("description", findings[0]["message"])
        self.assertIn("model", findings[0]["message"])

    def test_an_instructions_file_needs_applyto(self) -> None:
        write(self.root / ".github" / "instructions" / "python.instructions.md", "---\nversion: 1\n---\n\nBody.\n")
        ok, findings = integrity.docs(self.root)
        self.assertFalse(ok)
        self.assertIn("applyto", findings[0]["message"])

    def test_a_dead_relative_link_fails(self) -> None:
        write(self.root / "KAIOS" / "A.md", self._freshness("See [the rules](RULES/Missing.md).\n"))
        ok, findings = integrity.docs(self.root)
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_DEAD_LINK")

    def test_a_live_relative_link_passes(self) -> None:
        write(self.root / "KAIOS" / "RULES" / "Real.md", self._freshness())
        write(self.root / "KAIOS" / "A.md", self._freshness("See [the rules](RULES/Real.md).\n"))
        ok, findings = integrity.docs(self.root)
        self.assertTrue(ok, findings)

    def test_a_root_relative_link_passes(self) -> None:
        write(self.root / "KAIOS" / "RULES" / "Real.md", self._freshness())
        write(
            self.root / "KAIOS" / "DOCUMENTATION" / "B.md",
            self._freshness("See [the rules](KAIOS/RULES/Real.md).\n"),
        )
        ok, findings = integrity.docs(self.root)
        self.assertTrue(ok, findings)

    def test_urls_anchors_and_code_spans_are_ignored(self) -> None:
        body = "A [site](https://example.invalid/x), an [anchor](#here), and `[a span](nope.md)`.\n"
        write(self.root / "KAIOS" / "A.md", self._freshness(body))
        ok, findings = integrity.docs(self.root)
        self.assertTrue(ok, findings)

    def test_templates_are_exempt_from_freshness_frontmatter(self) -> None:
        write(self.root / "KAIOS" / "TEMPLATES" / "ISA.md", "---\nphase: scoping\nprogress: 0/1\n---\n\n# T\n")
        ok, findings = integrity.docs(self.root)
        self.assertTrue(ok, findings)

    def test_an_empty_tree_warns(self) -> None:
        ok, findings = integrity.docs(self.scratch / "nothing")
        self.assertTrue(ok)
        self.assertEqual(findings[0]["code"], "W_NO_DOCS")


class VersionTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.root = self.scratch / "tree"
        write(self.root / "KAIOS" / "VERSION", "1.0.0\n")
        write(self.root / "KAIOS" / "ALGORITHM" / "LATEST", "1.0.0\n")
        write(self.root / "KAIOS" / "ALGORITHM" / "v1.0.0.md", "# Algorithm\n")

    def test_an_aligned_tree_passes(self) -> None:
        ok, findings = integrity.versions(self.root, package_version="1.0.0")
        self.assertTrue(ok, findings)

    def test_package_drift_fails(self) -> None:
        ok, findings = integrity.versions(self.root, package_version="2.0.0")
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_VERSION_DRIFT")

    def test_readme_drift_fails(self) -> None:
        write(self.root / "README.md", "# KaiOS\n\nVersion 9.9.9\n")
        ok, findings = integrity.versions(self.root, package_version="1.0.0")
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_README_VERSION")

    def test_a_matching_readme_passes(self) -> None:
        write(self.root / "README.md", "# KaiOS\n\nVersion 1.0.0\n")
        ok, findings = integrity.versions(self.root, package_version="1.0.0")
        self.assertTrue(ok, findings)

    def test_a_missing_version_file_fails(self) -> None:
        (self.root / "KAIOS" / "VERSION").unlink()
        ok, findings = integrity.versions(self.root, package_version="1.0.0")
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_NO_VERSION")

    def test_a_malformed_version_fails(self) -> None:
        write(self.root / "KAIOS" / "VERSION", "one\n")
        ok, findings = integrity.versions(self.root, package_version="one")
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_VERSION_FORMAT")

    def test_a_missing_doctrine_pointer_fails(self) -> None:
        (self.root / "KAIOS" / "ALGORITHM" / "LATEST").unlink()
        ok, findings = integrity.versions(self.root, package_version="1.0.0")
        self.assertFalse(ok)
        self.assertEqual([f["code"] for f in findings], ["E_NO_LATEST"])

    def test_a_pointer_at_nothing_fails(self) -> None:
        write(self.root / "KAIOS" / "ALGORITHM" / "LATEST", "9.9.9\n")
        ok, findings = integrity.versions(self.root, package_version="1.0.0")
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_LATEST_TARGET")


class ImportTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.root = self.scratch / "tree"

    def test_stdlib_and_local_imports_pass(self) -> None:
        write(self.root / "helper.py", "VALUE = 1\n")
        write(
            self.root / "mod.py",
            "import json\nimport os.path\nfrom pathlib import Path\nimport helper\nfrom kaios import isa\n",
        )
        ok, findings = integrity.imports(self.root)
        self.assertTrue(ok, findings)

    def test_relative_imports_pass(self) -> None:
        write(self.root / "pkg" / "__init__.py", "")
        write(self.root / "pkg" / "a.py", "from . import b\nfrom .b import thing\n")
        write(self.root / "pkg" / "b.py", "thing = 1\n")
        ok, findings = integrity.imports(self.root)
        self.assertTrue(ok, findings)

    def test_a_third_party_import_fails(self) -> None:
        write(self.root / "mod.py", "import json\nimport " + "requests" + "\n")
        ok, findings = integrity.imports(self.root)
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_NON_STDLIB")
        self.assertEqual(findings[0]["module"], "requests")
        self.assertEqual(findings[0]["line"], 2)

    def test_a_third_party_from_import_fails(self) -> None:
        write(self.root / "mod.py", "from " + "yaml" + " import safe_load\n")
        ok, findings = integrity.imports(self.root)
        self.assertFalse(ok)
        self.assertEqual(findings[0]["module"], "yaml")

    def test_a_syntax_error_fails(self) -> None:
        write(self.root / "broken.py", "def (:\n")
        ok, findings = integrity.imports(self.root)
        self.assertFalse(ok)
        self.assertEqual(findings[0]["code"], "E_SYNTAX")

    def test_a_tree_with_no_python_warns(self) -> None:
        write(self.root / "a.md", "text\n")
        ok, findings = integrity.imports(self.root)
        self.assertTrue(ok)
        self.assertEqual(findings[0]["code"], "W_NO_PYTHON")


class ReportTests(TempHomeCase):
    def test_run_wraps_a_check_in_a_json_ready_report(self) -> None:
        root = self.scratch / "tree"
        write(root / "tests" / "containment.txt", "%s\n" % MARKER)
        write(root / "a.md", MARKER + "\n")
        report = integrity.run("containment", root)
        self.assertFalse(report["ok"])
        self.assertEqual(report["check"], "containment")
        self.assertEqual(report["errors"], 1)
        self.assertEqual(report["warnings"], 0)
        json.loads(integrity.as_json(report))

    def test_run_refuses_an_unknown_check(self) -> None:
        with self.assertRaises(ValueError):
            integrity.run("vibes", self.scratch)

    def test_markdown_renders_a_table(self) -> None:
        report = integrity.run("imports", self.scratch / "empty")
        out = integrity.to_markdown(report)
        self.assertIn("# integrity imports", out)
        self.assertIn("| level | code | file | message |", out)

    def test_every_named_check_is_runnable(self) -> None:
        root = self.scratch / "tree"
        write(root / "a.md", "text\n")
        for name in integrity.CHECKS:
            report = integrity.run(name, root)
            self.assertEqual(report["check"], name)
            self.assertIn("findings", report)


if __name__ == "__main__":
    unittest.main()
