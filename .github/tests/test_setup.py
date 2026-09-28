"""ISC-35 and ISC-36: tool detection, stored choices, and rendered user files."""

import json
import os
import unittest
from pathlib import Path

from kaios import isa as isa_mod
from kaios import setup as setup_mod
from kaios.events import EVENTS, NESTED_REGISTRY_EVENTS, REGISTRY_EVENT_NAMES
from tests.support import TempHomeCase, fixtures, read, repo_root, write


def _file_argument(command_line: str) -> str:
    """The path a ``powershell … -File <path> <Event>`` line runs."""
    return command_line.split(" -File ")[1].rsplit(" ", 1)[0]


class DetectTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.report = setup_mod.detect(self.paths)

    def test_detect_never_raises_and_reports_every_tool(self) -> None:
        for name in ("python", "git", "gh", "databricks", "code", "powershell"):
            self.assertIn(name, self.report["tools"])
            entry = self.report["tools"][name]
            self.assertIn("found", entry)
            self.assertIn("version", entry)
            self.assertIn("path", entry)
            self.assertIsInstance(entry["found"], bool)

    def test_python_is_always_found_and_supported(self) -> None:
        python = self.report["tools"]["python"]
        self.assertTrue(python["found"])
        self.assertTrue(python["supported"])
        self.assertTrue(python["version"])

    def test_a_missing_tool_is_reported_not_fatal(self) -> None:
        self.assertIsInstance(self.report["missing"], list)
        for name in self.report["missing"]:
            self.assertFalse(self.report["tools"][name]["found"])
            self.assertIsNone(self.report["tools"][name]["version"])

    def test_probe_of_a_nonexistent_binary_is_clean(self) -> None:
        entry = setup_mod.probe(["kaios-no-such-binary-anywhere", "--version"])
        self.assertFalse(entry["found"])
        self.assertIsNone(entry["version"])
        self.assertEqual(entry["reason"], "not on PATH")

    def test_mcp_and_copilot_surfaces_are_reported(self) -> None:
        self.assertIn("present", self.report["mcp_json"])
        self.assertIn("servers", self.report["mcp_json"])
        copilot = self.report["copilot_dirs"]
        for name in setup_mod.COPILOT_DIRS:
            self.assertIn(name, copilot)
            self.assertIsInstance(copilot[name], bool)

    def test_mcp_servers_are_read_from_a_repo_config(self) -> None:
        repo = self.fake_repo()
        vscode = repo / ".vscode"
        vscode.mkdir(parents=True, exist_ok=True)
        (vscode / "mcp.json").write_text(
            json.dumps({"servers": {"github": {"type": "http"}, "other": {}}}), encoding="utf-8"
        )
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        report = setup_mod.detect(paths)
        self.assertTrue(report["mcp_json"]["present"])
        self.assertEqual(report["mcp_json"]["servers"], ["github", "other"])

    def test_a_broken_mcp_config_is_reported_not_raised(self) -> None:
        repo = self.fake_repo("broken")
        vscode = repo / ".vscode"
        vscode.mkdir(parents=True, exist_ok=True)
        (vscode / "mcp.json").write_text("{not json", encoding="utf-8")
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        report = setup_mod.detect(paths)
        self.assertTrue(report["mcp_json"]["present"])
        self.assertIn("error", report["mcp_json"])


class ConfigTests(TempHomeCase):
    def test_write_config_from_a_json_string(self) -> None:
        stored = setup_mod.write_config('{"user": {"name": "Team Member"}}', paths=self.paths)
        self.assertEqual(stored["user"]["name"], "Team Member")
        self.assertTrue(stored["installed_at"])
        self.assertIn("optional", stored)
        self.assertTrue(self.paths.config_file.is_file())

    def test_write_config_from_a_file(self) -> None:
        stored = setup_mod.write_config(fixtures() / "setup-answers.json", paths=self.paths)
        self.assertEqual(stored["user"]["team"], "Platform")
        self.assertEqual(len(stored["projects"]), 2)

    def test_write_config_merges_without_dropping_keys(self) -> None:
        setup_mod.write_config('{"optional": {"mcp": {"github": true}}}', paths=self.paths)
        stored = setup_mod.write_config('{"optional": {"mcp": {"databricks": true}}}', paths=self.paths)
        self.assertTrue(stored["optional"]["mcp"]["github"])
        self.assertTrue(stored["optional"]["mcp"]["databricks"])
        self.assertIn("databricks_cli", stored["optional"])

    def test_write_config_keeps_the_first_install_stamp(self) -> None:
        first = setup_mod.write_config("{}", paths=self.paths)
        second = setup_mod.write_config('{"user": {"role": "engineer"}}', paths=self.paths)
        self.assertEqual(first["installed_at"], second["installed_at"])

    def test_a_non_object_config_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            setup_mod.write_config("[1, 2, 3]", paths=self.paths)

    def test_stack_and_aliases_accept_comma_strings(self) -> None:
        stored = setup_mod.write_config(
            '{"projects": [{"name": "A", "stack": "Python, SQL", "aliases": "a, the a"}]}',
            paths=self.paths,
        )
        project = stored["projects"][0]
        self.assertEqual(project["stack"], ["Python", "SQL"])
        self.assertEqual(project["aliases"], ["a", "the a"])

    def test_load_config_on_an_empty_home_returns_the_skeleton(self) -> None:
        config = setup_mod.load_config(self.paths)
        self.assertEqual(config["projects"], [])
        self.assertFalse(config["optional"]["mcp"]["github"])


