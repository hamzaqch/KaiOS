"""The event list must agree everywhere it is written down.

There are three places an event name can appear: the tuple in ``kaios.events``,
the keys of the checked-in registry, and the hook module directories. Two of
them silently disagreed once — the tuple said SessionEnd while the registry and
the modules said SubagentStart — which registered a dead event for every
user-level install and left a live one unregistered. Reading two files by hand
is what caught it; these tests are so nobody has to.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from kaios import events as events_mod
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
        installed = self.scratch / events_mod.INSTALLED_REGISTRY_RELATIVE
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text(json.dumps({"hooks": {"Stop": [{}], "SessionStart": [{}]}}), encoding="utf-8")
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
    def test_every_entry_names_its_event(self) -> None:
        data = json.loads((repo_root() / events_mod.REGISTRY_RELATIVE).read_text(encoding="utf-8"))
        for event, entries in data["hooks"].items():
            self.assertTrue(entries, "%s has no entries" % event)
            for entry in entries:
                self.assertTrue(
                    str(entry.get("command", "")).endswith(event),
                    "%s entry does not dispatch %s" % (event, event),
                )
                self.assertTrue(str(entry.get("windows", "")).endswith(event))


if __name__ == "__main__":
    unittest.main()
