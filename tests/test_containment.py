"""ISC-2: the real repository must contain none of the forbidden terms.

This runs over the checkout this file lives in, not a fixture. The term list is
read from ``tests/containment.txt`` and is never reproduced here, so the test
file cannot fail itself.
"""

import tempfile
import unittest
from pathlib import Path

from kaios import integrity
# Make the shared helper importable whether the runner puts this directory or
# the repository root on sys.path.
import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

from support import repo_root


class ContainmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = repo_root()
        self.terms_file = self.root / "tests" / "containment.txt"

    def test_the_term_list_exists_and_is_not_empty(self) -> None:
        self.assertTrue(self.terms_file.is_file(), "no term list at tests/containment.txt")
        terms = integrity.load_terms(self.terms_file)
        self.assertTrue(terms, "the term list is empty, so nothing would be checked")

    def test_the_repository_contains_no_forbidden_term(self) -> None:
        ok, findings = integrity.containment(self.root)
        hits = [f for f in findings if f.get("level") == "error"]
        detail = "\n".join(
            "%s line %s matched a forbidden term" % (hit["file"], hit.get("line")) for hit in hits
        )
        self.assertEqual(hits, [], "forbidden terms found:\n%s" % detail)
        self.assertTrue(ok)

    def test_the_scan_actually_covered_the_tree(self) -> None:
        """A silent pass would be worse than a failure, so prove the scanner fires.

        Feed it a term that is certainly in the checkout. If that comes back
        clean, the clean result above meant nothing was read.
        """
        with tempfile.TemporaryDirectory() as scratch:
            probe = Path(scratch) / "probe-terms.txt"
            probe.write_text("KaiOS\n", encoding="utf-8")
            ok, findings = integrity.containment(self.root, terms_file=probe)
        self.assertFalse(ok, "the scanner found nothing when given a term that is present")
        self.assertTrue(any(f["code"] == "E_CONTAINMENT" for f in findings))
        self.assertTrue(len(findings) > 10, "only %d file(s) were read" % len(findings))


if __name__ == "__main__":
    unittest.main()