class RenderTests(TempHomeCase):
    def setUp(self) -> None:
        super().setUp()
        self.result = setup_mod.render(fixtures() / "setup-answers.json", paths=self.paths)

    def test_profile_is_rendered_with_no_placeholders_left(self) -> None:
        self.assertTrue(self.paths.profile.is_file())
        body = read(self.paths.profile)
        self.assertNotIn("{{", body)
        self.assertIn("| role | Data platform engineer |", body)
        self.assertIn("| team | Platform |", body)
        self.assertIn("- PowerShell", body)
        self.assertIn("convention: kaios-freshness-v1", body)

    def test_profile_lists_only_linked_integrations(self) -> None:
        body = read(self.paths.profile)
        self.assertIn("MCP servers enabled: github", body)
        self.assertIn("profile work", body)
        self.assertIn("TRACKER_API_TOKEN", body)

    def test_projects_table_and_aliases(self) -> None:
        body = read(self.paths.projects)
        self.assertNotIn("{{", body)
        self.assertIn("| Ingest Pipeline |", body)
        self.assertIn("| Report Tool |", body)
        self.assertIn("| the pipeline | Ingest Pipeline |", body)
        self.assertIn("| reports | Report Tool |", body)

    def test_per_project_instructions_carry_an_applyto_glob(self) -> None:
        target = self.paths.projects_dir / "ingest-pipeline.instructions.md"
        self.assertTrue(target.is_file())
        body = read(target)
        self.assertNotIn("{{", body)
        self.assertTrue(body.startswith("---"))
        self.assertIn("applyTo:", body)
        self.assertIn("ingest-pipeline", body)
        self.assertIn("databricks bundle deploy -t dev", body)
        self.assertIn("Never deploy to prod without being asked.", body)

    def test_every_project_gets_an_isa_seed_that_checks_clean(self) -> None:
        for slug in ("ingest-pipeline", "report-tool"):
            target = self.paths.projects_dir / slug / "ISA.md"
            self.assertTrue(target.is_file(), "%s has no ISA seed" % slug)
            parsed = isa_mod.parse(target)
            self.assertEqual(parsed.frontmatter["slug"], slug)
            self.assertEqual([f.to_dict() for f in isa_mod.errors(isa_mod.check(parsed))], [])
        seeded = read(self.paths.projects_dir / "ingest-pipeline" / "ISA.md")
        self.assertIn("row-count check", seeded)

    def test_mcp_keeps_only_the_flagged_servers(self) -> None:
        self.assertTrue(self.paths.mcp_json.is_file())
        data = json.loads(read(self.paths.mcp_json))
        self.assertEqual(sorted(data["servers"]), ["github"])
        self.assertEqual(data["servers"]["github"]["type"], "http")
        self.assertIn("githubcopilot.com", data["servers"]["github"]["url"])
        self.assertNotIn("x-kaios", data)
        self.assertNotIn("x-kaios", data["servers"]["github"])
        self.assertEqual(self.result["mcp_servers"], ["github"])

    def test_mcp_can_include_the_databricks_placeholder(self) -> None:
        setup_mod.write_config('{"optional": {"mcp": {"databricks": true}}}', paths=self.paths)
        setup_mod.render(paths=self.paths)
        data = json.loads(read(self.paths.mcp_json))
        self.assertEqual(data["servers"]["databricks"]["command"], "databricks")
        self.assertEqual(data["servers"]["databricks"]["args"], ["experimental", "mcp"])

    def test_hook_registry_covers_every_event_with_absolute_paths(self) -> None:
        self.assertTrue(self.paths.hooks_json.is_file())
        data = json.loads(read(self.paths.hooks_json))
        self.assertEqual(
            sorted(data["hooks"]),
            sorted(REGISTRY_EVENT_NAMES[event] for event in EVENTS),
        )
        self.assertNotIn("x-kaios", data)
        for key, entries in data["hooks"].items():
            self.assertEqual(len(entries), 1)
            entry = entries[0]
            if key in NESTED_REGISTRY_EVENTS:
                # A Claude nested entry: the VS Code engine reads it natively and
                # the Copilot CLI engine reads it under Claude semantics.
                nested = entry["hooks"]
                self.assertEqual(len(nested), 1)
                self.assertEqual(nested[0]["type"], "command")
                self.assertTrue(nested[0]["command"].endswith(" %s" % key))
                self.assertIn("kaios.ps1", nested[0]["command"])
                self.assertTrue(os.path.isabs(_file_argument(nested[0]["command"])))
                continue
            self.assertEqual(entry["type"], "command")
            self.assertTrue(entry["powershell"].endswith(" %s" % key))
            self.assertIn("kaios.ps1", entry["powershell"])
            self.assertTrue(os.path.isabs(_file_argument(entry["powershell"])))
            self.assertTrue(entry["bash"].endswith(" %s" % key))
            self.assertIn("kaios.sh", entry["bash"])
            self.assertTrue(os.path.isabs(entry["bash"].split(" ")[1]))
            self.assertEqual(entry["timeoutSec"], 20)
            self.assertTrue(os.path.isabs(entry["env"]["PYTHONPATH"]))
            self.assertTrue(os.path.isabs(entry["env"]["KAIOS_HOME"]))
        self.assertTrue(os.path.isabs(data["cwd"]))
        self.assertTrue(self.result["hooks"]["absolute"])
        self.assertEqual(self.result["hooks"]["events"], list(EVENTS))

    def test_render_reports_every_file_it_wrote(self) -> None:
        written = self.result["written"]
        self.assertIn(str(self.paths.profile), written)
        self.assertIn(str(self.paths.projects), written)
        self.assertIn(str(self.paths.mcp_json), written)
        self.assertIn(str(self.paths.hooks_json), written)
        self.assertEqual(len(self.result["projects"]), 2)

    def test_dry_run_writes_nothing(self) -> None:
        import shutil

        shutil.rmtree(self.paths.user_dir)
        result = setup_mod.render(fixtures() / "setup-answers.json", paths=self.paths, write=False)
        self.assertEqual(result["written"], [])
        self.assertFalse(self.paths.profile.exists())

    def test_render_with_no_answers_still_produces_files(self) -> None:
        home = self.scratch / "bare"
        paths = type(self.paths)(home=home, repo=None, cwd=self.scratch).ensure()
        result = setup_mod.render(paths=paths)
        self.assertTrue(paths.profile.is_file())
        self.assertIn("(none yet)", read(paths.projects))
        self.assertEqual(json.loads(read(paths.mcp_json))["servers"], {})
        self.assertEqual(result["projects"], [])


