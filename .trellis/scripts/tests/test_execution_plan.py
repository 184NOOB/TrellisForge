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
    "schema": 3,
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
            "verification": {"level": "minimal", "required_checks": []},
            "no_check_reason": "pure read-only discovery; no files are touched",
        },
        {
            "id": "edit",
            "title": "edit code",
            "status": "pending",
            "objective": "change code",
            "depends_on": ["discover"],
            "scope": {"read": ["src/a.c"], "write": ["src/a.c"]},
            "verification": {"level": "minimal", "required_checks": ["app-build"]},
        },
    ],
}


def report_task(**overrides) -> dict:
    task = {
        "id": "verify-final",
        "title": "final acceptance",
        "status": "pending",
        "objective": "prove the task",
        "depends_on": ["edit"],
        "scope": {"read": ["src/"], "write": ["final-report.md"]},
        "verification": {
            "level": "report",
            "required_checks": ["build", "test", "diff-check"],
            "report_path": "final-report.md",
        },
    }
    task.update(overrides)
    return task


SEQ_PLAN = {
    "schema": 3,
    "task": ".trellis/tasks/demo",
    "revision": 1,
    "status": "proposed",
    "audit": {"required": True, "file": "execution-events.jsonl"},
    "created_by": "trellis-implement",
    "goal": "sequel goal",
    "constraints": {
        "forbidden_git_operations": ["commit"],
        "max_tasks": 8,
        "max_edits_per_file": 2,
        "allow_parallel_tasks": False,
    },
    "tasks": [
        {
            "id": "discover-x",
            "title": "read code",
            "status": "pending",
            "objective": "map symbols",
            "depends_on": [],
            "scope": {"read": ["src/**/*.c"], "write": []},
            "verification": {"level": "minimal", "required_checks": []},
            "no_check_reason": "pure read-only discovery; no files are touched",
        },
        {
            "id": "edit-x",
            "title": "edit code",
            "status": "pending",
            "objective": "change code",
            "depends_on": ["discover-x"],
            "scope": {"read": ["src/a.c"], "write": ["src/a.c"]},
            "verification": {"level": "minimal", "required_checks": ["app-build"]},
        },
        {
            "id": "verify-final-x",
            "title": "final acceptance",
            "status": "pending",
            "objective": "prove the task",
            "depends_on": ["edit-x"],
            "scope": {"read": ["src/"], "write": ["final-report.md"]},
            "verification": {
                "level": "report",
                "required_checks": ["build"],
                "report_path": "final-report.md",
            },
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

    def record(self, task_id: str, check: str, command: str = "cmd-id", *,
               result: str = "pass", exit_code: int = 0, artifact: str | None = None,
               summary: str | None = "short result") -> None:
        ep.cmd_record(self.root, self.task_dir, task_id, result, command,
                      exit_code, artifact, summary, check)

    def complete_discover(self) -> None:
        """Read-only discover phase: start→done needs no records (PRD 5.2)."""
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")

    def start_edit(self) -> None:
        self.approve()
        self.complete_discover()
        ep.cmd_start(self.root, self.task_dir, "edit")

    def complete_report_plan(self) -> None:
        """Drive BASE_PLAN + report task through full completion."""
        self.setup_report_plan()
        ep.cmd_start(self.root, self.task_dir, "verify-final")
        (self.task_dir / "final-report.md").write_text(
            "# Final report\n", encoding="utf-8"
        )
        self.record("verify-final", "build", command="keil-build-all")
        self.record("verify-final", "test", command="unit-tests")
        self.record("verify-final", "diff-check", command="git-diff-check",
                    artifact="final-report.md")
        ep.cmd_done(self.root, self.task_dir, "verify-final")

    def live_dir(self) -> Path:
        return ep.resolve_live_plan(self.task_dir)[1]

    def read_live_plan(self) -> dict:
        return json.loads(ep.plan_path(self.task_dir).read_text(encoding="utf-8"))

    def frozen_plan_path(self, number: int) -> Path:
        return self.task_dir / ep.PLANS_DIR / str(number) / ep.PLAN_FILE

    def sequel_to(self, reason: str = "requirement continues") -> str:
        return ep.cmd_sequel(self.root, self.task_dir, reason)

    def complete_seq_plan(self) -> None:
        """Drive SEQ_PLAN (live plan 2+) through full completion."""
        ep.cmd_start(self.root, self.task_dir, "discover-x")
        ep.cmd_done(self.root, self.task_dir, "discover-x")
        ep.cmd_start(self.root, self.task_dir, "edit-x")
        self.record("edit-x", "app-build")
        ep.cmd_done(self.root, self.task_dir, "edit-x")
        ep.cmd_start(self.root, self.task_dir, "verify-final-x")
        (self.live_dir() / "final-report.md").write_text(
            "# Sequel report\n", encoding="utf-8"
        )
        self.record("verify-final-x", "build", command="keil-build-all",
                    artifact="final-report.md")
        ep.cmd_done(self.root, self.task_dir, "verify-final-x")

    # -- validate / AC1: only two levels --------------------------------

    def test_validate_approves_and_logs(self) -> None:
        result = self.approve()
        plan = self.read_plan()
        self.assertEqual(plan["status"], "approved")
        self.assertIn("approved_fingerprint", plan)
        names = [e["event"] for e in self.events()]
        self.assertEqual(names, ["plan_created", "plan_approved"])
        self.assertTrue(result)

    def test_validate_rejects_old_schema(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["schema"] = 2
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("schema must be 3", str(ctx.exception))

    def test_validate_rejects_raw_level(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["verification"]["level"] = "raw"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        message = str(ctx.exception)
        self.assertIn("verification.level must be one of", message)
        self.assertNotIn("'raw'", message)

    def test_validate_rejects_unknown_level(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][0]["verification"]["level"] = "strict"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("verification.level", str(ctx.exception))

    def test_validate_rejects_legacy_fields(self) -> None:
        cases = [
            ({"risk": "high"}, "risk"),
            ({"required_evidence": ["md"]}, "required_evidence"),
            ({"required_artifacts": ["log"]}, "required_artifacts"),
            (
                {"verification": {"level": "minimal", "required_checks": ["x"],
                                  "required_artifacts": []}},
                "required_artifacts",
            ),
        ]
        for legacy, needle in cases:
            plan = copy.deepcopy(BASE_PLAN)
            if "verification" in legacy:
                plan["tasks"][1]["verification"] = legacy["verification"]
            else:
                plan["tasks"][1].update(legacy)
            self.write_plan(plan)
            with self.assertRaises(ep.PlanError) as ctx:
                ep.cmd_validate(self.root, self.task_dir)
            self.assertIn(needle, str(ctx.exception))

    # -- validate / AC3: required_checks constraints --------------------

    def test_empty_checks_require_no_check_reason(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][0].pop("no_check_reason")
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("no_check_reason", str(ctx.exception))

    def test_write_phase_cannot_bypass_with_empty_checks(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["verification"]["required_checks"] = []
        plan["tasks"][1]["no_check_reason"] = "trying to bypass"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("scope.write", str(ctx.exception))

    def test_no_check_reason_rejected_when_checks_declared(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["no_check_reason"] = "not needed"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("only valid when", str(ctx.exception))

    def test_validate_rejects_top_level_legacy_fields(self) -> None:
        # F1: plan-level legacy fields are refused, not just task-level ones.
        plan = copy.deepcopy(BASE_PLAN)
        plan["risk"] = "high"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("top-level fields", str(ctx.exception))

    def test_validate_rejects_unbounded_write_scope(self) -> None:
        # F15/R2-1: any wildcard-only pattern (no fixed segment) matches the
        # whole repository and is refused; bounded globs stay legal.
        for pattern in ("*", "**", "**/*", "*/**", "**/**", "*/*"):
            plan = copy.deepcopy(BASE_PLAN)
            plan["tasks"][1]["scope"]["write"] = [pattern]
            self.write_plan(plan)
            with self.subTest(pattern=pattern), self.assertRaises(ep.PlanError) as ctx:
                ep.cmd_validate(self.root, self.task_dir)
            self.assertIn("unbounded pattern", str(ctx.exception))
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["scope"]["write"] = ["src/**"]
        self.write_plan(plan)
        self.approve()

    def test_validate_rejects_unhashable_dependency_cleanly(self) -> None:
        # R2-2: malformed dep entries must produce a validation issue, not a
        # TypeError traceback out of the membership checks.
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][0]["depends_on"] = [{"x": 1}]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("list of task ids", str(ctx.exception))

    def test_validate_rejects_missing_required_checks(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["verification"].pop("required_checks")
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("required_checks", str(ctx.exception))

    def test_validate_rejects_shell_like_check_ids(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["verification"]["required_checks"] = ["rm -rf / && build"]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("kebab-case", str(ctx.exception))

    # -- validate / AC4: report topology ---------------------------------

    def test_report_requires_report_path(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][0]["verification"] = {"level": "report", "required_checks": ["review"]}
        plan["tasks"][0].pop("no_check_reason")
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("report_path", str(ctx.exception))

    def test_report_path_must_be_final_report(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task())
        plan["tasks"][-1]["verification"]["report_path"] = "summary.md"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("final-report.md", str(ctx.exception))

    def test_report_path_rejected_on_minimal_level(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"][1]["verification"]["report_path"] = "final-report.md"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("only valid for level=report", str(ctx.exception))

    def test_multiple_report_phases_rejected(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task())
        second = report_task(id="verify-final-2", depends_on=["verify-final"])
        second["scope"]["read"] = ["src/"]
        plan["tasks"].append(second)
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("at most one", str(ctx.exception))

    def test_report_phase_must_be_terminal(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task(depends_on=["discover"]))
        follower = {
            "id": "after-report",
            "title": "depends on the report",
            "status": "pending",
            "objective": "illegally after acceptance",
            "depends_on": ["verify-final"],
            "scope": {"read": [], "write": ["src/a.c"]},
            "verification": {"level": "minimal", "required_checks": ["x"]},
        }
        plan["tasks"].append(follower)
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("must be terminal", str(ctx.exception))

    def test_report_phase_requires_checks(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task())
        plan["tasks"][-1]["verification"]["required_checks"] = []
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("at least one", str(ctx.exception))

    def test_report_phase_must_depend_on_all_work(self) -> None:
        # F3: a report phase with no dependency chain to the implementation
        # could "finalize" before any work exists.
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task(depends_on=[]))
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            self.approve()
        self.assertIn("(transitively) depend", str(ctx.exception))

    def test_report_phase_transitive_coverage_counts(self) -> None:
        # verify-final ← edit ← discover: the closure covers every task.
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task())
        self.write_plan(plan)
        self.approve()

    # -- validate / general ---------------------------------------------

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

    def test_revalidate_detects_silent_edit(self) -> None:
        self.approve()
        plan = self.read_plan()
        plan["tasks"][1]["scope"]["write"] = ["src/b.c"]
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("without revising", str(ctx.exception))

    def test_revalidate_detects_check_removal(self) -> None:
        # PRD 5.2: declared checks may not be silently dropped after approval.
        self.approve()
        plan = self.read_plan()
        plan["tasks"][1]["verification"]["required_checks"] = []
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        # Either the shape rule (write phase needs a check) or the fingerprint
        # mismatch refuses; silent removal can never validate.
        message = str(ctx.exception)
        self.assertTrue(
            "required_checks" in message or "without revising" in message,
            message,
        )

    def test_start_requires_approved_plan(self) -> None:
        with self.assertRaises(ep.PlanError):
            ep.cmd_start(self.root, self.task_dir, "discover")

    # -- AC2 / advancement ------------------------------------------------

    def test_start_blocks_unmet_dependency(self) -> None:
        self.approve()
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_start(self.root, self.task_dir, "edit")
        self.assertIn("unmet dependencies", str(ctx.exception))

    def test_readonly_phase_completes_without_records(self) -> None:
        # AC2/AC3: minimal + empty required_checks (with no_check_reason)
        # completes with no artifact, no Markdown, and no record calls.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        self.assertEqual(self.read_plan()["tasks"][0]["status"], "completed")

    def test_full_happy_path(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError):
            ep.cmd_start(self.root, self.task_dir, "edit")  # parallel not allowed + dep
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "edit")  # check missing
        self.record("edit", "app-build", command="keil-app-build")
        ep.cmd_done(self.root, self.task_dir, "edit")
        names = [e["event"] for e in self.events()]
        self.assertEqual(names.count("task_completed"), 2)
        self.assertIn("plan_completed", names)
        self.assertEqual(self.read_plan()["tasks"][1]["status"], "completed")

    def test_record_cli_flow_requires_check_and_summary(self) -> None:
        self.start_edit()
        with patch.object(plan_cli, "get_repo_root", return_value=self.root), \
             patch.object(plan_cli, "resolve_task_dir", return_value=self.task_dir):
            with self.assertRaises(SystemExit):  # missing --summary (argparse required)
                plan_cli.main([
                    "--task", str(self.task_dir), "record", "edit",
                    "--check", "app-build", "--result", "pass",
                    "--command", "keil-app-build", "--exit-code", "0",
                ])
            exit_code = plan_cli.main([
                "--task", str(self.task_dir), "record", "edit",
                "--check", "app-build", "--result", "pass",
                "--command", "keil-app-build", "--exit-code", "0",
                "--summary", "0 errors 0 warnings",
            ])
        self.assertEqual(exit_code, 0)
        plan = self.read_plan()
        entry = plan["tasks"][1]["verification_results"]["app-build"]
        self.assertEqual(entry["result"], "pass")
        self.assertEqual(entry["exit_code"], 0)
        self.assertEqual(entry["summary"], "0 errors 0 warnings")

    def test_record_rejects_undeclared_check(self) -> None:
        self.start_edit()
        with self.assertRaises(ep.PlanError) as ctx:
            self.record("edit", "made-up")
        self.assertIn("not a declared required check", str(ctx.exception))

    def test_record_refused_for_phase_without_checks(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError) as ctx:
            self.record("discover", "anything")
        self.assertIn("not a declared required check", str(ctx.exception))

    def test_result_and_exit_code_must_agree(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        with self.assertRaises(ep.PlanError):
            self.record("edit", "app-build", result="pass", exit_code=1)
        with self.assertRaises(ep.PlanError):
            self.record("edit", "app-build", result="fail", exit_code=0)

    def test_record_requires_summary(self) -> None:
        self.start_edit()
        with self.assertRaises(ep.PlanError) as ctx:
            self.record("edit", "app-build", summary=None)
        self.assertIn("--summary", str(ctx.exception))
        with self.assertRaises(ep.PlanError):
            self.record("edit", "app-build", summary="   ")

    def test_long_command_is_stored_as_hash(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        command = "x" * (ep.MAX_INLINE_COMMAND_LENGTH + 1)
        self.record("edit", "app-build", command=command, summary="build ok")
        entry = self.read_plan()["tasks"][1]["verification_results"]["app-build"]
        self.assertNotIn("command", entry)
        self.assertEqual(entry["command_length"], len(command))
        self.assertEqual(entry["command_sha256"], ep.hashlib.sha256(command.encode("utf-8")).hexdigest())
        self.assertEqual(entry["summary"], "build ok")
        ep.cmd_done(self.root, self.task_dir, "edit")

    def test_replay_verification_results_returns_one_map(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build")
        replayed = ep.replay_verification_results(self.events(), self.read_plan())
        self.assertIsInstance(replayed, dict)
        self.assertIn("app-build", replayed["edit"])

    def test_registered_artifact_must_be_task_local_and_not_symlink(self) -> None:
        self.start_edit()
        outside = self.root / "outside.log"
        outside.write_text("outside\n", encoding="utf-8")
        with self.assertRaises(ep.PlanError):
            self.record("edit", "app-build", artifact=str(outside))
        link = self.task_dir / "linked.log"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are unavailable in this environment")
        with self.assertRaises(ep.PlanError):
            self.record("edit", "app-build", artifact="linked.log")

    # -- AC3: fail handling ------------------------------------------------

    def test_failed_record_blocks_done(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build", result="fail", exit_code=2)
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "edit")

    def test_fail_record_cannot_be_overwritten(self) -> None:
        # PRD 5.2: failed checks cannot be ignored or overwritten.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build", result="fail", exit_code=2)
        with self.assertRaises(ep.PlanError) as ctx:
            self.record("edit", "app-build", result="pass", exit_code=0)
        self.assertIn("cannot be ignored or overwritten", str(ctx.exception))
        # Recovery path: block, revise, then the new revision may record again.
        ep.cmd_block(self.root, self.task_dir, "edit", "build broken")
        ep.cmd_revise(self.root, self.task_dir, "fix then re-verify")
        self.approve()  # discover stays completed; edit is pending again
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build", command="keil-app-build")
        ep.cmd_done(self.root, self.task_dir, "edit")
        # The superseded fail must not poison the completed task's replay window
        # (otherwise every later mutation would freeze on a phantom drift).
        self.assertEqual(ep.managed_drift(self.read_plan(), self.events()), [])

    # -- AC4: report stage -------------------------------------------------

    def setup_report_plan(self) -> None:
        plan = copy.deepcopy(BASE_PLAN)
        plan["tasks"].append(report_task())
        self.write_plan(plan)
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build")
        ep.cmd_done(self.root, self.task_dir, "edit")

    def test_report_done_requires_final_report(self) -> None:
        self.setup_report_plan()
        ep.cmd_start(self.root, self.task_dir, "verify-final")
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "verify-final")  # no records
        self.record("verify-final", "build", command="keil-build-all")
        self.record("verify-final", "test", command="unit-tests")
        self.record("verify-final", "diff-check", command="git-diff-check")
        # All checks pass but the report file is missing → done must fail.
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "verify-final")
        self.assertIn("final-report.md", str(ctx.exception))
        (self.task_dir / "final-report.md").write_text("# Final report\n", encoding="utf-8")
        # File exists but is not registered through record --artifact.
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "verify-final")
        self.assertIn("--artifact", str(ctx.exception))
        self.record("verify-final", "diff-check", command="git-diff-check",
                    artifact="final-report.md")
        ep.cmd_done(self.root, self.task_dir, "verify-final")
        names = [e["event"] for e in self.events()]
        self.assertIn("plan_completed", names)

    def test_report_root_file_cannot_satisfy_task_report(self) -> None:
        self.setup_report_plan()
        (self.root / "final-report.md").write_text("# Wrong scope\n", encoding="utf-8")
        ep.cmd_start(self.root, self.task_dir, "verify-final")
        with self.assertRaises(ep.PlanError):
            self.record("verify-final", "build", artifact="final-report.md")

    # -- forgery / drift guards -------------------------------------------

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

    def test_completed_task_reopen_is_sanctioned_and_requires_rerun(self) -> None:
        # R3/AC3: after revise, resetting a completed non-report phase to
        # pending is a sanctioned reopen — validate records task_reopened and
        # clears the superseded managed map. Re-marking it completed by hand
        # without re-running stays rejected.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_revise(self.root, self.task_dir, "redo discovery")
        plan = self.read_plan()
        plan["tasks"][0]["status"] = "pending"
        plan["tasks"][0]["objective"] = "re-map symbols with the new spec"
        self.write_plan(plan)
        ep.cmd_validate(self.root, self.task_dir)
        reopened = [e for e in self.events() if e["event"] == "task_reopened"]
        self.assertEqual([e["task"] for e in reopened], ["discover"])
        ep.cmd_revise(self.root, self.task_dir, "second revision")
        plan = self.read_plan()
        self.assertEqual(plan["tasks"][0]["status"], "pending")
        plan["tasks"][0]["status"] = "completed"  # no re-run happened
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("cannot be marked completed again", str(ctx.exception))

    def test_forged_verification_result_rejected_by_done(self) -> None:
        self.start_edit()
        plan = self.read_plan()
        plan["tasks"][1]["verification_results"] = {
            "app-build": {"result": "pass", "command": "keil", "exit_code": 0,
                          "summary": "forged"}
        }
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_done(self.root, self.task_dir, "edit")
        self.assertIn("audit replay", str(ctx.exception))
        completed_tasks = {
            e.get("task") for e in self.events() if e["event"] == "task_completed"
        }
        self.assertNotIn("edit", completed_tasks)  # state stayed untouched for edit

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

    def test_tampering_completed_verification_result_caught_at_validate(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build")
        ep.cmd_done(self.root, self.task_dir, "edit")
        ep.cmd_revise(self.root, self.task_dir, "grow scope")
        plan = self.read_plan()
        # silently delete the completed task's verification result
        plan["tasks"][1]["verification_results"] = {}
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("does not match the audit log", str(ctx.exception))

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
        self.start_edit()
        plan = self.read_plan()
        plan["tasks"][1]["verification_results"] = {
            "app-build": {"result": "pass", "command": "keil", "exit_code": 0}
        }
        self.write_plan(plan)
        text = ep.format_status(self.task_dir, self.root)
        self.assertIn("DRIFT", text)
        with self.assertRaises(ep.PlanError):
            ep.cmd_done(self.root, self.task_dir, "edit")

    def test_status_shows_missing_report(self) -> None:
        self.setup_report_plan()
        ep.cmd_start(self.root, self.task_dir, "verify-final")
        text = ep.format_status(self.task_dir, self.root)
        self.assertIn("missing final-report.md file", text)

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
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build")
        ep.cmd_done(self.root, self.task_dir, "edit")
        ep.cmd_revise(self.root, self.task_dir, "split edit phase")
        plan = self.read_plan()
        self.assertEqual(plan["revision"], 2)
        self.assertEqual(plan["status"], "proposed")
        self.assertEqual(plan["tasks"][0]["status"], "completed")
        self.assertEqual(plan["tasks"][1]["status"], "completed")
        self.assertIn("verification_results", plan["tasks"][1])  # preserved for completed task
        ep.cmd_validate(self.root, self.task_dir)  # re-approve revision 2
        names = [e["event"] for e in self.events()]
        self.assertIn("plan_revised", names)
        self.assertEqual(names.count("plan_approved"), 2)

    def test_revise_requires_approved_revision(self) -> None:
        with self.assertRaises(ep.PlanError):
            ep.cmd_revise(self.root, self.task_dir, "too early")

    def test_hand_flip_to_proposed_cannot_reapprove(self) -> None:
        # F11: flipping an approved plan's status to 'proposed' by hand must
        # not silently re-stamp the fingerprint; revise is the only door.
        self.approve()
        plan = self.read_plan()
        plan["status"] = "proposed"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("hand-flip", str(ctx.exception))
        # Recovery: restore 'approved' then revise (sanctioned reopen).
        plan["status"] = "approved"
        self.write_plan(plan)
        ep.cmd_revise(self.root, self.task_dir, "legitimate reopen")
        self.assertEqual(self.read_plan()["revision"], 2)

    def test_revise_self_heals_crashed_revise_event(self) -> None:
        # F6: revise saved the proposed plan but crashed before appending
        # plan_revised. Running revise again heals the audit instead of
        # deadlocking validate↔revise.
        self.approve()
        plan = self.read_plan()
        plan["status"] = "proposed"
        plan["revision"] = 2
        for task in plan["tasks"]:
            task["status"] = "pending"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("run plan.py revise", str(ctx.exception))
        out = ep.cmd_revise(self.root, self.task_dir, "crash recovery")
        self.assertIn("audit healed", out)
        self.assertIn("plan_revised", [e["event"] for e in self.events()])
        ep.cmd_validate(self.root, self.task_dir)  # revision 2 approves cleanly
        self.assertEqual(self.read_plan()["revision"], 2)
        self.assertEqual(self.read_plan()["status"], "approved")

    def test_revise_heals_only_the_exact_crash_window(self) -> None:
        # R2-4: heal requires revision == expected + 1; anything larger is a
        # plain illegal bump and revise must refuse without writing events.
        self.approve()
        plan = self.read_plan()
        plan["status"] = "proposed"
        plan["revision"] = 3  # expected is 1
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError):
            ep.cmd_revise(self.root, self.task_dir, "not a crash")
        self.assertNotIn("plan_revised", [e["event"] for e in self.events()])
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("only plan.py revise bumps revisions", str(ctx.exception))

    def test_revise_reset_note_only_lists_real_resets(self) -> None:
        # R2-6: a task whose JSON drifted to in_progress while the audit says
        # completed is re-derived to completed — it was not "reset to pending".
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        plan = self.read_plan()
        plan["tasks"][0]["status"] = "in_progress"
        self.write_plan(plan)
        out = ep.cmd_revise(self.root, self.task_dir, "rederive statuses")
        self.assertNotIn("reset to pending", out)
        healed = self.read_plan()
        self.assertEqual(healed["tasks"][0]["status"], "completed")

    # -- audit integrity / AC7 ----------------------------------------------

    def test_corrupt_audit_pauses_mutations(self) -> None:
        self.approve()
        with (self.task_dir / ep.EVENTS_FILE).open("a", encoding="utf-8") as fh:
            fh.write("this is not json\n")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_start(self.root, self.task_dir, "discover")
        self.assertIn("unparseable", str(ctx.exception))
        # Status still readable (plan JSON remains the state source).
        self.assertIn("discover", ep.format_status(self.task_dir, self.root))

    def test_crash_recovery_with_files_only(self) -> None:
        # AC7: recovery relies on task-directory files only — a fresh process
        # (simulated here by calling the CLI entrypoint directly, no session
        # state, no hooks) sees the plan and resumes the in_progress task.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with patch.object(plan_cli, "get_repo_root", return_value=self.root):
            exit_code = plan_cli.main([
                "--task", str(self.task_dir), "status",
            ])
        self.assertEqual(exit_code, 0)
        plan = self.read_plan()
        in_progress = [t["id"] for t in plan["tasks"] if t["status"] == "in_progress"]
        self.assertEqual(in_progress, ["discover"])

    def test_edit_counters_never_block_done(self) -> None:
        # Two-level PRD 10: hooks are display-only. Even if the PreToolUse
        # counter hook recorded an overrun, plan.py done must not consult it.
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        ep.cmd_done(self.root, self.task_dir, "discover")
        ep.cmd_start(self.root, self.task_dir, "edit")
        self.record("edit", "app-build")
        plan_rel = ep.task_rel_path(self.root, self.task_dir)
        # max_edits_per_file is 2 in BASE_PLAN; simulate the hook counting 5.
        for _ in range(5):
            ep.bump_edit(self.root, plan_rel, 1, "edit", "src/a.c")
        ep.cmd_done(self.root, self.task_dir, "edit")
        self.assertEqual(self.read_plan()["tasks"][1]["status"], "completed")

    def test_scope_match_globs(self) -> None:
        self.assertTrue(ep.scope_match("src/**/*.c", "src/app/mod.c"))
        self.assertTrue(ep.scope_match("src/a.c", "src/a.c"))
        self.assertFalse(ep.scope_match("src/a.c", "src/b.c"))
        self.assertTrue(ep.scope_match("src/Function", "src/Function/APP/x.c"))

    # -- completion-state exit / sequel layout ------------------------------

    def test_legacy_single_file_layout_needs_no_migration(self) -> None:
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())
        self.approve()
        self.assertEqual(ep.resolve_live_plan(self.task_dir)[0], 1)
        self.assertEqual(ep.plan_path(self.task_dir), self.task_dir / ep.PLAN_FILE)
        text = ep.format_status(self.task_dir, self.root)
        self.assertIn("execution plan:", text)
        self.assertNotIn("frozen plans:", text)

    def test_protocol_block_offers_small_patch_and_in_place_revise_when_complete(self) -> None:
        self.complete_report_plan()
        text = ep.plan_protocol_block(self.root, self.task_dir)
        self.assertIn("fully completed", text)
        self.assertIn("Small patch (hard rule)", text)
        self.assertIn("touch any execution-plan file", text)
        self.assertIn("revise --reason", text)
        self.assertIn("Unmodified completed phases stay `completed`", text)
        self.assertIn("terminal report resets to `pending`", text)
        self.assertIn("sequel", text)
        self.assertIn("new Trellis task", text)
        self.assertNotIn("Per phase loop", text)

    def test_revise_reopens_completed_report_and_clears_its_records(self) -> None:
        # R1/R4: a fully completed live plan reopens in place; unmodified
        # completed phases stay completed while the terminal report resets to
        # pending with its managed map cleared. No sequel directory appears.
        self.complete_report_plan()
        out = ep.cmd_revise(self.root, self.task_dir, "same requirement continues")
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())
        self.assertIn("reopened terminal report", out)
        plan = self.read_live_plan()
        self.assertEqual(plan["revision"], 2)
        self.assertEqual(plan["status"], "proposed")
        by_id = {t["id"]: t for t in plan["tasks"]}
        self.assertEqual(by_id["discover"]["status"], "completed")
        self.assertEqual(by_id["edit"]["status"], "completed")
        self.assertEqual(by_id["verify-final"]["status"], "pending")
        self.assertNotIn("verification_results", by_id["verify-final"])
        revised = [e for e in self.events() if e["event"] == "plan_revised"][-1]
        self.assertEqual(revised["reopened"], ["verify-final"])

    def test_add_phase_after_completion_validates_and_reruns_report(self) -> None:
        # AC1/AC2: no sequel, no new task — revise, add a phase, update the
        # report's depends_on, validate, then re-run the new phase and the
        # terminal report, producing a fresh live final-report.md.
        self.complete_report_plan()
        ep.cmd_revise(self.root, self.task_dir, "a phase was missed")
        plan = self.read_live_plan()
        by_id = {t["id"]: t for t in plan["tasks"]}
        plan["tasks"].append({
            "id": "extra",
            "title": "extra phase",
            "status": "pending",
            "objective": "cover the missed work",
            "depends_on": ["edit"],
            "scope": {"read": ["src/"], "write": ["src/b.c"]},
            "verification": {"level": "minimal", "required_checks": ["extra-check"]},
        })
        by_id["verify-final"]["depends_on"] = ["edit", "extra"]
        self.write_plan(plan)
        ep.cmd_validate(self.root, self.task_dir)
        live = self.read_live_plan()
        self.assertEqual(live["tasks"][0]["status"], "completed")
        report = next(t for t in live["tasks"] if t["id"] == "verify-final")
        self.assertEqual(report["status"], "pending")
        reopened = [e for e in self.events() if e["event"] == "task_reopened"]
        self.assertEqual([e["task"] for e in reopened], ["verify-final"])
        ep.cmd_start(self.root, self.task_dir, "extra")
        self.record("extra", "extra-check")
        ep.cmd_done(self.root, self.task_dir, "extra")
        ep.cmd_start(self.root, self.task_dir, "verify-final")
        (self.live_dir() / "final-report.md").write_text(
            "# Second final report\n", encoding="utf-8"
        )
        self.record("verify-final", "build", command="keil-build-all",
                    artifact="final-report.md")
        self.record("verify-final", "test", command="unit-tests")
        self.record("verify-final", "diff-check", command="git-diff-check",
                    artifact="final-report.md")
        ep.cmd_done(self.root, self.task_dir, "verify-final")
        self.assertEqual(
            (self.live_dir() / "final-report.md").read_text(encoding="utf-8"),
            "# Second final report\n",
        )
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())
        completed = [e for e in self.events() if e["event"] == "plan_completed"]
        self.assertEqual(completed[-1]["revision"], 2)

    def test_completed_step_fingerprint_change_requires_pending_first(self) -> None:
        self.complete_report_plan()
        ep.cmd_revise(self.root, self.task_dir, "change edit scope")
        plan = self.read_live_plan()
        edit_task = next(t for t in plan["tasks"] if t["id"] == "edit")
        edit_task["objective"] = "changed while still completed"
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("rewritten after completion", str(ctx.exception))

    def test_report_demotion_after_completion_is_rejected(self) -> None:
        # AC4: the completion-state report cannot be demoted to a normal phase
        # or marked completed again by hand.
        self.complete_report_plan()
        ep.cmd_revise(self.root, self.task_dir, "reopen the live plan")
        plan = self.read_live_plan()
        report = next(t for t in plan["tasks"] if t["id"] == "verify-final")
        self.assertEqual(report["status"], "pending")
        report["verification"] = {"level": "minimal", "required_checks": ["build"]}
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("must stay level=report", str(ctx.exception))

    def test_report_marked_completed_again_is_rejected(self) -> None:
        self.complete_report_plan()
        ep.cmd_revise(self.root, self.task_dir, "reopen the live plan")
        plan = self.read_live_plan()
        report = next(t for t in plan["tasks"] if t["id"] == "verify-final")
        report["status"] = "completed"  # guarded fields untouched hand-flip
        self.write_plan(plan)
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("must be reset to pending", str(ctx.exception))

    def test_sequel_freezes_completed_plan_and_opens_live_two(self) -> None:
        self.complete_report_plan()
        frozen_events = (self.task_dir / ep.EVENTS_FILE).read_text(encoding="utf-8")
        out = self.sequel_to()
        self.assertIn("live plan is now 2", out)
        pointer = json.loads((self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8"))
        self.assertEqual(pointer, {"schema": 3, "live": 2})
        self.assertEqual(ep.resolve_live_plan(self.task_dir)[0], 2)
        self.assertEqual(self.live_dir(), self.task_dir / ep.PLANS_DIR / "2")
        frozen = json.loads(self.frozen_plan_path(1).read_text(encoding="utf-8"))
        self.assertTrue(all(t["status"] == "completed" for t in frozen["tasks"]))
        self.assertEqual(
            (self.task_dir / ep.PLANS_DIR / "1" / ep.EVENTS_FILE).read_text(
                encoding="utf-8"
            ),
            frozen_events,
        )
        self.assertTrue(
            (self.task_dir / ep.PLANS_DIR / "1" / "final-report.md").is_file()
        )
        self.assertFalse((self.task_dir / "final-report.md").exists())
        live = self.read_live_plan()
        self.assertEqual(live["status"], "proposed")
        sequel_events = [
            json.loads(line)
            for line in (
                self.task_dir / ep.PLANS_DIR / "2" / ep.EVENTS_FILE
            ).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(sequel_events[0]["event"], "plan_sequel")
        self.assertEqual((sequel_events[0]["from"], sequel_events[0]["to"]), (1, 2))
        self.assertEqual(sequel_events[0]["reason"], "requirement continues")

    def test_sequel_rollback_clears_empty_freeze_dir_so_retry_works(self) -> None:
        self.complete_report_plan()
        original_plan = (self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8")
        original_events = (self.task_dir / ep.EVENTS_FILE).read_text(encoding="utf-8")
        original_report = (self.task_dir / "final-report.md").read_text(encoding="utf-8")
        real_atomic = ep._atomic_write

        def boom(path, text):
            raise OSError("disk full")

        with patch.object(ep, "_atomic_write", boom):
            with self.assertRaises(ep.PlanError) as ctx:
                self.sequel_to()
        self.assertIn("sequel failed", str(ctx.exception))
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())
        self.assertEqual(
            (self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8"), original_plan
        )
        self.assertEqual(
            (self.task_dir / ep.EVENTS_FILE).read_text(encoding="utf-8"),
            original_events,
        )
        self.assertEqual(
            (self.task_dir / "final-report.md").read_text(encoding="utf-8"),
            original_report,
        )
        out = self.sequel_to()
        self.assertIn("live plan is now 2", out)
        self.assertIsNotNone(real_atomic)

    def test_sequel_refused_while_phases_open(self) -> None:
        self.approve()
        ep.cmd_start(self.root, self.task_dir, "discover")
        with self.assertRaises(ep.PlanError) as ctx:
            self.sequel_to()
        self.assertIn("open phase", str(ctx.exception))
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())

    def test_sequel_requires_terminal_report_phase(self) -> None:
        # BASE_PLAN has no report phase; a fully completed plan without one
        # cannot open a sequel.
        self.start_edit()
        self.record("edit", "app-build")
        ep.cmd_done(self.root, self.task_dir, "edit")
        with self.assertRaises(ep.PlanError) as ctx:
            self.sequel_to()
        self.assertIn("terminal report", str(ctx.exception))
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())

    def test_third_sequel_yields_live_three_with_frozen_history(self) -> None:
        # No hard-coded limit of two plans: the third sequel is just as legal.
        self.complete_report_plan()
        self.sequel_to("second plan")
        frozen_one_events = (
            self.task_dir / ep.PLANS_DIR / "1" / ep.EVENTS_FILE
        ).read_text(encoding="utf-8")
        (self.task_dir / ep.PLANS_DIR / "2" / ep.PLAN_FILE).write_text(
            json.dumps(copy.deepcopy(SEQ_PLAN), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.approve()
        self.complete_seq_plan()
        out = self.sequel_to("third plan")
        self.assertIn("live plan is now 3", out)
        pointer = json.loads((self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8"))
        self.assertEqual(pointer["live"], 3)
        self.assertTrue(
            (self.task_dir / ep.PLANS_DIR / "2" / "final-report.md").is_file()
        )
        self.assertTrue(
            (self.task_dir / ep.PLANS_DIR / "3" / ep.PLAN_FILE).is_file()
        )
        self.assertEqual(
            (self.task_dir / ep.PLANS_DIR / "1" / ep.EVENTS_FILE).read_text(
                encoding="utf-8"
            ),
            frozen_one_events,
        )
        self.assertEqual(self.read_live_plan()["status"], "proposed")

    def test_status_and_protocol_show_only_the_live_plan(self) -> None:
        self.complete_report_plan()
        self.sequel_to()
        text = ep.format_status(self.task_dir, self.root)
        self.assertIn("(live 2)", text)
        self.assertIn("frozen plans:", text)
        self.assertIn("plan 1: 3/3 completed", text)
        self.assertNotIn("[   completed] discover", text)
        self.assertIn("discover-x", text)
        protocol = ep.plan_protocol_block(self.root, self.task_dir)
        self.assertIn("Live plan 2 files:", protocol)
        self.assertIn("live pointer", protocol)
        self.assertIn("frozen read-only history", protocol)

    def test_frozen_plan_directories_refuse_mutations(self) -> None:
        self.complete_report_plan()
        self.sequel_to()
        frozen_dir = self.task_dir / ep.PLANS_DIR / "1"
        self.assertTrue(ep.is_plan_history_dir(frozen_dir))
        calls = (
            lambda: ep.cmd_start(self.root, frozen_dir, "edit"),
            lambda: ep.cmd_record(self.root, frozen_dir, "edit", "pass",
                                  "cmd", 0, None, "ok", "app-build"),
            lambda: ep.cmd_done(self.root, frozen_dir, "edit"),
            lambda: ep.cmd_block(self.root, frozen_dir, "edit", "reason"),
            lambda: ep.cmd_revise(self.root, frozen_dir, "reopen"),
            lambda: ep.cmd_validate(self.root, frozen_dir),
            lambda: ep.cmd_sequel(self.root, frozen_dir, "next"),
        )
        for call in calls:
            with self.subTest(call=call), self.assertRaises(ep.PlanError) as ctx:
                call()
            self.assertIn("plan history", str(ctx.exception))
        frozen = json.loads(self.frozen_plan_path(1).read_text(encoding="utf-8"))
        self.assertEqual(frozen["status"], "approved")
        self.assertEqual(frozen["revision"], 1)
        self.assertEqual(self.read_live_plan()["status"], "proposed")

    def test_pointer_fail_closed_variants(self) -> None:
        self.complete_report_plan()
        self.sequel_to()
        pointer_file = self.task_dir / ep.PLAN_FILE
        cases = [
            ({"schema": 3, "live": 9}, "plans/9"),
            ({"schema": 3, "live": "2"}, "integer"),
            ({"schema": 3, "live": 2, "tasks": []}, "mixes"),
            ("[1, 2]", "JSON object"),
            ("{not json", "not valid JSON"),
        ]
        for payload, needle in cases:
            text = payload if isinstance(payload, str) else json.dumps(payload)
            pointer_file.write_text(text, encoding="utf-8")
            with self.subTest(payload=payload):
                with self.assertRaises(ep.PlanError) as ctx:
                    ep.load_plan(self.task_dir)
                self.assertIn(needle, str(ctx.exception))
                with self.assertRaises(ep.PlanError):
                    ep.cmd_start(self.root, self.task_dir, "discover-x")
        pointer_file.write_text(
            json.dumps({"schema": 3, "live": 2}), encoding="utf-8"
        )
        live_plan = self.task_dir / ep.PLANS_DIR / "2" / ep.PLAN_FILE
        live_plan.write_text(json.dumps({"schema": 3, "live": 3}), encoding="utf-8")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.resolve_live_plan(self.task_dir)
        self.assertIn("itself a pointer", str(ctx.exception))
        live_plan.write_text(json.dumps({"schema": 3, "goal": "x"}), encoding="utf-8")
        with self.assertRaises(ep.PlanError) as ctx:
            ep.resolve_live_plan(self.task_dir)
        self.assertIn("not a real plan", str(ctx.exception))

    def test_ambiguous_or_missing_pointer_fails_closed(self) -> None:
        self.complete_report_plan()
        self.sequel_to()
        original = (self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8")
        root_plan = copy.deepcopy(BASE_PLAN)
        root_plan["status"] = "approved"
        (self.task_dir / ep.PLAN_FILE).write_text(
            json.dumps(root_plan, indent=2), encoding="utf-8"
        )
        with self.assertRaises(ep.PlanError) as ctx:
            ep.resolve_live_plan(self.task_dir)
        self.assertIn("ambiguous", str(ctx.exception))
        (self.task_dir / ep.PLAN_FILE).unlink()
        with self.assertRaises(ep.PlanError) as ctx:
            ep.resolve_live_plan(self.task_dir)
        self.assertIn("pointer is missing", str(ctx.exception))
        (self.task_dir / ep.PLAN_FILE).write_text(original, encoding="utf-8")
        self.assertEqual(ep.resolve_live_plan(self.task_dir)[0], 2)

    def test_revise_never_creates_a_sequel_and_report_stays_terminal(self) -> None:
        self.complete_report_plan()
        ep.cmd_revise(self.root, self.task_dir, "reopen the live plan")
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())
        plan = self.read_live_plan()
        self.assertEqual(plan["revision"], 2)
        self.assertEqual(plan["status"], "proposed")
        # revise resets the terminal report to pending; rewriting it into a
        # normal phase is still refused.
        report = next(t for t in plan["tasks"] if t["id"] == "verify-final")
        self.assertEqual(report["status"], "pending")
        report["verification"] = {"level": "minimal", "required_checks": ["build"]}
        ep.plan_path(self.task_dir).write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with self.assertRaises(ep.PlanError) as ctx:
            ep.cmd_validate(self.root, self.task_dir)
        self.assertIn("must stay level=report", str(ctx.exception))

    def test_sequel_cli_flow(self) -> None:
        self.complete_report_plan()
        with patch.object(plan_cli, "get_repo_root", return_value=self.root), \
             patch.object(plan_cli, "resolve_task_dir", return_value=self.task_dir):
            exit_code = plan_cli.main([
                "--task", str(self.task_dir), "sequel",
                "--reason", "next live plan",
            ])
        self.assertEqual(exit_code, 0)
        pointer = json.loads((self.task_dir / ep.PLAN_FILE).read_text(encoding="utf-8"))
        self.assertEqual(pointer["live"], 2)

    def test_revise_cli_flow_after_completion_stays_in_place(self) -> None:
        # AC1/AC6: the CLI `revise` subcommand is the completion-state exit —
        # no sequel pointer is created, the live plan reopens as proposed.
        self.complete_report_plan()
        with patch.object(plan_cli, "get_repo_root", return_value=self.root), \
             patch.object(plan_cli, "resolve_task_dir", return_value=self.task_dir):
            exit_code = plan_cli.main([
                "--task", str(self.task_dir), "revise",
                "--reason", "same requirement continues",
            ])
        self.assertEqual(exit_code, 0)
        self.assertFalse((self.task_dir / ep.PLANS_DIR).exists())
        plan = self.read_live_plan()
        self.assertEqual(plan["revision"], 2)
        self.assertEqual(plan["status"], "proposed")
        report = next(t for t in plan["tasks"] if t["id"] == "verify-final")
        self.assertEqual(report["status"], "pending")

    # -- template -----------------------------------------------------------

    def test_task_flag_accepted_after_subcommand(self) -> None:
        # F7: --task works both before and after the subcommand.
        self.approve()
        with patch.object(plan_cli, "get_repo_root", return_value=self.root):
            self.assertEqual(
                plan_cli.main(["status", "--task", str(self.task_dir)]), 0
            )
            self.assertEqual(
                plan_cli.main(["--task", str(self.task_dir), "status"]), 0
            )

    def test_template_validates(self) -> None:
        # The printed skeleton must be a schema-3 plan that survives validation
        # once placeholders get legal concrete values.
        self.assertEqual(json.loads(ep.template_text())["schema"], 3)
        text = ep.template_text()
        replacements = {
            "<task-path>": ".trellis/tasks/demo",
            "<one-line goal>": "template smoke",
            "<phase title>": "template phase",
            "<what must be established>": "establish",
            "<what must change>": "change",
            "<what proves the task>": "prove",
            "<repo-relative glob>": "src/",
            "<path glob>": "src/a.c",
            "<path>": "src/",
            "<check-id>": "tmpl-check",
            "<why this phase is pure read-only/analysis>": "read-only template phase",
        }
        for placeholder, value in replacements.items():
            text = text.replace(placeholder, value)
        self.assertNotIn("<", text, "unreplaced placeholder in template")
        self.write_plan(json.loads(text))
        self.approve()


if __name__ == "__main__":
    unittest.main()
