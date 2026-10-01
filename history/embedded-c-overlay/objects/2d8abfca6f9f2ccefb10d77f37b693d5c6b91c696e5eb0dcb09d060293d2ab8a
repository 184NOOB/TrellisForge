from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.planning_gate import VALID_REVIEW_LEVELS, validate_planning_gate
from common.task_store import _default_prd_content


READY_PRD = """# Example

## Workflow Settings

- Review level: standard

## Goal

Example goal.

## Spec References

- `.trellis/spec/example/guideline.md` — example constraint.

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
"""

SEED_MANIFEST = json.dumps({"_example": "seed row"}, ensure_ascii=False)
CURATED_ENTRY = json.dumps(
    {"file": ".trellis/spec/example/guideline.md", "reason": "example"},
    ensure_ascii=False,
)


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

    def _write_manifest(self, task_dir: Path, name: str, lines: list[str]) -> None:
        (task_dir / name).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _platform_root(self, root: Path) -> Path:
        (root / ".claude").mkdir()
        return root

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

    def test_five_valid_review_levels_pass_gate(self) -> None:
        self.assertEqual(
            VALID_REVIEW_LEVELS,
            ("light", "standard", "reinforced", "comprehensive", "strict"),
        )
        for level in VALID_REVIEW_LEVELS:
            with self.subTest(level=level):
                prd = READY_PRD.replace("Review level: standard", f"Review level: {level}")
                with tempfile.TemporaryDirectory() as tmp:
                    task_dir = self._task(
                        Path(tmp),
                        meta={"planning_ready": True, "plan_approved": True},
                        prd=prd,
                    )
                    result = validate_planning_gate(task_dir)
                    self.assertTrue(result.ok, (level, result.errors))

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
            level_errors = [e for e in result.errors if "Review level" in e]
            self.assertTrue(level_errors)
            message = " ".join(level_errors)
            for level in VALID_REVIEW_LEVELS:
                self.assertIn(level, message)

    def test_missing_review_level_section_blocks_start(self) -> None:
        prd = READY_PRD.replace("## Workflow Settings\n\n- Review level: standard\n\n", "")
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

    # ------------------------------------------------------------------
    # Spec References check (A)
    # ------------------------------------------------------------------

    def test_missing_spec_references_section_blocks_start(self) -> None:
        prd = READY_PRD.replace(
            "## Spec References\n\n- `.trellis/spec/example/guideline.md` — example constraint.\n\n",
            "",
        )
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
                prd=prd,
            )
            result = validate_planning_gate(task_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("Spec References" in error for error in result.errors))

    def test_empty_spec_references_section_blocks_start(self) -> None:
        prd = READY_PRD.replace(
            "- `.trellis/spec/example/guideline.md` — example constraint.",
            "<!-- List consulted specs here. -->",
        )
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
                prd=prd,
            )
            result = validate_planning_gate(task_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("Spec References" in error for error in result.errors))

    def test_spec_references_with_entry_passes_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
            )
            result = validate_planning_gate(task_dir)
            self.assertTrue(result.ok, result.errors)

    def test_default_prd_skeleton_declares_empty_spec_references_section(self) -> None:
        prd = _default_prd_content("Example task", "Goal text.")
        self.assertIn("## Spec References", prd)
        section = prd.split("## Spec References", 1)[1].split("\n## ", 1)[0]
        self.assertNotRegex(
            section,
            re.compile(r"^[ \t]*-[ \t]+", re.MULTILINE),
            "the seed skeleton must not carry a placeholder list item that "
            "would satisfy the Spec References check",
        )
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = self._task(
                Path(tmp),
                meta={"planning_ready": True, "plan_approved": True},
                prd=prd,
            )
            result = validate_planning_gate(task_dir)
            self.assertFalse(result.ok)
            self.assertTrue(any("Spec References" in error for error in result.errors))

    # ------------------------------------------------------------------
    # Curated manifest check (B)
    # ------------------------------------------------------------------

    def test_seed_only_manifests_block_start_on_subagent_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            self._write_manifest(task_dir, "implement.jsonl", [SEED_MANIFEST])
            self._write_manifest(task_dir, "check.jsonl", [SEED_MANIFEST])
            self._platform_root(root)
            result = validate_planning_gate(task_dir, root)
            self.assertFalse(result.ok)
            message = " ".join(result.errors)
            self.assertIn("implement.jsonl", message)
            self.assertIn("check.jsonl", message)

    def test_missing_manifests_block_start_on_subagent_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            self._platform_root(root)
            result = validate_planning_gate(task_dir, root)
            self.assertFalse(result.ok)
            message = " ".join(result.errors)
            self.assertIn("implement.jsonl is missing", message)
            self.assertIn("check.jsonl is missing", message)

    def test_curated_manifests_pass_on_subagent_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            self._write_manifest(task_dir, "implement.jsonl", [CURATED_ENTRY])
            self._write_manifest(task_dir, "check.jsonl", [CURATED_ENTRY])
            self._platform_root(root)
            result = validate_planning_gate(task_dir, root)
            self.assertTrue(result.ok, result.errors)

    def test_no_subagent_platform_skips_jsonl_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            self._write_manifest(task_dir, "implement.jsonl", [SEED_MANIFEST])
            self._write_manifest(task_dir, "check.jsonl", [SEED_MANIFEST])
            result = validate_planning_gate(task_dir, root)
            self.assertTrue(result.ok, result.errors)

    def test_repo_root_absent_skips_jsonl_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            self._write_manifest(task_dir, "implement.jsonl", [SEED_MANIFEST])
            self._write_manifest(task_dir, "check.jsonl", [SEED_MANIFEST])
            self._platform_root(root)
            result = validate_planning_gate(task_dir)
            self.assertTrue(result.ok, result.errors)

    def test_corrupt_manifest_line_blocks_start(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            self._write_manifest(task_dir, "implement.jsonl", [CURATED_ENTRY, "{not json"])
            self._write_manifest(task_dir, "check.jsonl", [CURATED_ENTRY])
            self._platform_root(root)
            result = validate_planning_gate(task_dir, root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("not valid JSON" in error for error in result.errors),
                result.errors,
            )

    def test_manifest_entry_with_blank_file_does_not_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task_dir = self._task(root, meta={"planning_ready": True, "plan_approved": True})
            blank_entry = json.dumps({"file": "   ", "reason": "blank"}, ensure_ascii=False)
            self._write_manifest(task_dir, "implement.jsonl", [blank_entry])
            self._write_manifest(task_dir, "check.jsonl", [CURATED_ENTRY])
            self._platform_root(root)
            result = validate_planning_gate(task_dir, root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("implement.jsonl must contain at least one curated entry" in error for error in result.errors),
                result.errors,
            )


if __name__ == "__main__":
    unittest.main()