class HookRenderTests(TempHomeCase):
    def test_windows_paths_stay_valid_json(self) -> None:
        text, meta = setup_mod.render_hooks(
            self.paths,
            python="C:\\tools\\python\\python.exe",
            wrapper="D:\\work\\repo\\hooks\\kaios.ps1",
            shell_wrapper="D:\\work\\repo\\hooks\\kaios.sh",
        )
        data = json.loads(text)
        entry = data["hooks"]["sessionStart"][0]
        self.assertIn("D:\\work\\repo\\hooks\\kaios.ps1", entry["powershell"])
        self.assertIn("D:\\work\\repo\\hooks\\kaios.sh", entry["bash"])
        nested = data["hooks"]["PreCompact"][0]["hooks"][0]
        self.assertIn("D:\\work\\repo\\hooks\\kaios.ps1", nested["command"])
        self.assertEqual(meta["python"], "C:\\tools\\python\\python.exe")

    def test_the_rendered_pythonpath_is_a_real_import_root(self) -> None:
        """isabs is not enough: the path has to be where ``kaios`` actually is.

        The package lives at ``.github/kaios``, so the import root is the
        framework directory, not the checkout root. A registry naming the checkout
        root would render clean, look absolute, and import nothing.
        """
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        text, meta = setup_mod.render_hooks(paths)
        framework = Path(meta["framework"])
        self.assertEqual(framework, repo_root() / ".github")
        self.assertTrue((framework / "kaios" / "__init__.py").is_file())
        data = json.loads(text)
        for key, entries in data["hooks"].items():
            for entry in entries:
                if "hooks" in entry:
                    continue
                root = Path(entry["env"]["PYTHONPATH"])
                with self.subTest(event=key):
                    self.assertTrue(
                        (root / "kaios" / "__init__.py").is_file(),
                        "%s renders PYTHONPATH=%s, which has no kaios package" % (key, root),
                    )

    def test_a_pre_move_checkout_still_renders_its_own_import_root(self) -> None:
        legacy = self.fake_repo("pre-move")
        (legacy / "kaios").mkdir(parents=True, exist_ok=True)
        write(legacy / "kaios" / "__init__.py", "")
        self.assertEqual(setup_mod.framework_dir(legacy), legacy)

    def test_repo_wrapper_path_is_reported(self) -> None:
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        _, meta = setup_mod.render_hooks(paths)
        self.assertTrue(meta["wrapper"].endswith(setup_mod.WRAPPER_RELATIVE.replace("/", os.sep)))
        self.assertTrue(
            meta["shell_wrapper"].endswith(setup_mod.SHELL_WRAPPER_RELATIVE.replace("/", os.sep))
        )
        self.assertTrue(meta["wrapper_exists"])
        self.assertTrue(meta["shell_wrapper_exists"])
        self.assertEqual(sorted(meta["events"]), sorted(EVENTS))
        self.assertEqual(meta["missing_events"], [])

    def test_the_checked_in_registry_is_the_source_of_truth(self) -> None:
        """Key spelling and entry shape survive rendering; only paths change.

        Both are load-bearing. The spelling decides which of Copilot's two hook
        engines recognises the event, and the shape decides whether that engine
        can parse the entry at all, so a render that normalised either would
        reintroduce the bug this file is the fixture for.
        """
        paths = type(self.paths)(home=self.home, repo=repo_root(), cwd=repo_root())
        source = setup_mod.repo_hooks_registry(paths)
        self.assertIsNotNone(source, "this checkout has no .github/hooks/kaios.json")
        original = json.loads(source.read_text(encoding="utf-8"))
        text, meta = setup_mod.render_hooks(paths)
        rendered = json.loads(text)
        self.assertEqual(meta["source"], str(source))
        self.assertEqual(rendered["version"], original.get("version", 1))
        self.assertEqual(sorted(rendered["hooks"]), sorted(original["hooks"]))
        self.assertEqual(meta["events"], list(EVENTS))
        for key, entries in original["hooks"].items():
            self.assertEqual(len(rendered["hooks"][key]), len(entries))
            for before, after in zip(entries, rendered["hooks"][key]):
                self.assertEqual(sorted(before), sorted(k for k in after if k != "env"))
                if "hooks" in before:
                    self.assertEqual(after["hooks"][0]["type"], before["hooks"][0]["type"])
                    self.assertEqual(after["hooks"][0]["timeout"], before["hooks"][0]["timeout"])
                    self.assertIn(str(meta["wrapper"]), after["hooks"][0]["command"])
                    self.assertTrue(after["hooks"][0]["command"].endswith(" %s" % key))
                    self.assertNotIn("env", after)
                    continue
                self.assertEqual(after["type"], before["type"])
                self.assertEqual(after["timeoutSec"], before["timeoutSec"])
                self.assertIn(str(meta["wrapper"]), after["powershell"])
                self.assertIn(str(meta["shell_wrapper"]), after["bash"])
                self.assertTrue(after["powershell"].endswith(" %s" % key))
                self.assertTrue(after["bash"].endswith(" %s" % key))

    def test_the_template_is_the_fallback_with_no_checkout(self) -> None:
        text, meta = setup_mod.render_hooks(self.paths)
        data = json.loads(text)
        self.assertEqual(meta["source"], "template")
        self.assertEqual(
            sorted(data["hooks"]),
            sorted(REGISTRY_EVENT_NAMES[event] for event in EVENTS),
        )
        self.assertEqual(meta["events"], list(EVENTS))
        for event in NESTED_REGISTRY_EVENTS:
            self.assertIn("hooks", data["hooks"][event][0])
        self.assertIn("bash", data["hooks"]["preToolUse"][0])

    def test_a_relative_shell_path_becomes_absolute(self) -> None:
        self.assertEqual(
            setup_mod._absolute_bash("sh .github/hooks/kaios.sh preToolUse", Path("/abs/kaios.sh")),
            "sh /abs/kaios.sh preToolUse",
        )
        self.assertEqual(
            setup_mod._absolute_bash("kaios.sh preToolUse", Path("/abs/kaios.sh")),
            "kaios.sh preToolUse",
        )

    def test_a_registry_with_no_hooks_object_is_refused(self) -> None:
        repo = self.fake_repo()
        target = repo / setup_mod.HOOKS_REGISTRY_RELATIVE
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('{"version": 1}', encoding="utf-8")
        paths = type(self.paths)(home=self.home, repo=repo, cwd=repo)
        with self.assertRaises(ValueError):
            setup_mod.render_hooks(paths)

    def test_a_non_python_command_is_left_alone(self) -> None:
        self.assertEqual(
            setup_mod._absolute_command("pwsh -File thing.ps1", "/abs/python"),
            "pwsh -File thing.ps1",
        )
        self.assertEqual(
            setup_mod._absolute_command("python3 -m kaios.hooks Stop", "/abs/python"),
            "/abs/python -m kaios.hooks Stop",
        )


