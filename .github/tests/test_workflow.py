"""Tests for the create-workflow skill tool (ISC-39).

Every case drives the tool the way an agent does: as a subprocess from the
repository root, with a temporary KAIOS_HOME and a temporary output tree, so no
test can write into the repo or into the developer's real state file.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# The framework lives under .github, so this file is two levels below the
# checkout root: <repo>/.github/tests/<this file>.
REPO = Path(__file__).resolve().parents[2]
SKILL_DIR = REPO / ".github" / "skills" / "CreateWorkflow"
TOOL = SKILL_DIR / "workflow_tool.py"
REFS = SKILL_DIR / "references"


def load_tool_module():
    """Import the tool by path so the YAML pair can be exercised directly.

    Bytecode writing is off for the load: the skill directory is copied to the
    user level at install time and should not carry a cache directory.
    """
    import importlib.util

    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location("kaios_workflow_tool", str(TOOL))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.dont_write_bytecode = previous


class WorkflowToolCase(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="kaios-workflow-"))
        self.home = self.work / "home"
        self.out = self.work / "repo"
        self.home.mkdir(parents=True)
        self.out.mkdir(parents=True)
        self.env = os.environ.copy()
        self.env["KAIOS_HOME"] = str(self.home)

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    # -- helpers --------------------------------------------------------
    def run_tool(self, *args):
        proc = subprocess.run(
            [sys.executable, str(TOOL)] + [str(a) for a in args],
            cwd=str(REPO),
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )
        return proc

    def run_json(self, *args):
        proc = self.run_tool(*args)
        try:
            payload = json.loads(proc.stdout)
        except ValueError:
            self.fail("expected JSON on stdout, got: %r / %r" % (proc.stdout, proc.stderr))
        return proc.returncode, payload

    def seed(self, relative, text):
        path = self.out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return path

    def scaffold(self, answers_name, kind=None):
        args = ["scaffold", "--answers", REFS / answers_name, "--out", self.out]
        if kind:
            args.extend(["--kind", kind])
        code, payload = self.run_json(*args)
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ok"], payload)
        return payload

    def codes(self, payload):
        return sorted(f["code"] for f in payload.get("findings", []))


class TestToolSurface(WorkflowToolCase):
    def test_help_exits_zero(self):
        proc = self.run_tool("--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("scaffold", proc.stdout)

    def test_no_command_is_a_usage_error(self):
        proc = self.run_tool()
        self.assertEqual(proc.returncode, 2, proc.stdout)

    def test_kinds_names_three_and_a_default(self):
        code, payload = self.run_json("kinds")
        self.assertEqual(code, 0)
        self.assertEqual(
            sorted(k["kind"] for k in payload["kinds"]), ["actions", "agent", "databricks"]
        )
        self.assertEqual(payload["default_kind"], "agent")

    def test_question_banks_stay_within_ten(self):
        for kind in ("agent", "actions", "databricks"):
            code, payload = self.run_json("questions", "--kind", kind)
            self.assertEqual(code, 0, payload)
            self.assertLessEqual(payload["count"], 10, kind)
            self.assertGreaterEqual(payload["count"], 1, kind)
            for question in payload["questions"]:
                self.assertTrue(question["ask"].strip(), kind)
                self.assertTrue(question["why"].strip(), kind)


class TestScaffoldAgentWorkflow(WorkflowToolCase):
    def test_scaffold_then_validate(self):
        payload = self.scaffold("answers-example-agent.json")
        spec_path = self.out / ".github" / "skills" / "ReleaseReview" / "workflow.json"
        skill_path = self.out / ".github" / "skills" / "ReleaseReview" / "SKILL.md"
        agent_path = self.out / ".github" / "agents" / "ReleaseReview.agent.md"
        for path in (spec_path, skill_path, agent_path):
            self.assertTrue(path.exists(), "missing %s" % path)
            self.assertIn(str(path), payload["written"])

        code, result = self.run_json("validate", spec_path)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["kind"], "agent")
        self.assertEqual(result["findings"], [])

    def test_generated_artifacts_carry_the_contract(self):
        self.scaffold("answers-example-agent.json")
        base = self.out / ".github" / "skills" / "ReleaseReview"
        spec = json.loads((base / "workflow.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["kind"], "agent")
        self.assertEqual(spec["state_file"], "$KAIOS_HOME/MEMORY/STATE/workflows.json")
        self.assertTrue(any(s["gate"] == "evidence" for s in spec["stages"]))
        self.assertTrue(spec["anti_claims"])

        skill = (base / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: release-review", skill)
        self.assertIn("USE WHEN", skill)
        self.assertIn("NOT FOR", skill)
        for stage in spec["stages"]:
            self.assertIn(stage["id"], skill)

        agent = (self.out / ".github" / "agents" / "ReleaseReview.agent.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("# kaios-role:", agent)
        self.assertIn("agents:", agent)
        self.assertIn("handoffs:", agent)

    def test_defaults_are_reported_not_hidden(self):
        thin = self.work / "thin.json"
        answers = {
            "kind": "agent",
            "name": "Thin",
            "goal": "Prove the tool fills gaps out loud.",
            "stages": [{"title": "Only stage", "agent": "Builder"}],
        }
        thin.write_text(json.dumps(answers), encoding="utf-8")
        code, payload = self.run_json("scaffold", "--answers", thin, "--out", self.out)
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["notes"], "the scaffold filled gaps without saying so")
        code, result = self.run_json(
            "validate", self.out / ".github" / "skills" / "Thin" / "workflow.json"
        )
        self.assertEqual(code, 0, result)

    def test_broken_spec_is_rejected(self):
        broken = {
            "name": "Broken",
            "version": "1.0.0",
            "goal": "cycle and no criteria",
            "kind": "agent",
            "state_file": "$KAIOS_HOME/MEMORY/STATE/workflows.json",
            "stages": [
                {
                    "id": "a",
                    "title": "A",
                    "agent": "Builder",
                    "role": "high",
                    "input": "x",
                    "output": "y",
                    "done_criteria": [],
                    "gate": "auto",
                    "after": ["b"],
                },
                {
                    "id": "b",
                    "title": "B",
                    "agent": "Auditor",
                    "role": "cross",
                    "input": "y",
                    "output": "z",
                    "done_criteria": ["Findings name file and line."],
                    "gate": "evidence",
                    "after": ["a"],
                },
            ],
            "anti_claims": ["No stage grades its own work."],
        }
        path = self.seed("broken.workflow.json", json.dumps(broken, indent=2))
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertFalse(payload["ok"])
        self.assertIn("no-done-criteria", self.codes(payload))
        self.assertIn("cyclic-after", self.codes(payload))

    def test_spec_without_evidence_gate_or_anti_claims_is_rejected(self):
        spec = {
            "name": "Loose",
            "version": "1.0.0",
            "goal": "no gate, no anti-claims",
            "kind": "agent",
            "state_file": "$KAIOS_HOME/MEMORY/STATE/workflows.json",
            "stages": [
                {
                    "id": "only",
                    "title": "Only",
                    "agent": "Builder",
                    "role": "high",
                    "input": "x",
                    "output": "y",
                    "done_criteria": ["Something observable happened."],
                    "gate": "auto",
                    "after": [],
                }
            ],
            "anti_claims": [],
        }
        path = self.seed("loose.workflow.json", json.dumps(spec, indent=2))
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertIn("no-evidence-gate", self.codes(payload))
        self.assertIn("no-anti-claims", self.codes(payload))

    def test_render_md_prints_the_stage_table(self):
        self.scaffold("answers-example-agent.json")
        spec_path = self.out / ".github" / "skills" / "ReleaseReview" / "workflow.json"
        proc = self.run_tool("render", "--spec", spec_path, "--md")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("| # | stage |", proc.stdout)
        for stage_id in ("plan", "build", "review", "verify"):
            self.assertIn("`%s`" % stage_id, proc.stdout)


class TestScaffoldActionsWorkflow(WorkflowToolCase):
    def test_scaffold_then_validate(self):
        payload = self.scaffold("answers-example-actions.json")
        path = self.out / ".github" / "workflows" / "python-tests.yml"
        self.assertTrue(path.exists())
        self.assertIn(str(path), payload["written"])
        code, result = self.run_json("validate", path)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["kind"], "actions")

    def test_each_template_scaffolds_and_validates(self):
        cases = [
            {"kind": "actions", "name": "tests-ci", "template": "python-tests"},
            {
                "kind": "actions",
                "name": "bundle-deploy",
                "template": "databricks-bundle-deploy",
                "target": "prod",
            },
            {
                "kind": "actions",
                "name": "nightly",
                "template": "scheduled-job",
                "cron": "0 7 * * 1-5",
                "command": "python -m unittest discover -s tests",
            },
        ]
        for answers in cases:
            answers_path = self.work / ("%s.json" % answers["name"])
            answers_path.write_text(json.dumps(answers), encoding="utf-8")
            code, payload = self.run_json("scaffold", "--answers", answers_path, "--out", self.out)
            self.assertEqual(code, 0, payload)
            target = self.out / ".github" / "workflows" / ("%s.yml" % answers["name"])
            self.assertTrue(target.exists(), "missing %s" % target)
            code, result = self.run_json("validate", target)
            self.assertEqual(code, 0, result)

    def test_step_without_uses_or_run_is_rejected(self):
        path = self.seed(
            ".github/workflows/bad.yml",
            "name: Bad workflow\n"
            "on:\n"
            "  push:\n"
            "    branches:\n"
            "      - main\n"
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - name: Does nothing\n"
            "      - name: Runs something\n"
            "        run: python -m unittest discover -s tests\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["kind"], "actions")
        self.assertIn("step-without-action", self.codes(payload))

    def test_missing_top_level_keys_are_rejected(self):
        path = self.seed(
            ".github/workflows/headless.yml",
            "jobs:\n"
            "  tests:\n"
            "    steps:\n"
            "      - run: python -m unittest discover -s tests\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        codes = self.codes(payload)
        self.assertIn("missing-name", codes)
        self.assertIn("missing-on", codes)
        self.assertIn("missing-runs-on", codes)

    def test_secret_in_a_run_line_is_rejected(self):
        path = self.seed(
            ".github/workflows/leaky.yml",
            "name: Leaky\n"
            "on:\n"
            "  workflow_dispatch: {}\n"
            "jobs:\n"
            "  deploy:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            '      - run: echo "${{ secrets.API_TOKEN }}"\n',
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertIn("secret-in-run", self.codes(payload))

    def test_prod_deploy_without_environment_is_rejected(self):
        path = self.seed(
            ".github/workflows/unprotected.yml",
            "name: Unprotected deploy\n"
            "on:\n"
            "  workflow_dispatch: {}\n"
            "jobs:\n"
            "  deploy:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: databricks/setup-cli@main\n"
            "      - run: databricks bundle deploy -t prod\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertIn("unprotected-prod-deploy", self.codes(payload))


class TestScaffoldDatabricksWorkflow(WorkflowToolCase):
    def test_scaffold_then_validate(self):
        payload = self.scaffold("answers-example-databricks.json")
        job = self.out / "resources" / "nightly_ingest.job.yml"
        root = self.out / "databricks.yml"
        self.assertTrue(job.exists())
        self.assertTrue(root.exists())
        self.assertIn(str(job), payload["written"])

        code, result = self.run_json("validate", job)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["kind"], "databricks")

        code, result = self.run_json("validate", root)
        self.assertEqual(code, 0, result)
        self.assertEqual(result["kind"], "databricks-bundle")

    def test_existing_bundle_root_is_left_alone(self):
        marker = "bundle:\n  name: already_here\ntargets:\n  prod:\n    mode: production\n"
        self.seed("databricks.yml", marker)
        payload = self.scaffold("answers-example-databricks.json")
        self.assertEqual(
            (self.out / "databricks.yml").read_text(encoding="utf-8"),
            marker,
            "the scaffold overwrote an existing bundle root",
        )
        self.assertNotIn(str(self.out / "databricks.yml"), payload["written"])

    def test_duplicate_task_key_is_rejected(self):
        self.seed(
            "databricks.yml",
            "bundle:\n  name: pipelines\ntargets:\n  dev:\n    mode: development\n"
            "  prod:\n    mode: production\n",
        )
        path = self.seed(
            "resources/dupe.job.yml",
            "resources:\n"
            "  jobs:\n"
            "    dupe:\n"
            "      name: Dupe\n"
            "      tasks:\n"
            "        - task_key: same\n"
            "          notebook_task:\n"
            "            notebook_path: ../notebooks/a.py\n"
            "        - task_key: same\n"
            "          notebook_task:\n"
            "            notebook_path: ../notebooks/b.py\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["kind"], "databricks")
        self.assertIn("duplicate-task-key", self.codes(payload))

    def test_task_graph_and_type_problems_are_rejected(self):
        self.seed(
            "databricks.yml",
            "bundle:\n  name: pipelines\ntargets:\n  dev:\n    mode: development\n"
            "  prod:\n    mode: production\n",
        )
        path = self.seed(
            "resources/tangled.job.yml",
            "resources:\n"
            "  jobs:\n"
            "    tangled:\n"
            "      name: Tangled\n"
            "      tasks:\n"
            "        - task_key: first\n"
            "          notebook_task:\n"
            "            notebook_path: ../notebooks/a.py\n"
            "          sql_task:\n"
            "            warehouse_id: w1\n"
            "          depends_on:\n"
            "            - task_key: second\n"
            "        - task_key: second\n"
            "          notebook_task:\n"
            "            notebook_path: ../notebooks/b.py\n"
            "          depends_on:\n"
            "            - task_key: first\n"
            "        - task_key: third\n"
            "          depends_on:\n"
            "            - task_key: nowhere\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        codes = self.codes(payload)
        self.assertIn("many-task-types", codes)
        self.assertIn("cyclic-depends-on", codes)
        self.assertIn("unknown-depends-on", codes)
        self.assertIn("no-task-type", codes)

    def test_bundle_root_without_prod_target_is_rejected(self):
        path = self.seed(
            "databricks.yml",
            "bundle:\n  name: pipelines\ntargets:\n  dev:\n    mode: development\n    default: true\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertIn("missing-prod-target", self.codes(payload))

    def test_job_outside_a_bundle_is_rejected(self):
        path = self.seed(
            "resources/orphan.job.yml",
            "resources:\n"
            "  jobs:\n"
            "    orphan:\n"
            "      name: Orphan\n"
            "      tasks:\n"
            "        - task_key: only\n"
            "          notebook_task:\n"
            "            notebook_path: ../notebooks/a.py\n",
        )
        code, payload = self.run_json("validate", path)
        self.assertEqual(code, 1, payload)
        self.assertIn("missing-bundle-root", self.codes(payload))


class TestScaffoldGuards(WorkflowToolCase):
    def test_existing_files_are_skipped_without_force(self):
        first = self.scaffold("answers-example-actions.json")
        path = self.out / ".github" / "workflows" / "python-tests.yml"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("# edited by hand\n")
        second = self.scaffold("answers-example-actions.json")
        self.assertEqual(second["written"], [])
        self.assertIn(str(path), second["skipped"])
        self.assertIn("# edited by hand", path.read_text(encoding="utf-8"))
        self.assertIn(str(path), first["written"])

    def test_force_overwrites(self):
        self.scaffold("answers-example-actions.json")
        path = self.out / ".github" / "workflows" / "python-tests.yml"
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("# edited by hand\n")
        code, payload = self.run_json(
            "scaffold",
            "--answers",
            REFS / "answers-example-actions.json",
            "--out",
            self.out,
            "--force",
        )
        self.assertEqual(code, 0, payload)
        self.assertIn(str(path), payload["written"])
        self.assertNotIn("# edited by hand", path.read_text(encoding="utf-8"))

    def test_missing_answers_file_fails_cleanly(self):
        code, payload = self.run_json(
            "scaffold", "--answers", self.work / "nope.json", "--out", self.out
        )
        self.assertEqual(code, 1, payload)
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)

    def test_unknown_kind_is_a_usage_error(self):
        answers = self.work / "mystery.json"
        answers.write_text(json.dumps({"kind": "mystery"}), encoding="utf-8")
        code, payload = self.run_json("scaffold", "--answers", answers, "--out", self.out)
        self.assertEqual(code, 2, payload)

    def test_validate_reports_a_missing_file(self):
        code, payload = self.run_json("validate", self.out / "absent.json")
        self.assertEqual(code, 1, payload)
        self.assertIn("missing-file", self.codes(payload))


class TestRunTracking(WorkflowToolCase):
    def state_file(self):
        return self.home / "MEMORY" / "STATE" / "workflows.json"

    def test_start_and_finish_round_trip(self):
        code, payload = self.run_json("runs", "start", "--name", "ReleaseReview")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["run"]["status"], "running")
        self.assertTrue(self.state_file().exists())

        code, payload = self.run_json("runs", "finish", "--name", "ReleaseReview", "--status", "ok")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["run"]["status"], "ok")
        self.assertTrue(payload["run"]["finished"])

        code, payload = self.run_json("runs", "list")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["runs"][0]["status"], "ok")

        on_disk = json.loads(self.state_file().read_text(encoding="utf-8"))
        self.assertEqual(on_disk["runs"][0]["name"], "ReleaseReview")
        self.assertEqual(on_disk["runs"][0]["status"], "ok")
        self.assertEqual(str(self.state_file()), payload["state_file"])

    def test_failed_status_is_recorded(self):
        self.run_json("runs", "start", "--name", "Nightly")
        code, payload = self.run_json("runs", "finish", "--name", "Nightly", "--status", "failed")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["run"]["status"], "failed")

    def test_finishing_an_unknown_run_fails(self):
        code, payload = self.run_json("runs", "finish", "--name", "Ghost", "--status", "ok")
        self.assertEqual(code, 1, payload)
        self.assertFalse(payload["ok"])

    def test_runs_list_on_a_fresh_home_is_empty(self):
        code, payload = self.run_json("runs", "list")
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["runs"], [])


class TestYamlPair(unittest.TestCase):
    """The serializer and the subset parser must agree, since validation re-reads what we write."""

    @classmethod
    def setUpClass(cls):
        cls.tool = load_tool_module()

    def test_round_trip_of_the_shapes_we_emit(self):
        data = {
            "name": "Round trip",
            "on": {"schedule": [{"cron": "0 7 * * 1-5"}], "workflow_dispatch": {}},
            "jobs": {
                "tests": {
                    "runs-on": "ubuntu-latest",
                    "environment": "prod",
                    "steps": [
                        {"uses": "actions/checkout@v4"},
                        {
                            "name": "Install",
                            "if": "hashFiles('requirements.txt') != ''",
                            "run": "python -m pip install --upgrade pip\npython -m pip install -r requirements.txt\n",
                        },
                        {"name": "Empty mapping", "with": {}, "run": "true"},
                        {"name": "Empty list", "args": [], "run": "true"},
                    ],
                }
            },
            "numbers": {"int": 3, "float": 1.5, "flag": True, "off": False, "nothing": None},
            "quoted": {"version": "3.11", "interp": "${{ vars.HOST }}", "colon": "a: b"},
        }
        text = self.tool.dump_yaml(data)
        self.assertEqual(self.tool.parse_yaml(text), data)

    def test_comments_and_blank_lines_are_tolerated(self):
        text = (
            "# leading comment\n"
            "name: With comments   # trailing comment\n"
            "\n"
            "on:\n"
            "  push:\n"
            "    branches: [main, release]\n"
            "jobs:\n"
            "  tests:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - run: echo '# not a comment'\n"
        )
        parsed = self.tool.parse_yaml(text)
        self.assertEqual(parsed["name"], "With comments")
        self.assertEqual(parsed["on"]["push"]["branches"], ["main", "release"])
        self.assertEqual(parsed["jobs"]["tests"]["steps"][0]["run"], "echo '# not a comment'")

    def test_unparsable_yaml_is_reported_not_raised(self):
        with self.assertRaises(self.tool.YamlError):
            self.tool.parse_yaml("name: fine\nthis line has no colon\n")


if __name__ == "__main__":
    unittest.main()
