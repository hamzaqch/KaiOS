"""The checked-in registry has to be readable by BOTH of Copilot's hook engines.

Copilot in VS Code ships two hook engines and they do not share one dialect. The
"Local" engine reads PascalCase event keys with flat entries; the Copilot CLI
engine — what the Agent Host and the `copilot` CLI use — reads camelCase keys
with `bash`/`powershell`/`timeoutSec` entries, drops any item it cannot parse,
and fails a preToolUse hook CLOSED. A registry in the wrong dialect for that
engine therefore does not degrade: every item is dropped, the file is reported as
needing repair, and every tool call is denied until it is fixed. That was a field
outage, and this file is the regression for it.

Falsifier: any of the six shared events written PascalCase, any flat entry
carrying the Claude keys `command`/`windows`/`timeout`, either PascalCase-only
event written without the Claude nested shape, or a key no engine reads.

See ``.github/SYSTEM/DOCUMENTATION/Hooks.md`` § Two Copilot engines, one registry.
"""

from __future__ import annotations

import json
import unittest

from kaios import events as events_mod
from tests.support import repo_root

#: Events shipped under the Copilot CLI engine's camelCase name, flat entries.
FLAT_KEYS = (
    "sessionStart",
    "userPromptSubmitted",
    "preToolUse",
    "postToolUse",
    "subagentStop",
    "agentStop",
)

#: Events that engine has no camelCase name for, shipped Claude-nested instead.
NESTED_KEYS = ("PreCompact", "SubagentStart")

#: Keys that belong to the Claude entry shape. On a flat entry they are what the
#: CLI engine cannot parse, so their absence there is the point of this file.
CLAUDE_ENTRY_KEYS = ("command", "windows", "timeout")


class RegistryDialectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.path = repo_root() / events_mod.REGISTRY_RELATIVE
        self.assertTrue(self.path.is_file(), "no registry at %s" % events_mod.REGISTRY_RELATIVE)
        self.data = json.loads(self.path.read_text(encoding="utf-8"))

    # --- the file ------------------------------------------------------

    def test_it_is_a_version_one_registry(self) -> None:
        self.assertIsInstance(self.data, dict)
        self.assertEqual(self.data["version"], 1)
        self.assertIsInstance(self.data["hooks"], dict)

    def test_it_registers_those_keys_and_nothing_else(self) -> None:
        self.assertEqual(sorted(self.data["hooks"]), sorted(FLAT_KEYS + NESTED_KEYS))

    # --- the six shared events ----------------------------------------

    def test_every_shared_event_is_one_flat_copilot_cli_entry(self) -> None:
        for key in FLAT_KEYS:
            with self.subTest(event=key):
                entries = self.data["hooks"][key]
                self.assertIsInstance(entries, list)
                self.assertEqual(len(entries), 1)
                entry = entries[0]
                self.assertEqual(entry["type"], "command")
                self.assertTrue(entry["bash"].strip(), "empty bash command line")
                self.assertTrue(entry["powershell"].strip(), "empty powershell command line")
                self.assertIsInstance(entry["timeoutSec"], int)
                self.assertNotIsInstance(entry["timeoutSec"], bool)

    def test_no_flat_entry_carries_a_claude_key(self) -> None:
        """The exact shape the Copilot CLI engine drops, item by item."""
        for key in FLAT_KEYS:
            entry = self.data["hooks"][key][0]
            for name in CLAUDE_ENTRY_KEYS:
                self.assertNotIn(name, entry, "%s entry carries %s" % (key, name))

    def test_each_flat_entry_runs_the_right_wrapper(self) -> None:
        for key in FLAT_KEYS:
            with self.subTest(event=key):
                entry = self.data["hooks"][key][0]
                self.assertIn("kaios.sh", entry["bash"])
                self.assertIn("kaios.ps1", entry["powershell"])
                self.assertTrue(entry["bash"].endswith(" " + key))
                self.assertTrue(entry["powershell"].endswith(" " + key))

    # --- the two PascalCase-only events -------------------------------

    def test_the_other_two_use_the_claude_nested_shape(self) -> None:
        for key in NESTED_KEYS:
            with self.subTest(event=key):
                entries = self.data["hooks"][key]
                self.assertIsInstance(entries, list)
                self.assertEqual(len(entries), 1)
                nested = entries[0]["hooks"]
                self.assertIsInstance(nested, list)
                self.assertEqual(len(nested), 1)
                inner = nested[0]
                self.assertEqual(inner["type"], "command")
                self.assertTrue(inner["command"].strip())
                self.assertIsInstance(inner["timeout"], int)
                self.assertNotIsInstance(inner["timeout"], bool)
                self.assertIn("kaios.ps1", inner["command"])
                self.assertTrue(inner["command"].endswith(" " + key))

    def test_no_event_is_registered_under_two_names(self) -> None:
        """Two spellings of one event would fire its hooks twice in one engine."""
        canonical = [events_mod.canonical(key) for key in self.data["hooks"]]
        self.assertEqual(len(canonical), len(set(canonical)), canonical)

    # --- what the package makes of it ---------------------------------

    def test_the_package_reads_all_eight_events_from_it(self) -> None:
        found = events_mod.read_registry(self.path)
        self.assertEqual(list(found), list(events_mod.EVENTS))

    def test_the_wrapper_arguments_canonicalize(self) -> None:
        """Whatever name a wrapper is handed has to reach a real event."""
        for key, entries in self.data["hooks"].items():
            argument = key
            self.assertEqual(events_mod.canonical(argument), events_mod.canonical(key))
            self.assertIsNotNone(events_mod.canonical(argument), "%s dispatches nothing" % key)
            self.assertTrue(entries)


if __name__ == "__main__":
    unittest.main()