class InterviewFieldTests(TempHomeCase):
    """The fields the setup skill captures must reach the rendered files."""

    ANSWERS = {
        "optional": {"apis": {"tracker": {"env_var": "TRACKER_TOKEN", "purpose": "read ticket titles"}}},
        "projects": [
            {
                "name": "Nightly Export",
                "path": "work/nightly-export",
                "purpose": "Ship a dated extract to the finance share every night.",
                "done_means": "The dated file exists, the count matches, and a failure alerts the owner.",
                "pain_points": ["Reruns duplicated a day's file.", "Schema drift reads as a count mismatch."],
            }
        ],
    }

    def setUp(self) -> None:
        super().setUp()
        setup_mod.render(self.ANSWERS, paths=self.paths)
        self.instructions = read(self.paths.projects_dir / "nightly-export.instructions.md")

    def test_purpose_renders_as_prose(self) -> None:
        self.assertIn("Ship a dated extract to the finance share every night.", self.instructions)

    def test_a_single_sentence_stays_one_bullet(self) -> None:
        self.assertIn(
            "- The dated file exists, the count matches, and a failure alerts the owner.",
            self.instructions,
        )
        self.assertNotIn("- the count matches", self.instructions)

    def test_pain_points_render_one_bullet_each(self) -> None:
        self.assertIn("- Reruns duplicated a day's file.", self.instructions)
        self.assertIn("- Schema drift reads as a count mismatch.", self.instructions)

    def test_an_api_purpose_reaches_the_profile_without_the_key(self) -> None:
        profile = read(self.paths.profile)
        self.assertIn("tracker via TRACKER_TOKEN for read ticket titles", profile)

    def test_the_isa_seed_goal_comes_from_the_interview(self) -> None:
        seeded = read(self.paths.projects_dir / "nightly-export" / "ISA.md")
        self.assertIn("The dated file exists, the count matches", seeded)
        self.assertNotIn("State what done looks like", seeded)


