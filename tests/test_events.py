"""The event list must agree everywhere it is written down.

There are three places an event name can appear: the tuple in ``kaios.events``,
the keys of the checked-in registry, and the hook module directories. Two of
them silently disagreed once — the tuple said SessionEnd while the registry and
the modules said SubagentStart — which registered a dead event for every
user-level install and left a live one unregistered. Reading two files by hand
is what caught it; these tests are so nobody has to.
"""

import ast
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kaios import events as events_mod
from kaios.paths import Paths
from tests.support import repo_root


class RegistryAgreementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = repo_root()
        self.registry = self.root / events_mod.REGISTRY_RELATIVE

    def test_the_registry_exists(self) -> None:
        self.assertTrue(self.registry.is_file(), "no registry at %s" % events_mod.REGISTRY_RELATIVE)

    def test_the_tuple_matches_the_registry_exactly(self) -> None:
        found = events_mod.registry_events(self.root, strict=True)
        self.assertEqual(
            list(events_mod.EVENTS),
            list(found),
            "kaios.events.EVENTS and the registry disagree; a user-level install "
            "would register the wrong events",
        )

    def test_there_are_eight_of_them(self) -> None:
        self.assertEqual(len(events_mod.EVENTS), 8)
        self.assertEqual(len(set(events_mod.EVENTS)), 8, "an event name is repeated")

    def test_the_root_addressed_reader_falls_back_rather_than_raising(self) -> None:
        self.assertEqual(events_mod.registry_events(self.root / "nowhere"), events_mod.EVENTS)

    def test_the_root_addressed_reader_raises_in_strict_mode(self) -> None:
        with self.assertRaises((OSError, ValueError)):
            events_mod.registry_events(self.root / "nowhere", strict=True)


class PathAddressedReaderTests(unittest.TestCase):
    """``read_registry`` is for a caller that must not paper over a bad registry.

    ``kaios hooks list`` reports how many events are registered, and ISC-11's
    falsifier is that count coming back under eight. A reader that substituted
    the default on an unreadable file would report eight for a registry with
    none, hiding the one condition the claim exists to catch.
    """

    def setUp(self) -> None:
        self._dir = tempfile.mkdtemp(prefix="kaios-events-")
        self.scratch = Path(self._dir)

    def tearDown(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)

    def _write(self, text: str) -> Path:
        target = self.scratch / "kaios.json"
        target.write_text(text, encoding="utf-8")
        return target

    def test_it_reads_any_path_not_just_a_repository_root(self) -> None:
        """The installed registry sits nowhere near the checked-in relative path."""
        installed = Paths(home=self.scratch / "home").hooks_json
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text(json.dumps({"hooks": {"Stop": [{}], "SessionStart": [{}]}}), encoding="utf-8")
        self.assertFalse(str(installed).endswith(events_mod.REGISTRY_RELATIVE))
        self.assertEqual(events_mod.read_registry(installed), ("Stop", "SessionStart"))

    def test_it_preserves_file_order(self) -> None:
        target = self._write(json.dumps({"hooks": {"Stop": [{}], "PreToolUse": [{}]}}))
        self.assertEqual(events_mod.read_registry(target), ("Stop", "PreToolUse"))

    def test_a_missing_file_raises(self) -> None:
        with self.assertRaises(OSError):
            events_mod.read_registry(self.scratch / "absent.json")

    def test_malformed_json_raises(self) -> None:
        with self.assertRaises(ValueError):
            events_mod.read_registry(self._write("{not json"))

    def test_a_registry_with_no_hooks_object_raises(self) -> None:
        with self.assertRaises(ValueError):
            events_mod.read_registry(self._write(json.dumps({"version": 1})))

    def test_an_empty_hooks_object_raises_rather_than_reporting_zero(self) -> None:
        with self.assertRaises(ValueError):
            events_mod.read_registry(self._write(json.dumps({"hooks": {}})))

    def test_a_json_array_raises(self) -> None:
        with self.assertRaises(ValueError):
            events_mod.read_registry(self._write(json.dumps([1, 2, 3])))

    def test_it_never_substitutes_the_default(self) -> None:
        target = self._write(json.dumps({"hooks": {"Stop": [{}]}}))
        self.assertEqual(events_mod.read_registry(target), ("Stop",))
        self.assertNotEqual(events_mod.read_registry(target), events_mod.EVENTS)


