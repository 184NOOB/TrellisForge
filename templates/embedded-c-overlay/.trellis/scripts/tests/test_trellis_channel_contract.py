"""Contract tests for the trellis-channel Skill overlay and Codex wait flow.

Static template checks only: complete skill file trees, byte-identical public
mirrors, Codex-terminal-term scoping, one-spawn / one-wait dispatch examples,
and the polling probes that must stay out of the normal wait path. These tests
never spawn workers or touch external providers.
"""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]

AGENTS_SKILL = REPO_ROOT / ".agents" / "skills" / "trellis-channel"
CLAUDE_SKILL = REPO_ROOT / ".claude" / "skills" / "trellis-channel"

COMMON_FILES = (
    "SKILL.md",
    "references/command-reference.md",
    "references/forum.md",
    "references/progress-debugging.md",
    "references/workers.md",
    "references/workflows.md",
)

WORKFLOW = REPO_ROOT / ".trellis" / "workflow.md"
IMPLEMENT_CARD = REPO_ROOT / ".trellis" / "agents" / "implement.md"
CHECK_CARD = REPO_ROOT / ".trellis" / "agents" / "check.md"

CODEX_TERMS = ("exec_command", "write_stdin", "yield_time_ms", "session_id")


def _tag_blocks(text: str, tag: str):
    """Return the bodies of every [tag] ... [/tag] block in ``text``."""
    start, end = f"[{tag}]", f"[/{tag}]"
    blocks, pos = [], 0
    while True:
        begin = text.find(start, pos)
        if begin == -1:
            break
        finish = text.find(end, begin + len(start))
        if finish == -1:
            break
        blocks.append(text[begin + len(start):finish])
        pos = finish + len(end)
    return blocks


def _code_section(text: str, header: str):
    match = re.search(
        rf"### {re.escape(header)}\n\n```powershell\n(.*?)\n```",
        text,
        re.S,
    )
    return match.group(1) if match else ""


class TrellisChannelSkillTreeTests(unittest.TestCase):
    def _relative_skill_files(self, base: Path):
        return {
            str(p.relative_to(base)).replace("\\", "/")
            for p in base.rglob("*")
            if p.is_file()
        }

    def test_skill_trees_are_complete_and_symmetric(self):
        for base in (AGENTS_SKILL, CLAUDE_SKILL):
            self.assertTrue(base.is_dir(), f"missing skill tree: {base}")
            present = self._relative_skill_files(base)
            self.assertEqual(
                present,
                set(COMMON_FILES),
                f"unexpected or missing files under {base}",
            )

    def test_public_skill_files_byte_identical_between_mirrors(self):
        for relative in COMMON_FILES:
            agents_path = AGENTS_SKILL / relative
            claude_path = CLAUDE_SKILL / relative
            self.assertTrue(agents_path.is_file(), f"missing {agents_path}")
            self.assertTrue(claude_path.is_file(), f"missing {claude_path}")
            self.assertEqual(
                agents_path.read_bytes(),
                claude_path.read_bytes(),
                f"public mirror drifted: {relative}",
            )

    def test_codex_terms_and_plan_status_stay_out_of_public_skill_layer(self):
        for base in (AGENTS_SKILL, CLAUDE_SKILL):
            for relative in COMMON_FILES:
                text = (base / relative).read_text(encoding="utf-8")
                for term in CODEX_TERMS:
                    self.assertNotIn(term, text, f"{base}/{relative} contains {term}")
                self.assertNotIn(
                    "plan.py status", text, f"{base}/{relative} mentions plan.py status"
                )


class TrellisChannelWorkflowScopeTests(unittest.TestCase):
    def test_codex_terminal_terms_scoped_to_codex_blocks_in_workflow(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        for term in CODEX_TERMS:
            self.assertIn(term, text, f"{term} missing from workflow.md")
        codex_text = "\n".join(_tag_blocks(text, "Codex"))
        for term in CODEX_TERMS:
            self.assertIn(term, codex_text, f"{term} missing from [Codex] blocks")
        claude_text = "\n".join(
            _tag_blocks(text, "Claude Code")
            + _tag_blocks(text, "Claude Code, codex-sub-agent")
        )
        for term in CODEX_TERMS:
            self.assertNotIn(
                term, claude_text, f"{term} leaked into a [Claude Code] scope"
            )

    def test_workflow_requires_reusing_the_same_session_id(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        codex_text = "\n".join(_tag_blocks(text, "Codex"))
        self.assertIn("复用同一 ID", codex_text)
        self.assertIn("只对该 ID 调用 `write_stdin`", codex_text)


class TrellisChannelDispatchExampleTests(unittest.TestCase):
    def setUp(self):
        self.workflows = (AGENTS_SKILL / "references" / "workflows.md").read_text(
            encoding="utf-8"
        )
        self.workers = (AGENTS_SKILL / "references" / "workers.md").read_text(
            encoding="utf-8"
        )
        self.skill = (AGENTS_SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_standard_dispatch_examples_one_spawn_one_wait(self):
        examples = {
            "implement": ("Standard Implement Dispatch", "--agent implement"),
            "check": ("Standard Check Dispatch", "--agent check"),
        }
        for name, (header, agent_flag) in examples.items():
            block = _code_section(self.workflows, header)
            self.assertTrue(block, f"missing {name} dispatch section")
            self.assertEqual(
                block.count("trellis channel spawn"), 1, f"{name} must spawn once"
            )
            self.assertEqual(
                block.count("trellis channel wait"), 1, f"{name} must wait once"
            )
            self.assertIn(agent_flag, block, f"{name} must use {agent_flag}")
            self.assertIn("--kind done,error", block, f"{name} must wait on terminal kinds")
            self.assertIn("trellis channel wait", block)
            self.assertIn("--as main", block)

    def test_standard_dispatch_examples_have_no_polling(self):
        for header in ("Standard Implement Dispatch", "Standard Check Dispatch"):
            block = _code_section(self.workflows, header)
            for probe in (
                "--include-progress",
                "messages --kind progress",
                "plan.py status",
                "channel list",
            ):
                self.assertNotIn(probe, block, f"{header} shows forbidden {probe}")

    def test_normal_path_carries_explicit_one_wait_rule(self):
        self.assertIn("Unique wait pattern", self.skill)
        self.assertIn("do not re-`wait`", self.skill)
        self.assertIn("Dispatcher Wait Discipline", self.workers)
        self.assertIn("exactly one `spawn`, then block on exactly one `wait`", self.workers)
        self.assertIn("progress", self.workers)

    def test_progress_diagnostic_boundary_is_documented(self):
        debugging = (AGENTS_SKILL / "references" / "progress-debugging.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Normal Path vs Diagnostics", debugging)
        self.assertIn("diagnostic activity", debugging)


class TrellisChannelWorkerCardTests(unittest.TestCase):
    def test_worker_cards_state_termination_contract(self):
        for path in (IMPLEMENT_CARD, CHECK_CARD):
            text = path.read_text(encoding="utf-8")
            self.assertIn("Channel Termination Contract", text, f"{path}")
            self.assertIn("wait --kind done,error", text, f"{path}")
            for term in CODEX_TERMS:
                self.assertNotIn(term, text, f"{path} contains dispatcher terminal {term}")
            self.assertTrue(
                "trellis channel wait" in text,
                f"{path} should forbid dispatcher waits explicitly",
            )


if __name__ == "__main__":
    unittest.main()