class ProjectGoalTests(unittest.TestCase):
    def test_an_explicit_goal_wins(self) -> None:
        project = {"name": "A", "goal": "G.", "done_means": "D.", "purpose": "P."}
        self.assertEqual(setup_mod.project_goal(project), "G.")

    def test_done_means_is_the_next_choice(self) -> None:
        self.assertEqual(setup_mod.project_goal({"name": "A", "done_means": "D.", "purpose": "P."}), "D.")

    def test_purpose_is_the_last_stated_choice(self) -> None:
        self.assertEqual(setup_mod.project_goal({"name": "A", "purpose": "P."}), "P.")

    def test_a_bare_project_gets_a_prompt_to_articulate_done(self) -> None:
        self.assertIn("falsifiable claims", setup_mod.project_goal({"name": "A"}))


class GlobTests(unittest.TestCase):
    def test_glob_comes_from_the_path_tail(self) -> None:
        self.assertEqual(setup_mod.project_glob({"name": "A", "path": "work/ingest-pipeline"}), "**/ingest-pipeline/**")

    def test_an_explicit_glob_wins(self) -> None:
        self.assertEqual(setup_mod.project_glob({"name": "A", "glob": "src/**/*.py"}), "src/**/*.py")

    def test_a_project_with_no_path_falls_back_to_its_slug(self) -> None:
        self.assertEqual(setup_mod.project_glob({"name": "Report Tool"}), "**/report-tool/**")


if __name__ == "__main__":
    unittest.main()