class OneDefinitionTests(unittest.TestCase):
    """Each registry location is written down exactly once in the package.

    Both registry paths had picked up second and third definitions: the
    checked-in one in `kaios.events` and again in `kaios.setup`, plus a third
    spelling built piece by piece in `kaios.doctor`, and the installed one as a
    constant in `kaios.events` beside the `Paths.hooks_json` that already owned
    it. They agreed at the time, which is exactly why nothing caught them.
    """

    CHECKED_IN = ".github/hooks/kaios.json"

    def _module_sources(self):
        for path in sorted((repo_root() / "kaios").glob("*.py")):
            yield path, path.read_text(encoding="utf-8")

    def test_the_checked_in_path_is_assigned_in_exactly_one_module(self) -> None:
        assigners = []
        for path, source in self._module_sources():
            tree = ast.parse(source, filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                    if node.value.value == self.CHECKED_IN:
                        assigners.append(path.name)
        self.assertEqual(
            assigners,
            ["events.py"],
            "the checked-in registry path is assigned as a literal in %s; it belongs "
            "only in events.py" % (assigners or "nowhere"),
        )

    def test_the_constant_is_the_path_it_claims_to_be(self) -> None:
        self.assertEqual(events_mod.REGISTRY_RELATIVE, self.CHECKED_IN)
        self.assertTrue((repo_root() / events_mod.REGISTRY_RELATIVE).is_file())

    def test_setup_reuses_the_constant_rather_than_restating_it(self) -> None:
        from kaios import setup as setup_mod

        self.assertIs(setup_mod.HOOKS_REGISTRY_RELATIVE, events_mod.REGISTRY_RELATIVE)

    def test_only_paths_builds_a_registry_location_from_segments(self) -> None:
        """``paths.py`` is the owner, so it is the one module allowed to compose it.

        Anywhere else, assembling ``hooks`` and ``kaios.json`` by hand is a new
        definition of a location that already has one. That is how ``doctor``
        ended up with a third spelling of the checked-in path.
        """
        offenders = [
            path.name
            for path, source in self._module_sources()
            if path.name != "paths.py" and '"hooks"' in source and '"kaios.json"' in source
        ]
        self.assertEqual(offenders, [], "%s spells a registry location in pieces" % offenders)

    def test_the_installed_location_lives_only_in_paths(self) -> None:
        self.assertFalse(
            hasattr(events_mod, "INSTALLED_REGISTRY_RELATIVE"),
            "events should not name the installed location; Paths.hooks_json owns it",
        )
        resolved = Paths(home=Path("/tmp/kaios-probe-home")).hooks_json
        self.assertEqual(resolved.name, "kaios.json")
        self.assertEqual(resolved.parent.name, "hooks")


class HookModuleAgreementTests(unittest.TestCase):
    """Every registered event needs somewhere for its hooks to live."""

    def setUp(self) -> None:
        self.hooks_dir = repo_root() / "kaios" / "hooks"
        if not self.hooks_dir.is_dir():
            self.skipTest("the hooks package is not in this checkout yet")
        self.present = sorted(
            path.name
            for path in self.hooks_dir.iterdir()
            if path.is_dir() and path.name != "__pycache__"
        )
        if not self.present:
            self.skipTest("the hooks package has no event directories yet")

    def test_every_event_has_a_module_directory(self) -> None:
        expected = sorted(events_mod.event_dir(event) for event in events_mod.EVENTS)
        missing = [name for name in expected if name not in self.present]
        self.assertEqual(missing, [], "registered events with nowhere to put a hook: %s" % missing)

    def test_no_module_directory_is_unregistered(self) -> None:
        expected = [events_mod.event_dir(event) for event in events_mod.EVENTS]
        orphans = [name for name in self.present if name not in expected]
        self.assertEqual(orphans, [], "hook directories no event registers: %s" % orphans)

    def test_a_hook_layer_event_list_agrees_with_this_one(self) -> None:
        """Green by construction while the hook layer re-exports, and that is fine.

        The hook layer imports ``EVENTS`` from ``kaios.events``, so today this
        compares the tuple to itself. Keeping it is deliberate: the attribute
        resolving does not prove it is a re-export, so the day a literal tuple
        goes back into ``kaios/hooks/__init__.py`` this is what catches it
        drifting. The name says agreement, not that a second definition exists.
        """
        try:
            from kaios import hooks as hooks_mod
        except ImportError:
            self.skipTest("the hooks package does not import")
        theirs = getattr(hooks_mod, "EVENTS", None)
        if theirs is None:
            self.skipTest("the hook layer exposes no EVENTS at all")
        self.assertEqual(
            list(theirs),
            list(events_mod.EVENTS),
            "the hook layer and kaios.events disagree about the event list",
        )


class EventDirTests(unittest.TestCase):
    def test_camel_case_becomes_snake_case(self) -> None:
        self.assertEqual(events_mod.event_dir("SessionStart"), "session_start")
        self.assertEqual(events_mod.event_dir("PreToolUse"), "pre_tool_use")
        self.assertEqual(events_mod.event_dir("Stop"), "stop")
        self.assertEqual(events_mod.event_dir("SubagentStart"), "subagent_start")

    def test_canonical_accepts_every_spelling_of_a_real_event(self) -> None:
        for event in events_mod.EVENTS:
            for spelling in (event, event.lower(), event.upper(), events_mod.event_dir(event)):
                self.assertEqual(events_mod.canonical(spelling), event, "failed on %r" % spelling)

    def test_canonical_rejects_an_event_that_does_not_exist(self) -> None:
        self.assertIsNone(events_mod.canonical("SessionEnd"))
        self.assertIsNone(events_mod.canonical("NotAnEvent"))
        self.assertIsNone(events_mod.canonical(""))


class RegistryShapeTests(unittest.TestCase):
    """Every command line in the registry dispatches the event it is filed under.

    A wrapper invoked with the wrong event name runs the wrong hooks and nothing
    reports it, because both the registry and the wrapper stay perfectly valid.
    ``tests/test_registry_dialects.py`` owns the shape of these entries; this
    checks only that each one names its own event.
    """

    def _command_lines(self, entry: dict) -> list:
        nested = entry.get("hooks")
        if isinstance(nested, list):
            lines: list = []
            for item in nested:
                lines.extend(self._command_lines(item))
            return lines
        return [
            str(value)
            for key, value in entry.items()
            if key in ("command", "windows", "bash", "powershell")
        ]

    def test_every_entry_dispatches_the_event_it_is_filed_under(self) -> None:
        data = json.loads((repo_root() / events_mod.REGISTRY_RELATIVE).read_text(encoding="utf-8"))
        for event, entries in data["hooks"].items():
            self.assertTrue(entries, "%s has no entries" % event)
            for entry in entries:
                lines = self._command_lines(entry)
                self.assertTrue(lines, "%s entry carries no command line" % event)
                for line in lines:
                    self.assertTrue(
                        line.endswith(" " + event),
                        "%s entry dispatches something else: %s" % (event, line),
                    )


class RegistryNameTests(unittest.TestCase):
    """The key spelling per event is written down once and used everywhere.

    ``setup`` renders a user-level registry and ``Install.ps1`` renders another,
    and both have to agree with the checked-in file about how each event is
    spelled — a camelCase key both engines read, or a PascalCase key the Copilot
    CLI engine reads under Claude semantics. Spelling one of them a second time
    by hand is how the two dialects drifted apart to begin with.
    """

    def test_every_event_has_a_registry_spelling(self) -> None:
        self.assertEqual(sorted(events_mod.REGISTRY_EVENT_NAMES), sorted(events_mod.EVENTS))

    def test_every_spelling_canonicalizes_back_to_its_event(self) -> None:
        for event, key in events_mod.REGISTRY_EVENT_NAMES.items():
            self.assertEqual(events_mod.canonical(key), event, "failed on %r" % key)
            self.assertEqual(events_mod.registry_key(event), key)

    def test_the_checked_in_registry_uses_exactly_those_spellings(self) -> None:
        data = json.loads((repo_root() / events_mod.REGISTRY_RELATIVE).read_text(encoding="utf-8"))
        expected = [events_mod.REGISTRY_EVENT_NAMES[event] for event in events_mod.EVENTS]
        self.assertEqual(list(data["hooks"].keys()), expected)

    def test_the_nested_events_are_the_pascal_case_ones(self) -> None:
        self.assertEqual(events_mod.NESTED_REGISTRY_EVENTS, ("PreCompact", "SubagentStart"))
        for event in events_mod.NESTED_REGISTRY_EVENTS:
            self.assertEqual(events_mod.REGISTRY_EVENT_NAMES[event], event)

    def test_registry_keys_canonicalize_to_the_event_list_in_order(self) -> None:
        """The drift guard, in the dialect the file is actually written in."""
        found = events_mod.read_registry(repo_root() / events_mod.REGISTRY_RELATIVE)
        self.assertEqual(list(found), list(events_mod.EVENTS))


class CopilotDialectTests(unittest.TestCase):
    """The Copilot CLI engine's event names have to reach our event list.

    Its vocabulary is not ours: ``userPromptSubmitted`` and ``agentStop`` are the
    same events under different names, and ``sessionEnd`` is an event it has and
    we do not. Reading a registry written in that dialect as a file full of
    unknown names is the failure that dropped every hook item in that engine and
    blocked every tool call behind it.
    """

    def test_the_two_translated_names(self) -> None:
        self.assertEqual(events_mod.canonical("userPromptSubmitted"), "UserPromptSubmit")
        self.assertEqual(events_mod.canonical("agentStop"), "Stop")

    def test_the_camel_case_names_that_are_only_case_variants(self) -> None:
        for spelling, expected in (
            ("sessionStart", "SessionStart"),
            ("preToolUse", "PreToolUse"),
            ("postToolUse", "PostToolUse"),
            ("preCompact", "PreCompact"),
            ("subagentStart", "SubagentStart"),
            ("subagentStop", "SubagentStop"),
        ):
            self.assertEqual(events_mod.canonical(spelling), expected, "failed on %r" % spelling)

    def test_an_event_that_engine_has_and_we_do_not_is_ignored(self) -> None:
        self.assertIsNone(events_mod.canonical("sessionEnd"))
        self.assertIsNone(events_mod.canonical("errorOccurred"))
        self.assertIsNone(events_mod.canonical("postToolUseFailure"))


class RegistryReadingTests(unittest.TestCase):
    """``read_registry`` reads either dialect and reports our names."""

    def setUp(self) -> None:
        self._dir = tempfile.mkdtemp(prefix="kaios-dialect-")
        self.scratch = Path(self._dir)

    def tearDown(self) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)

    def _write(self, data: dict) -> Path:
        target = self.scratch / "kaios.json"
        target.write_text(json.dumps(data), encoding="utf-8")
        return target

    def test_camel_case_keys_come_back_canonical(self) -> None:
        target = self._write({"hooks": {"preToolUse": [{}], "agentStop": [{}]}})
        self.assertEqual(events_mod.read_registry(target), ("PreToolUse", "Stop"))

    def test_a_claude_nested_entry_is_accepted(self) -> None:
        target = self._write(
            {"hooks": {"PreCompact": [{"hooks": [{"type": "command", "command": "x"}]}]}}
        )
        self.assertEqual(events_mod.read_registry(target), ("PreCompact",))

    def test_two_spellings_of_one_event_count_once(self) -> None:
        target = self._write({"hooks": {"Stop": [{}], "agentStop": [{}]}})
        self.assertEqual(events_mod.read_registry(target), ("Stop",))

    def test_an_event_we_do_not_have_is_skipped_not_fatal(self) -> None:
        target = self._write({"hooks": {"sessionEnd": [{}], "preToolUse": [{}]}})
        self.assertEqual(events_mod.read_registry(target), ("PreToolUse",))

    def test_a_registry_of_nothing_we_know_raises(self) -> None:
        target = self._write({"hooks": {"sessionEnd": [{}], "notAnEvent": [{}]}})
        with self.assertRaises(ValueError):
            events_mod.read_registry(target)

    def test_an_event_registered_with_no_entries_registers_nothing(self) -> None:
        target = self._write({"hooks": {"preToolUse": [], "agentStop": [{}]}})
        self.assertEqual(events_mod.read_registry(target), ("Stop",))


if __name__ == "__main__":
    unittest.main()
