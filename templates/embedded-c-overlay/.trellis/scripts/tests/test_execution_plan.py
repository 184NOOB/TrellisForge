from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import execution_plan as ep
import plan as plan_cli


BASE_PLAN = {
    "schema": 2,
    "task": ".trellis/tasks/demo",
    "revision": 1,
    "status": "proposed",
    "audit": {"required": True, "file": "execution-events.jsonl"},
    "created_by": "trellis-implement",
    "goal": "demo goal",
    "constraints": {
        "forbidden_git_operations": ["commit"],
        "max_tasks": 8,
        "max_edits_per_file": 2,
        "allow_parallel_tasks": False,
    },
    "tasks": [
        {
            "id": "discover",
            "title": "read code",
            "status": "pending",
            "objective": "map symbols",
            "depends_on": [],
            "scope": {"read": ["src/**/*.c"], "write": []},
            "risk": "normal",
            "verification": {"level": "minimal", "checks": [], "required_artifacts": []},
        },
        {
            "id": "edit",
            "title": "edit code",
            "status": "pending",
            "objective": "change code",
            "depends_on": ["discover"],
            "scope": {"read": ["src/a.c"], "write": ["src/a.c"]},
            "risk": "normal",
            "verification": {"level": "minimal", "checks": ["app-build"], "required_artifacts": []},
        },
    ],
}


class ExecutionPlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".trellis" / "scripts").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.c").write_text("int main(void){return 0;}\n", encoding="utf-8")
        self.task_dir = self.root / ".trellis" / "tasks" / "demo"
        self.task_dir.mkdir(parents=True)
        (self.task_dir / "task.json").write_text(
            json.dumps({"id": "demo", "status": "in_progress"}), encoding="utf-8"
        )
        self.write_plan(copy.deepcopy(BASE_PLAN))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # -- helpers --------------------------------------------------------

    def write_plan(self, plan: dict) -> None:
        (self.task_dir / ep.PLAN_FILE).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def read_plan(self) -> dict:
        return json.loads((self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8"))

    def events(self) -> list[dict]:
        path = self.task_dir / ep.EVENTS_FILE
        if not path.is_file():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def approve(self) -> str:
        return ep.cmd_validate(self.root, self.task_dir)

    def record(self, task_id: str, command: str, *, result: str = "pass",
               exit_code: int = 0, artifact: str | None = None,
               summary: str | None = None) -> None:
        ep.cmd_record(self.root, self.task_dir, task_id, result, command,
                      exit_code, artifact, summary)

    # -- validate -------------------------------------------------------

    def test_validate_approves_and_logs(self) -> None:
        result = self.approve()
        plan = self.read_plan()
        self.assertEqual(plan["status"], "approved")
        self.assertIn("approved_fingerprint", plan)
        names = [e["event"] for e in self.events()]
        self.assertEqual(names, ["plan_created", "plan_approved"])
        self.assertTrue(result)

    def test_record_cli_does_not_overwrite_subcommand(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with patch.object(plan_cli, "get_repo_root", return_value=self.root), \
             patch.object(plan_cli, "resolve_task_dir", return_value=self.task_dir):
            exit_code = plan_cli.main([
                "--task", str(self.task_dir), "record", "discover",
                "--result", "pass", "--command", "manual-check", "--exit-code", "0",
            ])
        self.assertEqual(exit_code, 0)
        plan = self.read_plan()
        self.assertEqual(plan["tasks"][0]["verification_results"]["phase-result"]["result"], "pass")

    def test_record_requires_explicit_check_for_actual_command(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["verification"] = {
            "level": "minimal", "checks": ["inspect"],
            "required_artifacts": [],
        }
        self.write_plan(plan)
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_record(
                self.root, self.task_dir, "discover", "pass", "python inspect.py",
                0, None, None,
            )
        self.assertIn("--check", str(ctx.exception))
        ep.cmd_record(
            self.root, self.task_dir, "discover", "pass", "python inspect.py",
            0, None, None, "inspect",
        )

    def test_minimal_record_uses_stable_result_id(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "arbitrary shell-like text --danger")
        plan = self.read_plan()
        self.assertEqual(list(plan["tasks"][0]["verification_results"]), ["phase-result"])

    def test_result_and_exit_code_must_agree(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError):
            self.record("discover", "inspect", result="pass", exit_code=1)
        with self.assertRaises(ep.PlanError):
            self.record("discover", "inspect", result="fail", exit_code=0)

    def test_long_command_is_stored_as_hash_and_summary(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        command = "x" * (ep.MAX_INLINE_COMMAND_LENGTH + 1)
        self.record("discover", command)
        entry = self.read_plan()["tasks"][0]["verification_results"]["phase-result"]
        self.assertNotIn("command", entry)
        self.assertEqual(entry["command_length"], len(command))
        self.assertEqual(entry["command_sha256"], ep.hashlib.sha256(command.encode("utf-8")).hexdigest())
        self.assertIn("summary", entry)
        self.assertEqual(entry["summary"], "x" * ep.MAX_COMMAND_SUMMARY_LENGTH + "…")
        ep.cmd_done(self.root, self.task_dir, "discover")

    def test_replay_verification_results_returns_one_map(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        replayed = ep.replay_verification_results(self.events(), self.read_plan())
        self.assertIsInstance(replayed, dict)
        self.assertIn("phase-result", replayed["discover"])

    def test_registered_artifact_must_be_task_local_and_not_symlink(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        outside = self.root / "outside.log"
        outside.write_text("outside\n", encoding="utf-8")
        with self.assertRaises(ep.PlanError):
            self.record("discover", "inspect", artifact=str(outside))
        link = self.task_dir / "linked.log"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are unavailable in this environment")
        with self.assertRaises(ep.PlanError):
            self.record("discover", "inspect", artifact="linked.log")

    def test_reject_report_write_failure_preserves_validation_issues(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["risk"] = "high"
        plan["tasks"][0]["verification"]["level"] = "minimal"
        self.write_plan(plan)
        original = ep._write_reject_reports
        try:
            ep._write_reject_reports = lambda *args, **kwargs: (_ for _ in ()).throw(
                ep.PlanError("disk full")
            )
            with self.assertRaises(ep.PlanError) as ctx:
                ep.cmd_validate(self.root, self.task_dir)
        finally:
            ep._write_reject_reports = original
        message = str(ctx.exception)
        self.assertIn("risk=high requires level>=raw", message)
        self.assertIn("reject report write failed", message)

    def test_validate_rejects_cycles_and_bad_paths(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][0]["depends_on"] = ["edit"]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("cycle", str(ctx.exception))

        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["scope"]["write"] = ["../outside.c"]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("escapes", str(ctx.exception))

    def test_validate_rejects_shell_like_check_ids(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["verification"]["checks"] = ["rm -rf / && build"]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("kebab-case", str(ctx.exception))

    def test_revalidate_detects_silent_edit(self) -> None:
        self.approve()
        plan = self.read_plan()
        plan["tasks"][1]["scope"]["write"] = ["src/b.c"]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("without revising", str(ctx.exception))

    def test_start_requires_approved_plan(self) -> None:
        with self.assertRaises(ep.PlanError):
            ep.cmd_start(self.root, self.task_dir, "discover")

    # -- advancement ------------------------------------------------------

    def test_start_blocks_unmet_dependency(self) -> None:
        self.approve()
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_start(self.root, self.task_dir, "edit")
        self.assertIn("unmet dependencies", str(ctx.exception))

    def test_full_happy_path(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError):
            ep.cmd_start(self.root, self.task_dir, "edit")  # parallel not allowed + dep
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "discover")  # result missing
        self.record("discover", "inspect")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "edit")  # result/check missing
        ep.cmd_check(self.root, self.task_dir, "edit", "app-build", "pass", None)
        ep.cmd_done(self.root, self.task_dir, "edit")
        names = [e["event"] for e in self.events()]
        self.assertEqual(names.count("task_completed"), 2)
        self.assertIn("plan_completed", names)
        self.assertEqual(self.read_plan()["tasks"][1]["status"], "completed")

    def test_unregistered_check_rejected(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["verification"]["checks"] = ["inspect"]
        self.write_plan(plan)
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_check(self.root, self.task_dir, "discover", "made-up", "pass", None)
        self.assertIn("registered", str(ctx.exception))

    def test_status_forgery_caught_by_audit_replay(self) -> None:
        self.approve()
        plan = self.read_plan()
        plan["tasks"][1]["status"] = "in_progress"  # skipped start + dependency
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "edit")
        self.assertIn("audit replay", str(ctx.exception))

    def test_completed_forgery_caught_at_validate(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_revise(self.root, self.task_dir, "scope grew")
        plan = self.read_plan()
        plan["tasks"][1]["status"] = "completed"  # never had a task_completed event
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("without audit history", str(ctx.exception))

    def test_completed_task_cannot_be_downgraded_by_edit(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_revise(self.root, self.task_dir, "reorder")
        plan = self.read_plan()
        plan["tasks"][0]["status"] = "pending"  # try to redo finished work
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("downgraded", str(ctx.exception))

    def test_revise_recovers_from_silent_guarded_edit(self) -> None:
        self.approve()
        plan = self.read_plan()
        plan["tasks"][1]["scope"]["write"] = ["src/b.c"]  # unauthorized edit
        self.write_plan(plan)
        out = ep.cmd_revise(self.root, self.task_dir, "legit reason")
        self.assertIn("reverted", out)
        revised = self.read_plan()
        self.assertEqual(revised["tasks"][1]["scope"]["write"], ["src/a.c"])  # snapshot restored
        self.assertEqual(revised["revision"], 2)
        self.assertEqual(revised["status"], "proposed")
        ep.cmd_validate(self.root, self.task_dir)  # clean re-approval path works

    # -- verification result forgery -----------------------------------------

    def test_forged_verification_result_rejected_by_done(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        plan = self.read_plan()
        plan["tasks"][0]["verification_results"] = {
            "inspect": {"result": "pass", "command": "inspect", "exit_code": 0}
        }
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "discover")
        self.assertIn("audit replay", str(ctx.exception))
        # and the state stayed untouched (no task_completed event)
        self.assertNotIn("task_completed", [e["event"] for e in self.events()])

    def test_forged_check_result_rejected(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        plan = self.read_plan()
        plan["tasks"][1]["verification_results"] = {
            "app-build": {"result": "pass", "command": "app-build", "exit_code": 0}
        }
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "edit")
        self.assertIn("verification result", str(ctx.exception).lower())

    def test_tampering_completed_verification_result_caught_at_validate(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_revise(self.root, self.task_dir, "grow scope")
        plan = self.read_plan()
        # silently delete the completed task's verification result
        plan["tasks"][0]["verification_results"] = {}
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("does not match the audit log", str(ctx.exception))

    def test_legitimate_verification_flow_still_passes_replay(self) -> None:
        # Regression guard: the replay check must not reject honest traffic,
        # including verification registered before a task's completion.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        ep.cmd_check(self.root, self.task_dir, "edit", "app-build", "pass", None)
        ep.cmd_done(self.root, self.task_dir, "edit")  # no drift error

    def test_minimal_phase_needs_only_recorded_result(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect symbols", summary="completed")
        ep.cmd_done(self.root, self.task_dir, "discover")

    def test_failed_record_blocks_done(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect", result="fail", exit_code=2)
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "discover")

    def test_raw_requires_existing_declared_artifact(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["risk"] = "high"
        plan["tasks"][0]["verification"] = {
            "level": "raw", "checks": ["build"],
            "required_artifacts": ["research/build.log"],
        }
        self.write_plan(plan)
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "build", artifact=None)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "discover")
        self.assertIn("missing required artifacts", str(ctx.exception))
        artifact = self.task_dir / "research" / "build.log"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text("build ok\n", encoding="utf-8")
        self.record("discover", "build", artifact="research/build.log")
        ep.cmd_done(self.root, self.task_dir, "discover")

    def test_report_requires_markdown_artifact(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["risk"] = "final"
        plan["tasks"][0]["verification"] = {
            "level": "report", "checks": ["review"],
            "required_artifacts": ["final-report.md"],
        }
        self.write_plan(plan)
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        artifact = self.task_dir / "review.json"
        artifact.write_text("{}\n", encoding="utf-8")
        self.record("discover", "review", artifact="review.json")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "discover")
        self.assertIn("missing required artifacts", str(ctx.exception))
        report = self.task_dir / "final-report.md"
        report.write_text("# Review\n", encoding="utf-8")
        self.record("discover", "review", artifact="final-report.md")
        ep.cmd_done(self.root, self.task_dir, "discover")

    def test_report_rejects_arbitrary_declared_markdown(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["risk"] = "final"
        plan["tasks"][0]["verification"] = {
            "level": "report", "checks": ["review"],
            "required_artifacts": ["prd.md"],
        }
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("final-report.md", str(ctx.exception))

    def test_report_root_file_cannot_satisfy_task_report(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["risk"] = "final"
        plan["tasks"][0]["verification"] = {
            "level": "report", "checks": ["review"],
            "required_artifacts": ["final-report.md"],
        }
        self.write_plan(plan)
        self.approve()
        (self.root / "final-report.md").write_text("# Wrong scope\n", encoding="utf-8")
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError):
            self.record("discover", "review", artifact="final-report.md")

    def test_verification_policy_rejection_writes_unique_report(self) -> None:
        plan = self.read_plan()
        plan["tasks"][0]["risk"] = "high"
        plan["tasks"][0]["verification"]["level"] = "minimal"
        self.write_plan(plan)
        for _ in range(2):
            with self.assertRaises(ep.PlanError) as ctx:
                ep.cmd_validate(self.root, self.task_dir)
            self.assertIn("requires level>=raw", str(ctx.exception))
        reports = sorted((self.task_dir / "reject-reports").glob("reject-*.json"))
        self.assertEqual(len(reports), 2)
        report = json.loads(reports[0].read_text(encoding="utf-8"))
        self.assertEqual(report["type"], "verification-policy-rejection")
        self.assertEqual(report["risk"], "high")
        self.assertEqual(report["requested_level"], "minimal")
        self.assertEqual(report["minimum_level"], "raw")
        self.assertRegex(report["time"], r"^\d{4}-\d{2}-\d{2}T.*Z$")

    # -- B2: task ref containment --------------------------------------------

    def test_resolve_task_dir_refuses_outside_repo(self) -> None:
        import tempfile as _tf
        with _tf.TemporaryDirectory() as outside:
            (Path(outside) / "execution-plan.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ep.PlanError):
                ep.resolve_task_dir(self.root, str(outside))
            with self.assertRaises(ep.PlanError):
                ep.resolve_task_dir(self.root, ".trellis/tasks/../demo2")

    def test_resolve_task_dir_accepts_inside_paths(self) -> None:
        got = ep.resolve_task_dir(self.root, ".trellis/tasks/demo")
        self.assertEqual(got, (self.root / ".trellis" / "tasks" / "demo").resolve())
        got = ep.resolve_task_dir(self.root, "demo")  # bare slug
        self.assertEqual(got, (self.root / ".trellis" / "tasks" / "demo").resolve())

    def test_resolve_task_dir_refuses_container_dirs(self) -> None:
        # Containers without task.json must not accept plan files.
        for ref in (".trellis/tasks", ".trellis/tasks/archive", ".trellis"):
            with self.subTest(ref=ref), self.assertRaises(ep.PlanError):
                ep.resolve_task_dir(self.root, ref)

    def test_status_shows_drift_line(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        plan = self.read_plan()
        plan["tasks"][0]["verification_results"] = {
            "inspect": {"result": "pass", "command": "inspect", "exit_code": 0}
        }
        self.write_plan(plan)
        text = ep.format_status(self.task_dir, self.root)
        self.assertIn("DRIFT", text)
        # mutations still refuse it (defense, not just display)
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "discover")

    def test_status_shows_status_forgery_drift(self) -> None:
        # N1: status-only forgery (maps still consistent) must still be
        # previewed by format_status, not only rejected on mutation.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        plan = self.read_plan()
        plan["tasks"][0]["status"] = "completed"
        self.write_plan(plan)
        text = ep.format_status(self.task_dir, self.root)
        self.assertIn("DRIFT", text)
        self.assertIn("audit says in_progress", text)
        with self.assertRaises(ep.PlanError):
            ep.cmd_record(
                self.root, self.task_dir, "discover", "pass", "inspect", 0, None, None
            )

    def test_resolve_task_dir_finds_archive_month_slugs(self) -> None:
        # N2: task.py archives under archive/<YYYY-MM>/<slug>.
        archived = self.root / ".trellis" / "tasks" / "archive" / "2026-08" / "old-task"
        archived.mkdir(parents=True)
        (archived / "task.json").write_text(
            json.dumps({"id": "old-task", "status": "completed"}), encoding="utf-8"
        )
        got = ep.resolve_task_dir(self.root, "old-task")
        self.assertEqual(got, archived.resolve())

    def test_resolve_task_dir_refuses_glob_metachar_slugs(self) -> None:
        # A "*" slug must fail loudly, not silently hit the first task.
        archived = self.root / ".trellis" / "tasks" / "archive" / "2026-08" / "first"
        archived.mkdir(parents=True)
        (archived / "task.json").write_text('{"id": "first"}', encoding="utf-8")
        for ref in ("*", "f*s*t", "fi?st", "[a]rch"):
            with self.subTest(ref=ref), self.assertRaises(ep.PlanError):
                ep.resolve_task_dir(self.root, ref)

    # -- block / revise ----------------------------------------------------

    def test_block_and_resume(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_block(self.root, self.task_dir, "discover", "requirement unclear")
        self.assertEqual(self.read_plan()["tasks"][0]["status"], "blocked")
        ep.cmd_start(self.root, self.task_dir, "discover")  # resume from blocked
        self.assertEqual(self.read_plan()["tasks"][0]["status"], "in_progress")

    def test_revise_resets_and_bumps_revision(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_revise(self.root, self.task_dir, "split edit phase")
        plan = self.read_plan()
        self.assertEqual(plan["revision"], 2)
        self.assertEqual(plan["status"], "proposed")
        self.assertEqual(plan["tasks"][0]["status"], "completed")
        self.assertIn("verification_results", plan["tasks"][0])  # preserved for completed task
        ep.cmd_validate(self.root, self.task_dir)  # re-approve revision 2
        ep.cmd_start(self.root, self.task_dir, "edit")  # deps still satisfied
        names = [e["event"] for e in self.events()]
        self.assertIn("plan_revised", names)
        self.assertEqual(names.count("plan_approved"), 2)

    def test_revise_requires_approved_revision(self) -> None:
        with self.assertRaises(ep.PlanError):
            ep.cmd_revise(self.root, self.task_dir, "too early")

    # -- audit integrity -----------------------------------------------------

    def test_corrupt_audit_pauses_mutations(self) -> None:
        self.approve()
        with (self.task_dir / ep.EVENTS_FILE).open("a", encoding="utf-8") as fh:
            fh.write("this is not json\n")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_start(self.root, self.task_dir, "discover")
        self.assertIn("unparseable", str(ctx.exception))
        # Status still readable (plan JSON remains the state source).
        self.assertIn("discover", ep.format_status(self.task_dir, self.root))

    def test_edit_counters_enforced_when_present(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        self.record("discover", "inspect")
        plan_rel = ep.task_rel_path(self.root, self.task_dir)
        # max_edits_per_file is 2 in BASE_PLAN; simulate the hook counting 3.
        ep.bump_edit(self.root, plan_rel, 1, "discover", "src/a.c")
        ep.bump_edit(self.root, plan_rel, 1, "discover", "src/a.c")
        ep.bump_edit(self.root, plan_rel, 1, "discover", "src/a.c")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "discover")
        self.assertIn("max_edits_per_file", str(ctx.exception))

    def test_scope_match_globs(self) -> None:
        self.assertTrue(ep.scope_match("src/**/*.c", "src/app/mod.c"))
        self.assertTrue(ep.scope_match("src/a.c", "src/a.c"))
        self.assertFalse(ep.scope_match("src/a.c", "src/b.c"))
        self.assertTrue(ep.scope_match("src/Function", "src/Function/APP/x.c"))


if __name__ == "__main__":
    unittest.main()
