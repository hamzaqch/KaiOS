"""Shared test scaffolding. Never touches the real KAIOS_HOME.

Every case gets its own temporary home through the ``KAIOS_HOME`` environment
variable, restored on teardown, so a failing test cannot leak state into the
next one or into the machine.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from kaios.paths import HOME_ENV, Paths


def repo_root() -> Path:
    """The checkout this test file lives in, found without hardcoding a path."""
    return Path(__file__).resolve().parents[1]


def fixtures() -> Path:
    return Path(__file__).resolve().parent / "fixtures"


def read(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: Path, text: str, newline: str = "\n") -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline=newline) as handle:
        handle.write(text)
    return target


class TempHomeCase(unittest.TestCase):
    """A case with a private KAIOS_HOME and a scratch directory."""

    def setUp(self) -> None:
        self._scratch = Path(tempfile.mkdtemp(prefix="kaios-test-"))
        self.home = self._scratch / "home"
        self._previous = os.environ.get(HOME_ENV)
        os.environ[HOME_ENV] = str(self.home)
        self.paths = Paths(home=self.home, repo=None, cwd=self._scratch).ensure()

    def tearDown(self) -> None:
        if self._previous is None:
            os.environ.pop(HOME_ENV, None)
        else:
            os.environ[HOME_ENV] = self._previous
        shutil.rmtree(self._scratch, ignore_errors=True)

    @property
    def scratch(self) -> Path:
        return self._scratch

    def fake_repo(self, name: str = "repo") -> Path:
        """A directory that looks like a checkout, for repo-scoped behaviour."""
        root = self._scratch / name
        (root / ".git").mkdir(parents=True, exist_ok=True)
        return root
