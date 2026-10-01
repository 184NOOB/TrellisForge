"""Contract tests for the MM-DD-HHmm task-directory prefix and minute stagger.

Covers:
- ``common.paths.generate_task_date_prefix`` format and wall-clock agreement.
- ``task_store.cmd_create`` slug-guard branches for pasted date prefixes
  (issue #377): today's full prefix / legacy date-only prefix strip, non-today reject,
  invalid HHmm passthrough.
- ``task_store._allocate_task_prefix`` same-minute stagger, occupied-minute
  skip, midnight rollover, and the defensive exists-warning fallback.
- Directory-name sort order equals creation order.

Every test drives the real ``cmd_create`` against a TemporaryDirectory fake
repo root; nothing here reads or writes a real repository task store.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import common.task_store as ts  # noqa: E402
from common.paths import generate_task_date_prefix  # noqa: E402


# Fixed base prefix used by the create harness; never derives from the real
# clock, so guard branches are deterministic. The real date is irrelevant
# because the guard compares against this patched base prefix.
FIXED_PREFIX = "09-22-1435"


def _shift_prefix(prefix: str, minutes: int) -> str:
    """Shift an MM-DD-HHmm prefix by N minutes.

    Uses an explicit leap year so the helper stays valid for 02-29 inputs and
    avoids the year-less ``strptime`` deprecation warning.
    """
    month, day, hhmm = prefix.split("-")
    base = datetime(2000, int(month), int(day), int(hhmm[:2]), int(hhmm[2:]))
    return (base + timedelta(minutes=minutes)).strftime("%m-%d-%H%M")


class _CreateHarness(unittest.TestCase):
    """Drive ``task_store.cmd_create`` against a temporary fake repo root."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.tasks_dir = self.root / ".trellis" / "tasks"

    def _args(self, slug: str, **overrides: object) -> argparse.Namespace:
        args = argparse.Namespace(
            title="Demo task",
            slug=slug,
            description="",
            assignee="tester",
            priority="P2",
            parent=None,
            package=None,
            meta=None,
            base_branch=None,
            no_start=True,
        )
        for key, value in overrides.items():
            setattr(args, key, value)
        return args

    def run_create(
        self, slug: str, base_prefix: str = FIXED_PREFIX, **overrides: object
    ) -> tuple[int, str, str]:
        args = self._args(slug, **overrides)
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(ts, "get_repo_root", return_value=self.root), patch.object(
            ts, "run_git", return_value=(0, "main\n", "")
        ), patch.object(
            ts, "resolve_default_branch", return_value="main"
        ), patch.object(
            ts, "generate_task_date_prefix", return_value=base_prefix
        ), contextlib.redirect_stdout(
            stdout
        ), contextlib.redirect_stderr(
            stderr
        ):
            code = ts.cmd_create(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def task_dirs(self) -> list[str]:
        if not self.tasks_dir.is_dir():
            return []
        return sorted(
            p.name
            for p in self.tasks_dir.iterdir()
            if p.is_dir() and p.name != "archive"
        )

    def read_task_json(self, dir_name: str) -> dict:
        raw = (self.tasks_dir / dir_name / "task.json").read_text(encoding="utf-8")
        return json.loads(raw)


class DatePrefixFormatTests(unittest.TestCase):
    def test_prefix_is_mm_dd_hhmm_and_matches_current_time(self) -> None:
        before = datetime.now().strftime("%m-%d-%H%M")
        prefix = generate_task_date_prefix()
        after = datetime.now().strftime("%m-%d-%H%M")
        self.assertRegex(prefix, r"^\d{2}-\d{2}-\d{4}$")
        # Tolerate a minute rollover between the two samples.
        self.assertIn(prefix, (before, after))


class SlugGuardTests(_CreateHarness):
    def test_today_full_prefix_is_stripped_with_warning(self) -> None:
        code, _, stderr = self.run_create(f"{FIXED_PREFIX}-pasted-name")
        self.assertEqual(code, 0, stderr)
        self.assertIn("normalized", stderr)
        self.assertEqual(self.task_dirs(), [f"{FIXED_PREFIX}-pasted-name"])
        data = self.read_task_json(f"{FIXED_PREFIX}-pasted-name")
        self.assertEqual(data["id"], "pasted-name")
        self.assertEqual(data["name"], "pasted-name")

    def test_today_legacy_mm_dd_prefix_is_stripped_with_warning(self) -> None:
        code, _, stderr = self.run_create("09-22-legacy-name")
        self.assertEqual(code, 0, stderr)
        self.assertIn("normalized", stderr)
        self.assertEqual(self.task_dirs(), [f"{FIXED_PREFIX}-legacy-name"])

    def test_non_today_prefix_is_rejected_without_creating(self) -> None:
        code, _, stderr = self.run_create("01-05-old-name")
        self.assertEqual(code, 1)
        self.assertIn("Error", stderr)
        self.assertEqual(self.task_dirs(), [])

    def test_today_other_minute_prefix_is_rejected(self) -> None:
        code, _, stderr = self.run_create("09-22-1030-other-task")
        self.assertEqual(code, 1)
        self.assertIn("Error", stderr)
        self.assertEqual(self.task_dirs(), [])

    def test_invalid_hhmm_falls_through_as_plain_slug(self) -> None:
        code, _, stderr = self.run_create("09-22-2461-weird")
        self.assertEqual(code, 0, stderr)
        self.assertNotIn("normalized", stderr)
        self.assertEqual(self.task_dirs(), [f"{FIXED_PREFIX}-09-22-2461-weird"])

    def test_created_at_stays_real_date(self) -> None:
        before = datetime.now().strftime("%Y-%m-%d")
        code, _, stderr = self.run_create("plain-slug")
        after = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(code, 0, stderr)
        data = self.read_task_json(f"{FIXED_PREFIX}-plain-slug")
        self.assertRegex(data["createdAt"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn(data["createdAt"], (before, after))


class PrefixStaggerTests(_CreateHarness):
    def test_same_minute_creates_take_successive_minutes(self) -> None:
        for slug in ("first", "second", "third"):
            code, _, stderr = self.run_create(slug)
            self.assertEqual(code, 0, stderr)
        self.assertEqual(
            self.task_dirs(),
            [
                f"{FIXED_PREFIX}-first",
                f"{_shift_prefix(FIXED_PREFIX, 1)}-second",
                f"{_shift_prefix(FIXED_PREFIX, 2)}-third",
            ],
        )

    def test_occupied_minute_is_skipped(self) -> None:
        code, _, stderr = self.run_create("first")
        self.assertEqual(code, 0, stderr)
        (self.tasks_dir / f"{_shift_prefix(FIXED_PREFIX, 1)}-preset").mkdir()
        code, _, stderr = self.run_create("second")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            self.task_dirs(),
            [
                f"{FIXED_PREFIX}-first",
                f"{_shift_prefix(FIXED_PREFIX, 1)}-preset",
                f"{_shift_prefix(FIXED_PREFIX, 2)}-second",
            ],
        )

    def test_stagger_crosses_midnight(self) -> None:
        before = datetime.now().strftime("%Y-%m-%d")
        code, _, stderr = self.run_create("late-first", base_prefix="09-22-2359")
        self.assertEqual(code, 0, stderr)
        code, _, stderr = self.run_create("late-second", base_prefix="09-22-2359")
        after = datetime.now().strftime("%Y-%m-%d")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(
            self.task_dirs(),
            ["09-22-2359-late-first", "09-23-0000-late-second"],
        )
        data = self.read_task_json("09-23-0000-late-second")
        self.assertIn(data["createdAt"], (before, after))

    def test_directory_sort_order_matches_creation_order(self) -> None:
        created: list[str] = []
        for slug in ("alpha", "bravo", "charlie"):
            code, stdout, stderr = self.run_create(slug)
            self.assertEqual(code, 0, stderr)
            created.append(Path(stdout.strip()).name)
        self.assertEqual(self.task_dirs(), created)
        self.assertEqual(sorted(created), created)

    def test_occupied_fallback_warns_when_allocation_reuses_prefix(self) -> None:
        # The defensive fallback (allocation returns an occupied prefix) is
        # unreachable through the real allocator, so drive it via a patch and
        # keep the existing exists-warning path covered.
        occupied = f"{FIXED_PREFIX}-defense"
        (self.tasks_dir / occupied).mkdir(parents=True)
        args = self._args("defense")
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(ts, "get_repo_root", return_value=self.root), patch.object(
            ts, "run_git", return_value=(0, "main\n", "")
        ), patch.object(
            ts, "resolve_default_branch", return_value="main"
        ), patch.object(
            ts, "generate_task_date_prefix", return_value=FIXED_PREFIX
        ), patch.object(
            ts, "_allocate_task_prefix", return_value=FIXED_PREFIX
        ), contextlib.redirect_stdout(
            stdout
        ), contextlib.redirect_stderr(
            stderr
        ):
            code = ts.cmd_create(args)
        self.assertEqual(code, 0, stderr.getvalue())
        self.assertIn("already exists", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()