from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.planning_gate import validate_planning_gate


READY_PRD = """# Example

## Workflow Settings

- Review level: standard

## Goal

Example goal.

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
"""


class PlanningGateTests(unittest.TestCase):
    def _task(
        self,
        root: Path,
        *,
        status: str = "planning",
        meta: dict[str, object] | None = None,
        prd: str = READY_PRD,
    ) -> Path:
        task_dir = root / "task"
        task_dir.mkdir()
        (task_dir / "task.json").write_text(
            json.dumps({"status": status, "meta": meta or {}}, indent=2),
            encoding="utf-8",
        )
        (task_dir / "prd.md").write_text(prd, encoding="utf-8")
        return task_dir

    def test_ready_plan_may_have_zero_clarification_questions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
            )
            result = validate_planning_gate(task_dir)
            self.assertTrue(result.ok, result.errors)

    def test_missing_metadata_blocks_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(Path(tmp))
            result = validate_planning_gate(task_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("planning_ready" in error for error in result.errors))
            self.assertTrue(any("plan_approved" in error for error in result.errors))

    def test_unresolved_technical_decision_blocks_start(self) -> None:
        prd = READY_PRD.replace("Blocking technical decisions: 0", "Blocking technical decisions: 1")
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
                prd=prd,
            )
            result = validate_planning_gate(task_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("Blocking technical decisions" in error for error in result.errors))

    def test_invalid_review_level_blocks_start(self) -> None:
        prd = READY_PRD.replace("Review level: standard", "Review level: extreme")
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
                prd=prd,
            )
            result = validate_planning_gate(task_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("Review level" in error for error in result.errors))

    def test_in_progress_reattachment_skips_planning_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(Path(tmp), status="in_progress", prd="")
            result = validate_planning_gate(task_dir)
            self.assertTrue(result.ok, result.errors)


if __name__ == "__main__":
    unittest.main()
