"""Static contract test for main-session severity adjudication.

Locks the dual-gate review contract:

- Check Agent labels and ``Blocking findings count`` are signals;
- the main session re-grades every finding against the absolute
  safety/correctness/acceptance gate;
- loop-exit IF/until sentences use the adjudicated count, not
  ``newest independent report`` as the sole subject;
- the OpenCode review Skill mirror stays byte-identical;
- production-side Check Agent definitions forbid downgrading gate hits.

This test only parses template files; it never dispatches agents.
"""

from __future__ import annotations

from pathlib import Path
import unittest


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]

WORKFLOW = TEMPLATE_ROOT / ".trellis" / "workflow.md"
REVIEW_SKILL = (
    TEMPLATE_ROOT
    / ".agents"
    / "skills"
    / "trellisforge-trellis-review"
    / "SKILL.md"
)
OPENCODE_REVIEW_SKILL = (
    TEMPLATE_ROOT
    / ".opencode"
    / "skills"
    / "trellisforge-trellis-review"
    / "SKILL.md"
)
CHANNEL_CHECK = TEMPLATE_ROOT / ".trellis" / "agents" / "check.md"
CLAUDE_CHECK = TEMPLATE_ROOT / ".claude" / "agents" / "trellis-check.md"
CODEX_CHECK = TEMPLATE_ROOT / ".codex" / "agents" / "trellis-check.toml"
OPENCODE_CHECK = TEMPLATE_ROOT / ".opencode" / "agents" / "trellis-check.md"
CHECK_AGENTS = (CHANNEL_CHECK, CLAUDE_CHECK, CODEX_CHECK, OPENCODE_CHECK)

STALE_ENUMERATIONS = (
    "light|standard|strict",
    "light/standard/strict",
    "light, standard, or strict",
    "`light`, `standard`, or `strict`",
    "`light`, `standard`, `strict`",
    "`standard` and `strict`",
    "`standard` / `strict`",
    "standard/strict",
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing managed template file: {path}"
    return path.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    needle = heading if heading.startswith("\n") else "\n" + heading
    start = text.index(needle) + (0 if heading.startswith("\n") else 1)
    rest = text[start + len(heading):]
    end = len(rest)
    for marker in ("\n## ", "\n# "):
        idx = rest.find(marker)
        if idx != -1:
            end = min(end, idx)
    return rest[:end]


def _state_block(text: str, name: str) -> str:
    start = f"[workflow-state:{name}]"
    end = f"[/workflow-state:{name}]"
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


class ReviewSeverityAdjudicationContractTests(unittest.TestCase):
    def test_skill_declares_severity_adjudication_section(self) -> None:
        skill = _read(REVIEW_SKILL)
        body = _section(skill, "## Severity Adjudication")
        self.assertIn("absolute gate", body)
        self.assertIn("signals", body)
        self.assertIn("escalate", body)
        self.assertIn("adjudicated", body)
        self.assertIn("downgrade", body)

    def test_opencode_review_skill_mirror_is_byte_identical(self) -> None:
        self.assertEqual(_read(REVIEW_SKILL), _read(OPENCODE_REVIEW_SKILL))

    def test_verify_before_routing_cites_adjudication(self) -> None:
        ownership = _section(_read(REVIEW_SKILL), "## Blocking-Finding Ownership")
        self.assertIn("Severity Adjudication", ownership)
        self.assertIn("Verify before routing", ownership)
        self.assertNotIn("dispatch a fresh Check Agent", ownership)
        self.assertNotIn("an extra review round", ownership)

    def test_report_contract_uses_adjudicated_count_for_exit(self) -> None:
        report = _section(_read(REVIEW_SKILL), "## Report Contract")
        self.assertIn("adjudicated count", report)
        self.assertIn("loop exit", report)

    def test_skill_loop_sentences_use_adjudicated_subject(self) -> None:
        skill = _read(REVIEW_SKILL)
        reinforced = _section(skill, "## Reinforced")
        comprehensive = _section(skill, "## Comprehensive")
        strict = _section(skill, "## Strict")
        for body in (reinforced, comprehensive, strict):
            self.assertIn("adjudicated", body)
            self.assertNotIn(
                "until the newest independent report shows zero blocking",
                body,
            )
        self.assertIn("Severity Adjudication", reinforced)
        self.assertIn("do not start another complete independent review unless the\n  task scope materially changes", _section(skill, "## Standard"))

    def test_workflow_injected_blocks_use_adjudicated_exit(self) -> None:
        workflow = _read(WORKFLOW)
        in_progress = _state_block(workflow, "in_progress")
        inline = _state_block(workflow, "in_progress-inline")
        for body in (in_progress, inline):
            self.assertIn("Severity Adjudication", body)
            self.assertIn("adjudicated count", body)
            self.assertNotIn(
                "until blocking findings are zero",
                body,
            )

    def test_workflow_authoritative_profile_loop_uses_adjudicated_exit(self) -> None:
        workflow = _read(WORKFLOW)
        self.assertIn("`reinforced`: dispatch an independent affected-scope", workflow)
        start = workflow.index("`reinforced`: dispatch an independent affected-scope")
        profile = workflow[start:start + 1800]
        self.assertIn("Severity Adjudication", profile)
        self.assertIn("adjudicated count", profile)
        self.assertIn("If the report has blocking findings", profile)
        self.assertNotIn(
            "until the newest independent report shows zero blocking",
            profile,
        )
        preamble = workflow[
            workflow.index("**Review-profile preamble**: before drafting commits,")
            :
        ]
        self.assertIn("Severity Adjudication", preamble)
        self.assertIn("adjudicated count", preamble)

    def test_check_agents_forbid_downgrading_gate_hits(self) -> None:
        for path in CHECK_AGENTS:
            text = _read(path)
            rel = path.relative_to(TEMPLATE_ROOT)
            self.assertIn(
                "must be classified as blocking",
                text,
                f"missing blocking classification rule in {rel}",
            )
            self.assertIn("never downgrade", text, f"missing never-downgrade in {rel}")
            self.assertIn(
                "acceptance criterion",
                text,
                f"missing acceptance-criterion gate in {rel}",
            )

    def test_no_stale_three_level_enumerations_in_touched_files(self) -> None:
        for path in (WORKFLOW, REVIEW_SKILL, OPENCODE_REVIEW_SKILL) + CHECK_AGENTS:
            text = _read(path)
            for needle in STALE_ENUMERATIONS:
                self.assertNotIn(
                    needle,
                    text,
                    f"stale three-level text in {path.relative_to(TEMPLATE_ROOT)}: {needle!r}",
                )


if __name__ == "__main__":
    unittest.main()
