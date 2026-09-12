"""Regression tests for main-session and sub-agent active-task isolation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]  # templates/embedded-c-overlay/
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.active_task import resolve_active_task, resolve_context_key  # noqa: E402


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


# Fixed session-id vectors that must produce identical context keys in the
# Python resolver (platform="opencode") and the OpenCode JS adapter. If these
# ever disagree, `task.py create` succeeds under one identity while the
# plugin prompts resolve `no_task` under the other — the cross-language
# isolation contract fails.
OPENCODE_KEY_VECTORS = (
    "ses_abc123",
    "weird id/../with chars!",
    "x" * 200,
    "  spaced  ",
    "ses_12345",
)

_JS_KEY_HARNESS = """
import { pathToFileURL } from "url";
const mod = await import(pathToFileURL(process.argv[2]).href);
const vectors = JSON.parse(process.argv[3]);
const out = {};
for (const v of vectors) out[v] = mod.contextKeyForSessionId(v);
const ctx = new mod.TrellisContext(process.cwd());
out.__override__ = ctx.getContextKey({ sessionID: "ses_abc123" }, { TRELLIS_CONTEXT_ID: "opencode_explicit_key" });
out.__env_session__ = ctx.getContextKey(null, { OPENCODE_SESSION_ID: "env_sess_42" });
out.__env_run__ = ctx.getContextKey(null, { OPENCODE_RUN_ID: "run/9" });
out.__input_beats_env__ = ctx.getContextKey({ sessionID: "ses_abc123" }, { OPENCODE_SESSION_ID: "env_sess_42" });
process.stdout.write(JSON.stringify(out));
"""

_NODE = shutil.which("node")


@unittest.skipIf(_NODE is None, "node is not available; the OpenCode JS adapter was NOT executed")
class OpenCodeSessionKeyTests(unittest.TestCase):
    """OpenCode platform keys: Python resolver == JS adapter, fail-closed."""

    def _py_key(self, session_id: str) -> str | None:
        saved = os.environ.pop("TRELLIS_CONTEXT_ID", None)
        try:
            return resolve_context_key({"sessionID": session_id}, platform="opencode")
        finally:
            if saved is not None:
                os.environ["TRELLIS_CONTEXT_ID"] = saved

    def test_py_opencode_key_format(self) -> None:
        self.assertEqual("opencode_ses_abc123", self._py_key("ses_abc123"))

    def test_js_adapter_matches_python_vectors(self) -> None:
        lib = TEMPLATE_ROOT / ".opencode" / "lib" / "trellis-context.js"
        self.assertTrue(lib.is_file(), f"missing OpenCode lib: {lib}")
        python_keys = {v: self._py_key(v) for v in OPENCODE_KEY_VECTORS}
        clean_keys = {
            "TRELLIS_CONTEXT_ID",
            "OPENCODE_SESSION_ID",
            "OPENCODE_SESSIONID",
            "OPENCODE_RUN_ID",
        }
        env_override = {k: v for k, v in os.environ.items() if k not in clean_keys}
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            for key in clean_keys:
                os.environ.pop(key, None)
            os.environ["TRELLIS_CONTEXT_ID"] = "opencode_explicit_key"
            expected_override = resolve_context_key({"sessionID": "ses_abc123"}, platform="opencode")
            os.environ.pop("TRELLIS_CONTEXT_ID")
            os.environ["OPENCODE_SESSION_ID"] = "env_sess_42"
            expected_env = resolve_context_key(None, platform="opencode")
            os.environ.pop("OPENCODE_SESSION_ID")
            os.environ["OPENCODE_RUN_ID"] = "run/9"
            expected_run = resolve_context_key(None, platform="opencode")

        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
            handle.write(_JS_KEY_HARNESS)
            script = handle.name
        try:
            result = subprocess.run(
                [_NODE, script, str(lib), json.dumps(OPENCODE_KEY_VECTORS)],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
                env=env_override,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            os.unlink(script)
        js = json.loads(result.stdout)
        for vector, key in python_keys.items():
            self.assertEqual(key, js[vector], f"key drift for vector {vector!r}")
        self.assertEqual(expected_override, js["__override__"])
        self.assertEqual(expected_env, js["__env_session__"])
        self.assertEqual(expected_run, js["__env_run__"])
        self.assertEqual("opencode_ses_abc123", js["__input_beats_env__"],
                         "JS must prefer platform-input ids over env keys, like Python")

    def test_opencode_main_resolution_matrix_matches_python(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            task_ref = ".trellis/tasks/09-11-demo"
            (repo / task_ref).mkdir(parents=True)
            (repo / task_ref / "task.json").write_text(
                json.dumps({"id": "09-11-demo", "status": "in_progress"}), encoding="utf-8"
            )
            sessions = repo / ".trellis" / ".runtime" / "sessions"
            sessions.mkdir(parents=True)
            (sessions / "opencode_ses_one.json").write_text(
                json.dumps({"current_task": task_ref}), encoding="utf-8"
            )
            (sessions / "opencode_ses_two.json").write_text(
                json.dumps({"current_task": task_ref}), encoding="utf-8"
            )

            exact = resolve_active_task(
                repo, {"sessionID": "ses_one"}, platform="opencode",
                allow_environment_context=False,
            )
            self.assertEqual(task_ref, exact.task_path)
            self.assertEqual("session", exact.source_type)
            self.assertEqual("opencode_ses_one", exact.context_key)

            fresh = resolve_active_task(
                repo, {"sessionID": "ses-fresh-window"}, platform="opencode",
                allow_environment_context=False,
            )
            self.assertIsNone(fresh.task_path)
            self.assertEqual("none", fresh.source_type)

            no_identity = resolve_active_task(
                repo, {}, platform="opencode", allow_environment_context=False,
            )
            self.assertIsNone(no_identity.task_path)
            self.assertEqual("ambiguous", no_identity.source_type)

            pull_child = resolve_active_task(
                repo, {"sessionID": "ses-fresh-window"}, platform="opencode",
                allow_single_session_fallback=True, allow_environment_context=False,
            )
            # two files remain ambiguous even for opted-in children
            self.assertIsNone(pull_child.task_path)
            self.assertEqual("ambiguous", pull_child.source_type)

            (sessions / "opencode_ses_two.json").unlink()
            sole_child = resolve_active_task(
                repo, {"sessionID": "ses-fresh-window"}, platform="opencode",
                allow_single_session_fallback=True, allow_environment_context=False,
            )
            self.assertEqual(task_ref, sole_child.task_path)
            self.assertEqual("session-fallback", sole_child.source_type)


if __name__ == "__main__":
    unittest.main()
