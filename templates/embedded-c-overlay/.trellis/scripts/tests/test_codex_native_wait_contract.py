"""Contract tests for the Codex native wait contract and its delivery chain.

Split into four TestCase classes so later phases can run green subsets:

- ``TestStepExtraction``: real-CLI reachability of 2.1 / 2.1.1 (step merge fix)
- ``TestPlatformAlias``: in-process platform family alias matrix
- ``TestDeliveryEntry``: Loading Step Detail + Codex SessionStart hint text
- ``TestNativeWaitContractText``: frozen 2.1.2 contract text (lands last)

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


# Template root: when installed into a downstream repo this resolves to that
# repo root, so tests must never hardcode templates/embedded-c-overlay.
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import workflow_phase as wp  # noqa: E402


WORKFLOW = REPO_ROOT / ".trellis" / "workflow.md"
CODEX_HOOK = REPO_ROOT / ".codex" / "hooks" / "session-start.py"
TEMPLATE_CONTENTS = REPO_ROOT / "TEMPLATE-CONTENTS.md"

STEP_2_1_2_TITLE = "#### 2.1.2 Codex 主会话：原生子代理派发与静默等待"

# Frozen wording that the 2.1.2 contract must carry verbatim.
NATIVE_WAIT_TERMS = (
    "spawn_agent",
    "wait_agent",
    "send_message",
    "list_agents",
    "取该工具允许的最大值",
    "分钟级",
    "120000",
    "timed_out",
    "禁用 30000 这类短周期窗口",
    "交互中断",
    "最小最终结果",
    "读代码或 diff 正文",
    "git status --short",
    "execution-events.jsonl",
    "final-report.md",
    "plan.py status",
    "最多一次",
)

# Terms that must only ever appear in [Codex] bodies.
CODEX_ONLY_TERMS = (
    "exec_command",
    "write_stdin",
    "yield_time_ms",
    "session_id",
    "wait_agent",
    "spawn_agent",
)


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


class TestStepExtraction(unittest.TestCase):
    """Numbered substeps must be reachable through the real CLI."""

    def test_codex_platform_delivers_channel_wait_contract(self) -> None:
        result = run_step("--step", "2.1", "--platform", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("write_stdin", result.stdout)
        self.assertIn("yield_time_ms=300000", result.stdout)

    def test_plain_step_2_1_delivers_channel_wait_contract(self) -> None:
        result = run_step("--step", "2.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("write_stdin", result.stdout)

    def test_numbered_substep_is_locatable(self) -> None:
        result = run_step("--step", "2.1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("write_stdin", result.stdout)
        self.assertNotIn("#### 2.2", result.stdout)

    def test_step_2_2_excludes_substep_content(self) -> None:
        result = run_step("--step", "2.2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("write_stdin", result.stdout)
        self.assertNotIn("#### 2.1.1", result.stdout)

    def test_bare_major_numbers_stay_unresolved(self) -> None:
        for step in ("1", "2", "3"):
            with self.subTest(step=step):
                result = run_step("--step", step)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("Step not found", result.stderr)

    def test_claude_alias_delivers_dispatch_instructions(self) -> None:
        result = run_step("--step", "2.1", "--platform", "claude")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Spawn the implement sub-agent", result.stdout)
        self.assertIn("trellis-implement", result.stdout)

    def test_every_platform_keeps_the_dispatch_instructions(self) -> None:
        for platform in ("claude-code", "codex", "opencode"):
            with self.subTest(platform=platform):
                result = run_step("--step", "2.1", "--platform", platform)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Spawn the implement sub-agent", result.stdout)


def _block(name: str, body: str) -> str:
    return f"[{name}]\n{body}\n[/{name}]\n"


CODEX_FAMILY_BODY = "codex-family-body-marker"
SUB_AGENT_BODY = "codex-sub-agent-only-body-marker"
INLINE_BODY = "codex-inline-only-body-marker"
CLAUDE_BODY = "claude-code-only-body-marker"
OPENCODE_BODY = "opencode-only-body-marker"
COMBINED_BODY = "combined-claude-sub-agent-opencode-body-marker"

MATRIX_CONTENT = (
    _block("Codex", CODEX_FAMILY_BODY)
    + _block("codex-sub-agent", SUB_AGENT_BODY)
    + _block("codex-inline", INLINE_BODY)
    + _block("Claude Code", CLAUDE_BODY)
    + _block("OpenCode", OPENCODE_BODY)
    + _block("Claude Code, codex-sub-agent, OpenCode", COMBINED_BODY)
)


class TestPlatformAlias(unittest.TestCase):
    """Platform family aliases must not leak across families."""

    def test_resolve_effective_platform(self) -> None:
        self.assertEqual(wp.resolve_effective_platform("codex", {}), "codex-sub-agent")
        self.assertEqual(
            wp.resolve_effective_platform(
                "codex", {"codex": {"dispatch_mode": "inline"}}
            ),
            "codex-inline",
        )
        self.assertEqual(wp.resolve_effective_platform("claude", {}), "claude")

    def test_codex_family_alias_keeps_codex_block_only(self) -> None:
        for platform in ("codex-sub-agent", "codex-inline"):
            with self.subTest(platform=platform):
                out = wp.filter_platform(MATRIX_CONTENT, platform)
                self.assertIn(CODEX_FAMILY_BODY, out)
                self.assertNotIn(CLAUDE_BODY, out)
                self.assertNotIn(OPENCODE_BODY, out)

    def test_sub_agent_and_inline_are_not_aliases(self) -> None:
        sub_agent_out = wp.filter_platform(MATRIX_CONTENT, "codex-sub-agent")
        self.assertIn(SUB_AGENT_BODY, sub_agent_out)
        self.assertNotIn(INLINE_BODY, sub_agent_out)
        inline_out = wp.filter_platform(MATRIX_CONTENT, "codex-inline")
        self.assertIn(INLINE_BODY, inline_out)
        self.assertNotIn(SUB_AGENT_BODY, inline_out)

    def test_claude_family_alias_keeps_claude_block_only(self) -> None:
        for platform in ("claude", "claude-code"):
            with self.subTest(platform=platform):
                out = wp.filter_platform(MATRIX_CONTENT, platform)
                self.assertIn(CLAUDE_BODY, out)
                self.assertNotIn(CODEX_FAMILY_BODY, out)
                self.assertNotIn(SUB_AGENT_BODY, out)
                self.assertNotIn(INLINE_BODY, out)
                self.assertNotIn(OPENCODE_BODY, out)

    def test_opencode_matches_only_itself(self) -> None:
        out = wp.filter_platform(MATRIX_CONTENT, "opencode")
        self.assertIn(OPENCODE_BODY, out)
        self.assertNotIn(CODEX_FAMILY_BODY, out)
        self.assertNotIn(CLAUDE_BODY, out)

    def test_no_cross_family_aliases(self) -> None:
        codex_out = wp.filter_platform(MATRIX_CONTENT, "codex-sub-agent")
        claude_out = wp.filter_platform(MATRIX_CONTENT, "claude")
        self.assertNotIn(CLAUDE_BODY, codex_out)
        self.assertNotIn(CODEX_FAMILY_BODY, claude_out)

    def test_combined_marker_follows_each_platform(self) -> None:
        for platform in ("codex-sub-agent", "claude", "claude-code", "opencode"):
            with self.subTest(platform=platform):
                self.assertIn(
                    COMBINED_BODY, wp.filter_platform(MATRIX_CONTENT, platform)
                )
        self.assertNotIn(
            COMBINED_BODY, wp.filter_platform(MATRIX_CONTENT, "codex-inline")
        )


class TestDeliveryEntry(unittest.TestCase):
    """The Codex entry points must tell the session to pass --platform."""

    def test_loading_step_detail_names_all_three_platforms(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"### Loading Step Detail\n(.*?)(?=\n---|\n## )", text, re.DOTALL
        )
        self.assertIsNotNone(match, "Loading Step Detail section not found")
        section = match.group(1)
        for flag in ("--platform claude", "--platform codex", "--platform opencode"):
            with self.subTest(flag=flag):
                self.assertIn(flag, section)

    def test_codex_session_start_hint_passes_platform(self) -> None:
        text = CODEX_HOOK.read_text(encoding="utf-8")
        self.assertIn("--mode phase --step <X.Y> --platform codex", text)


class TestNativeWaitContractText(unittest.TestCase):
    """Frozen 2.1.2 contract: written after the reachability fixes."""

    def test_step_2_1_2_is_locatable_with_frozen_terms(self) -> None:
        result = run_step("--step", "2.1.2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(STEP_2_1_2_TITLE, result.stdout)
        for term in NATIVE_WAIT_TERMS:
            with self.subTest(term=term):
                self.assertIn(term, result.stdout)

    def test_both_contracts_delivered_with_and_without_platform(self) -> None:
        for args in (("--step", "2.1", "--platform", "codex"), ("--step", "2.1")):
            with self.subTest(args=args):
                result = run_step(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("write_stdin", result.stdout)
                self.assertIn("wait_agent", result.stdout)

    def test_step_2_1_1_stops_before_the_native_contract(self) -> None:
        result = run_step("--step", "2.1.1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("wait_agent", result.stdout)

    def test_claude_platforms_never_see_codex_term_bodies(self) -> None:
        for platform in ("claude-code", "claude"):
            with self.subTest(platform=platform):
                result = run_step("--step", "2.1", "--platform", platform)
                self.assertEqual(result.returncode, 0, result.stderr)
                for term in CODEX_ONLY_TERMS:
                    self.assertNotIn(term, result.stdout)

    def test_filtered_substep_does_not_leak_codex_body(self) -> None:
        # git_context.py checks for empty content before platform filtering,
        # so this command exits 0; the heading line may survive while the
        # [Codex] body is dropped. Emptiness itself is deliberately not
        # asserted here.
        result = run_step("--step", "2.1.2", "--platform", "claude-code")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(STEP_2_1_2_TITLE, result.stdout)
        for term in CODEX_ONLY_TERMS:
            self.assertNotIn(term, result.stdout)
        for phrase in ("取该工具允许的最大值", "交互中断", "最小最终结果"):
            self.assertNotIn(phrase, result.stdout)

    def test_contract_text_is_scoped_and_has_no_short_windows(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn('"timeout_ms":30000', text)
        self.assertIn(STEP_2_1_2_TITLE, text)
        index = text.index(STEP_2_1_2_TITLE)
        match = re.match(
            r"[^\n]*\n+\[Codex\]\n(.*?)\n\[/Codex\]",
            text[index:],
            re.DOTALL,
        )
        self.assertIsNotNone(
            match, "[Codex] wrapper not found right after the 2.1.2 heading"
        )
        body = match.group(1)
        self.assertIsNone(re.search(r"yield_time_ms=30000(?!0)", body))

    def test_template_contents_registers_new_tests(self) -> None:
        text = TEMPLATE_CONTENTS.read_text(encoding="utf-8")
        self.assertIn("test_codex_native_wait_contract.py", text)
        self.assertIn("test_write_json_lf.py", text)


if __name__ == "__main__":
    unittest.main()