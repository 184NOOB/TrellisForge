"""Contract tests for the small-patch bypass and completion-state reopen rules.

These lock the workflow / implement-agent wording that lets a small patch
bypass plan.py and that reopens a fully completed live plan in place via
`plan.py revise` (unmodified completed phases stay completed, the terminal
report resets to pending); `plan.py sequel` stays an explicit compatibility
command for opening a separate plan book. They also cover the live-plan
resolution surfaces the wording depends on (completion-state protocol block,
breadcrumb/status, Claude PreToolUse reminder).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import execution_plan as ep  # noqa: E402


def load_module(relative_path: str, name: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized(relative_path: str) -> str:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", text)


IMPLEMENT_AGENTS = (
    ".trellis/agents/implement.md",
    ".claude/agents/trellis-implement.md",
    ".codex/agents/trellis-implement.toml",
    ".opencode/agents/trellis-implement.md",
)

CHECK_AGENTS = (
    ".trellis/agents/check.md",
    ".claude/agents/trellis-check.md",
    ".codex/agents/trellis-check.toml",
    ".opencode/agents/trellis-check.md",
)


def completed_plan() -> dict:
    return {
        "schema": 3,
        "task": ".trellis/tasks/demo",
        "revision": 1,
        "status": "approved",
        "audit": {"required": True, "file": "execution-events.jsonl"},
        "created_by": "trellis-implement",
        "goal": "demo",
        "constraints": {
            "forbidden_git_operations": ["commit"],
            "max_tasks": 8,
            "max_edits_per_file": 2,
            "allow_parallel_tasks": False,
        },
        "tasks": [
            {
                "id": "edit",
                "title": "edit code",
                "status": "completed",
                "objective": "change code",
                "depends_on": [],
                "scope": {"read": ["src/a.c"], "write": ["src/a.c"]},
                "verification": {"level": "minimal", "required_checks": ["build"]},
            },
            {
                "id": "verify-final",
                "title": "final acceptance",
                "status": "completed",
                "objective": "prove the task",
                "depends_on": ["edit"],
                "scope": {"read": ["src/"], "write": ["final-report.md"]},
                "verification": {
                    "level": "report",
                    "required_checks": ["build"],
                    "report_path": "final-report.md",
                },
            },
        ],
    }


class SmallPatchWorkflowContractTests(unittest.TestCase):
    def test_workflow_carries_small_patch_hard_rules(self) -> None:
        text = normalized(".trellis/workflow.md")
        self.assertIn("Small patch (hard rule, bypasses plan.py)", text)
        self.assertIn(
            "when the user explicitly says this is a small patch (`小修`) or says "
            "not to go through `plan.py`",
            text,
        )
        self.assertIn("no `revise`, no new phase, no new task", text)
        self.assertIn(
            "Blocking fixes from review or implementation default to a small patch",
            text,
        )
        self.assertIn(
            "only blocking work that is too much, messy, and complex enough to "
            "need new steps/checks/report justifies an in-place `revise`",
            text,
        )

    def test_workflow_carries_completion_state_exit(self) -> None:
        text = normalized(".trellis/workflow.md")
        self.assertIn("Completion-state exit", text)
        self.assertIn("a small patch touches no execution-plan file at all", text)
        self.assertIn("reopens the same live plan with `plan.py revise", text)
        self.assertIn("unmodified completed phases stay `completed`", text)
        self.assertIn("the terminal report resets to `pending`", text)
        self.assertIn("no longer the required completion-state exit", text)
        self.assertIn("opens a new Trellis task", text)
        self.assertNotIn("freezes the old plan", text)

    def test_workflow_gate_routes_by_plan_state_not_revise(self) -> None:
        text = normalized(".trellis/workflow.md")
        self.assertIn("Phase 2 source edits require an approved live", text)
        self.assertIn("while the live plan is open", text)
        self.assertIn(
            "follow the small-patch exit or reopen it in place with `plan.py revise`",
            text,
        )
        self.assertNotIn(
            "Phase 2 source edits require an approved `<task>/execution-plan.json`;",
            text,
        )

    def test_implement_agents_carry_the_same_contract(self) -> None:
        for relative in IMPLEMENT_AGENTS:
            with self.subTest(agent=relative):
                text = normalized(relative)
                self.assertIn("Small patch (hard rule, bypasses plan.py)", text)
                self.assertIn("never `revise`", text)
                self.assertIn("Completion-state reopen", text)
                self.assertIn("plan.py revise --reason", text)
                self.assertIn("terminal report resets to `pending`", text)
                self.assertIn("no longer the required completion-state exit", text)
                self.assertIn("Blocking", text)
                self.assertIn("default to", text)
                self.assertIn("frozen read-only history", text)
                self.assertIn("touch no execution-plan file at all", text)
                self.assertNotIn("Same-task sequel", text)

    def test_check_agents_reference_the_live_plan(self) -> None:
        for relative in CHECK_AGENTS:
            with self.subTest(agent=relative):
                text = normalized(relative)
                self.assertIn("live execution plan", text)
                self.assertIn("plans/<N>/execution-plan.json", text)
                self.assertIn("read-only history", text)
                self.assertIn("prior sequel books", text)
                self.assertIn("reopened in place with `plan.py revise`", text)
                self.assertIn("is not frozen", text)

    def test_plan_cli_help_exposes_sequel(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS_DIR / "plan.py"), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("sequel", result.stdout)


class PlanReminderHookContractTests(unittest.TestCase):
    """The Claude PreToolUse reminder resolves the live plan and advises the
    small-patch / in-place `revise` exit for a completed live plan."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".trellis" / "scripts").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / "src" / "a.c").write_text("x\n", encoding="utf-8")
        self.task_dir = self.root / ".trellis" / "tasks" / "demo"
        (self.task_dir / "task.json").parent.mkdir(parents=True, exist_ok=True)
        (self.task_dir / "plans" / "1").mkdir(parents=True)
        (self.task_dir / "plans" / "2").mkdir(parents=True)
        (self.task_dir / "task.json").write_text(
            json.dumps({"id": "demo", "status": "in_progress"}), encoding="utf-8"
        )
        (self.task_dir / ep.PLAN_FILE).write_text(
            json.dumps({"schema": 3, "live": 2}), encoding="utf-8"
        )
        for number in (1, 2):
            (self.task_dir / ep.PLANS_DIR / str(number) / ep.PLAN_FILE).write_text(
                json.dumps(completed_plan(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (self.task_dir / ep.PLANS_DIR / str(number) / ep.EVENTS_FILE).write_text(
                "", encoding="utf-8"
            )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_hook(self, target: Path) -> str:
        hook = load_module(
            ".claude/hooks/plan-pretool-reminder.py", "pretool_hook_contract"
        )
        hook.find_trellis_root = lambda _cwd: self.root
        import common.active_task as active_task

        original = active_task.resolve_active_task
        active_task.resolve_active_task = lambda *args, **kwargs: SimpleNamespace(
            task_path=str(self.task_dir), stale=False
        )
        payload = {
            "tool_name": "Edit",
            "cwd": str(self.root),
            "tool_input": {"file_path": str(target)},
        }
        output = io.StringIO()
        previous_stdin = sys.stdin
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(
                io.StringIO()
            ):
                sys.stdin = io.StringIO(json.dumps(payload))
                exit_code = hook.main()
        finally:
            sys.stdin = previous_stdin
            active_task.resolve_active_task = original
        self.assertEqual(exit_code, 0)
        text = output.getvalue().strip()
        if not text:
            return ""
        return json.loads(text)["systemMessage"]

    def test_completed_plan_edit_outside_task_advises_small_patch_or_revise(self) -> None:
        message = self._run_hook(self.root / "src" / "a.c")
        self.assertIn("fully completed", message)
        self.assertIn("small patch", message)
        self.assertIn("revise --reason", message)
        self.assertNotIn("sequel --reason", message)

    def test_pointer_and_frozen_history_tamper_are_reported(self) -> None:
        message = self._run_hook(self.task_dir / ep.PLAN_FILE)
        self.assertIn("live-plan pointer", message)
        message = self._run_hook(self.task_dir / ep.PLANS_DIR / "1" / ep.PLAN_FILE)
        self.assertIn("frozen plan history", message)
        message = self._run_hook(self.task_dir / ep.PLANS_DIR / "1" / ep.EVENTS_FILE)
        self.assertIn("frozen plan history", message)

    def test_completed_live_plan_rewrite_is_reported(self) -> None:
        message = self._run_hook(self.task_dir / ep.PLANS_DIR / "2" / ep.PLAN_FILE)
        self.assertIn("fully completed", message)
        self.assertIn("revise --reason", message)
        self.assertNotIn("sequel", message)

    def test_live_events_file_keeps_append_only_warning(self) -> None:
        message = self._run_hook(self.task_dir / ep.PLANS_DIR / "2" / ep.EVENTS_FILE)
        self.assertIn("append-only", message)


if __name__ == "__main__":
    unittest.main()