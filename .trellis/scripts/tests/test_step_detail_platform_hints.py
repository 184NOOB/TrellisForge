"""Drift-prevention tests for Step detail platform hints and task.py step ids.

Covers, across the Claude / Codex / OpenCode delivery chain:

- the three SessionStart "Step detail" hint strings each pass their own
  ``--platform`` flag and never another platform's flag;
- every ``--step <id>`` hint printed by ``task.py`` is resolvable (no more
  bare ``--step 1`` that the CLI rejects with exit code 2);
- the Loading Step Detail section keeps its three platform examples (a
  deliberately redundant second lock next to
  ``test_codex_native_wait_contract.py``).

Resolution choice: ``task.py`` hint ids are checked with the in-process
``get_step`` from the template's ``common.workflow_phase``, after patching
``common.workflow_phase.get_repo_root`` to ``REPO_ROOT`` so a discover run from a
parent TrellisForge checkout cannot resolve the *root* workflow instead of
the template's. One real-CLI subprocess test (``cwd=REPO_ROOT``) still
locks the user-visible ``--step 1.1`` path at the template root.

No test here spawns or waits for a real agent, and none invokes
``trellis channel``.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


# Template root: when installed into a downstream repo this resolves to that
# repo root, so tests must never hardcode templates/embedded-c-overlay.
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import workflow_phase as wp  # noqa: E402


CLAUDE_HOOK = REPO_ROOT / ".claude" / "hooks" / "session-start.py"
CODEX_HOOK = REPO_ROOT / ".codex" / "hooks" / "session-start.py"
OPENCODE_SESSION_UTILS = REPO_ROOT / ".opencode" / "lib" / "session-utils.js"
TASK_PY = REPO_ROOT / ".trellis" / "scripts" / "task.py"
WORKFLOW = REPO_ROOT / ".trellis" / "workflow.md"

HINT_STRUCTURE = "Full guide: .trellis/workflow.md. Step detail:"
ALL_PLATFORMS = ("claude", "codex", "opencode")

# task.py may print more than one step hint in the future; collect them all.
STEP_ARG_RE = re.compile(r"--step\s+(\d+(?:\.\d+)*)")
# Boundary regex: `--step 1.1` itself contains the `--step 1` substring, so a
# naive substring check would be vacuously true. The lookahead rejects both
# `.` and digits after the bare `1`.
BARE_STEP_1_RE = re.compile(r"--step 1(?![.\d])")


def run_step(*args: str) -> subprocess.CompletedProcess:
    """Run the real template CLI in the template root.

    PYTHONIOENCODING plus explicit utf-8 decoding keeps Chinese assertions
    alive on Windows GBK pipes.
    """
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPTS_DIR / "get_context.py"),
            "--mode",
            "phase",
            *args,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


class TestStepDetailPlatformHints(unittest.TestCase):
    """Each platform's SessionStart hint must pass its own --platform."""

    def _assert_hint(
        self, path: Path, platform: str, forbidden: tuple[str, ...]
    ) -> None:
        text = path.read_text(encoding="utf-8")
        self.assertIn(HINT_STRUCTURE, text)
        self.assertIn(
            f"--mode phase --step <X.Y> --platform {platform}", text
        )
        for other in forbidden:
            with self.subTest(other=other):
                self.assertNotIn(f"--platform {other}", text)

    def test_claude_hint_passes_claude_platform(self) -> None:
        self._assert_hint(CLAUDE_HOOK, "claude", ("codex", "opencode"))

    def test_codex_hint_passes_codex_platform(self) -> None:
        self._assert_hint(CODEX_HOOK, "codex", ("claude", "opencode"))

    def test_opencode_hint_passes_opencode_platform(self) -> None:
        self._assert_hint(
            OPENCODE_SESSION_UTILS, "opencode", ("claude", "codex")
        )


class TestTaskPyStepHints(unittest.TestCase):
    """Every step hint task.py prints must be resolvable by get_step."""

    def test_every_step_hint_resolves_through_get_step(self) -> None:
        text = TASK_PY.read_text(encoding="utf-8")
        step_ids = sorted(set(STEP_ARG_RE.findall(text)))
        self.assertTrue(step_ids, "task.py prints no --step hint")
        for step_id in step_ids:
            with self.subTest(step_id=step_id):
                with patch("common.workflow_phase.get_repo_root", return_value=REPO_ROOT):
                    resolved = wp.get_step(step_id)
                self.assertTrue(
                    resolved,
                    f"task.py hint --step {step_id} does not resolve",
                )

    def test_no_bare_step_1_hint_remains(self) -> None:
        text = TASK_PY.read_text(encoding="utf-8")
        match = BARE_STEP_1_RE.search(text)
        self.assertIsNone(
            match,
            "task.py still prints the unresolvable bare --step 1 hint",
        )

    def test_cli_resolves_the_step_hint_at_template_root(self) -> None:
        result = run_step("--step", "1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("#### 1.1", result.stdout)


class TestLoadingStepDetailLock(unittest.TestCase):
    """Second lock on the three platform examples (first: Codex contract tests)."""

    def test_loading_step_detail_keeps_all_three_platform_examples(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"### Loading Step Detail\n(.*?)(?=\n---|\n## )", text, re.DOTALL
        )
        self.assertIsNotNone(match, "Loading Step Detail section not found")
        section = match.group(1)
        for platform in ALL_PLATFORMS:
            with self.subTest(platform=platform):
                self.assertIn(f"--platform {platform}", section)


if __name__ == "__main__":
    unittest.main()
