"""Path resolution: KAIOS_HOME, the doctrine tree, and the enclosing git repo.

Everything that changes at runtime lives under ``KAIOS_HOME`` (default
``~/.kaios``). Nothing here touches the filesystem unless :meth:`Paths.ensure`
is called.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

HOME_ENV = "KAIOS_HOME"
DEFAULT_HOME = "~/.kaios"

#: The doctrine tree: algorithm, rules, templates, and the shipped registries.
#: Deliberately not named after the package — a doctrine directory differing
#: from ``.github/kaios/`` only in case cannot coexist with it on Windows or macOS.
DOCTRINE_DIR = "SYSTEM"

#: The name the doctrine tree shipped under before the rename. Kept as a
#: fallback so an existing KAIOS_HOME or checkout keeps resolving.
LEGACY_DOCTRINE_DIRS = ("KAIOS",)

#: The one directory the whole framework lives in inside a checkout. Everything
#: KaiOS ships — the package, the doctrine tree, the scripts, the tests and every
#: Copilot surface — sits under it, so a single folder carries the framework into
#: any work repository and Copilot discovers all of it where it already looks.
FRAMEWORK_DIR = ".github"


def doctrine_candidates(base: Path | str) -> list[Path]:
    """Doctrine tree locations under ``base``, current name first."""
    root = Path(base)
    return [root / DOCTRINE_DIR] + [root / name for name in LEGACY_DOCTRINE_DIRS]


def repo_doctrine_candidates(repo: Path | str) -> list[Path]:
    """Doctrine tree locations in a checkout, current layout first.

    ``<repo>/.github/SYSTEM`` is where the doctrine tree lives now. The flat
    ``<repo>/SYSTEM`` and ``<repo>/KAIOS`` shapes are probed after it so a
    checkout made before the framework moved under ``.github`` keeps resolving.
    """
    root = Path(repo)
    return doctrine_candidates(root / FRAMEWORK_DIR) + doctrine_candidates(root)


#: Directories :meth:`Paths.ensure` creates, as attribute names.
MANAGED_DIRS = (
    "config_dir",
    "user_dir",
    "projects_dir",
    "memory",
    "work",
    "state",
    "knowledge",
    "learning",
    "reflections",
    "incidents",
    "observability",
    "hooks_dir",
)


def find_repo(start: Path | str | None = None) -> Path | None:
    """Walk up from ``start`` (default: cwd) to the nearest directory with .git."""
    try:
        here = Path(start).expanduser().resolve() if start else Path.cwd().resolve()
    except OSError:
        return None
    if here.is_file():
        here = here.parent
    for candidate in (here, *here.parents):
        marker = candidate / ".git"
        if marker.is_dir() or marker.is_file():
            return candidate
    return None


def resolve_home(home: Path | str | None = None) -> Path:
    """KAIOS_HOME from the argument, then the environment, then the default."""
    raw = str(home) if home else os.environ.get(HOME_ENV) or DEFAULT_HOME
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return Path(expanded).absolute()


@dataclass(frozen=True)
class Paths:
    """Resolved locations for one KaiOS invocation."""

    home: Path
    repo: Path | None = None
    cwd: Path | None = None

    @classmethod
    def resolve(cls, cwd: Path | str | None = None, home: Path | str | None = None) -> "Paths":
        where = Path(cwd).expanduser().absolute() if cwd else Path.cwd()
        return cls(home=resolve_home(home), repo=find_repo(where), cwd=where)

    # --- configuration -------------------------------------------------
    @property
    def config_dir(self) -> Path:
        return self.home / "CONFIG"

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.json"

    @property
    def models_file(self) -> Path:
        return self.config_dir / "models.json"

    # --- the user's own content ---------------------------------------
    @property
    def user_dir(self) -> Path:
        return self.home / "USER"

    @property
    def profile(self) -> Path:
        return self.user_dir / "PROFILE.md"

    @property
    def projects(self) -> Path:
        return self.user_dir / "PROJECTS.md"

    @property
    def projects_dir(self) -> Path:
        return self.user_dir / "PROJECTS"

    @property
    def mcp_json(self) -> Path:
        return self.user_dir / "mcp.json"

    # --- memory --------------------------------------------------------
    @property
    def memory(self) -> Path:
        return self.home / "MEMORY"

    @property
    def work(self) -> Path:
        return self.memory / "WORK"

    @property
    def state(self) -> Path:
        return self.memory / "STATE"

    @property
    def work_json(self) -> Path:
        return self.state / "work.json"

    @property
    def ledger(self) -> Path:
        return self.state / "ledger.jsonl"

    @property
    def knowledge(self) -> Path:
        return self.memory / "KNOWLEDGE"

    @property
    def learning(self) -> Path:
        return self.memory / "LEARNING"

    @property
    def captures(self) -> Path:
        return self.learning / "captures.jsonl"

    @property
    def reflections(self) -> Path:
        return self.learning / "REFLECTIONS"

    @property
    def incidents(self) -> Path:
        return self.learning / "INCIDENTS"

    # --- observability -------------------------------------------------
    @property
    def observability(self) -> Path:
        return self.memory / "OBSERVABILITY"

    @property
    def hook_events(self) -> Path:
        return self.observability / "hook-events.jsonl"

    @property
    def tool_events(self) -> Path:
        return self.observability / "tool-events.jsonl"

    @property
    def ask_fidelity(self) -> Path:
        return self.observability / "ask-fidelity.jsonl"

    # --- doctrine ------------------------------------------------------
    @property
    def doctrine(self) -> Path:
        """The installed doctrine copy inside KAIOS_HOME."""
        for candidate in doctrine_candidates(self.home):
            if candidate.is_dir():
                return candidate
        return self.home / DOCTRINE_DIR

    @property
    def hooks_dir(self) -> Path:
        """User-level hook registry directory inside KAIOS_HOME."""
        return self.home / "hooks"

    @property
    def hooks_json(self) -> Path:
        return self.hooks_dir / "kaios.json"

    @property
    def repo_doctrine(self) -> Path | None:
        """The doctrine tree in the checkout, if this invocation is inside one."""
        if self.repo is None:
            return None
        for candidate in repo_doctrine_candidates(self.repo) + [self.repo]:
            if (candidate / "ALGORITHM").is_dir() or (candidate / "VERSION").is_file():
                return candidate
        return None

    @property
    def repo_isa(self) -> Path | None:
        if self.repo is None:
            return None
        candidate = self.repo / "ISA.md"
        return candidate if candidate.is_file() else None

    @property
    def repo_models_file(self) -> Path | None:
        if self.repo is None:
            return None
        for base in repo_doctrine_candidates(self.repo):
            candidate = base / "CONFIG" / "models.json"
            if candidate.is_file():
                return candidate
        return None

    @property
    def templates_dir(self) -> Path | None:
        """Where the shipped templates are: the checkout first, then KAIOS_HOME."""
        candidates: list[Path] = []
        if self.repo is not None:
            candidates += [base / "TEMPLATES" for base in repo_doctrine_candidates(self.repo)]
        candidates.append(self.doctrine / "TEMPLATES")
        # The package sits at ``.github/kaios``, so its parent IS the framework
        # directory and the doctrine tree is ``.github/SYSTEM`` beside it.
        package_parent = Path(__file__).resolve().parent.parent
        candidates += [base / "TEMPLATES" for base in doctrine_candidates(package_parent)]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return None

    # --- behaviour -----------------------------------------------------
    def ensure(self) -> "Paths":
        """Create every managed directory. Idempotent."""
        self.home.mkdir(parents=True, exist_ok=True)
        for name in MANAGED_DIRS:
            getattr(self, name).mkdir(parents=True, exist_ok=True)
        return self

    def to_dict(self) -> dict:
        out: dict = {"home": str(self.home)}
        for name in (
            "config_dir",
            "config_file",
            "models_file",
            "user_dir",
            "profile",
            "projects",
            "projects_dir",
            "mcp_json",
            "memory",
            "work",
            "state",
            "work_json",
            "ledger",
            "knowledge",
            "learning",
            "captures",
            "reflections",
            "incidents",
            "observability",
            "hook_events",
            "tool_events",
            "ask_fidelity",
            "doctrine",
            "hooks_dir",
            "hooks_json",
        ):
            out[name] = str(getattr(self, name))
        for name in ("repo", "repo_isa", "repo_doctrine", "repo_models_file", "templates_dir", "cwd"):
            value = getattr(self, name)
            out[name] = str(value) if value is not None else None
        out["home_env"] = HOME_ENV
        out["home_from_env"] = bool(os.environ.get(HOME_ENV))
        return out
