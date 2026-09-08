"""Regression tests for main-session and sub-agent active-task isolation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.active_task import resolve_active_task  # noqa: E402


class ActiveTaskSessionIsolationTests(unittest.TestCase):
    def _repo_with_single_old_session(self, root: Path) -> str:
        task_ref = ".trellis/tasks/08-03-port-sd-card"
        task_dir = root / task_ref
        task_dir.mkdir(parents=True)
        (task_dir / "task.json").write_text(
            json.dumps({"id": "08-03-port-sd-card", "status": "in_progress"}),
            encoding="utf-8",
        )

        sessions_dir = root / ".trellis" / ".runtime" / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "codex_old.json").write_text(
            json.dumps({"current_task": task_ref}),
            encoding="utf-8",
        )
        return task_ref

    def test_main_session_without_identity_does_not_borrow_old_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            self._repo_with_single_old_session(repo)

            active = resolve_active_task(
                repo,
                {},
                platform="codex",
                allow_environment_context=False,
            )

            self.assertIsNone(active.task_path)
            self.assertEqual("ambiguous", active.source_type)

    def test_exact_new_session_without_pointer_is_no_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            self._repo_with_single_old_session(repo)

            active = resolve_active_task(
                repo,
                {"session_id": "new-session"},
                platform="codex",
                allow_environment_context=False,
            )

            self.assertIsNone(active.task_path)
            self.assertEqual("none", active.source_type)
            self.assertIsNotNone(active.context_key)

    def test_explicit_subagent_fallback_can_use_sole_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            task_ref = self._repo_with_single_old_session(repo)

            active = resolve_active_task(
                repo,
                {"session_id": "pull-based-child-session"},
                platform="copilot",
                allow_single_session_fallback=True,
                allow_environment_context=False,
            )

            self.assertEqual(task_ref, active.task_path)
            self.assertEqual("session-fallback", active.source_type)
            self.assertEqual("codex_old", active.context_key)


if __name__ == "__main__":
    unittest.main()
