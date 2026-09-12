"""Static cross-file contract test for the five review levels.

The review-level contract is consumed by workflow text, Skills, three Check
Agent definitions, a Codex hook, and the planning gate. These files cannot
share one Python constant at the prose layer, so this test locks the contract:

- the five legal level names are present in every level consumer;
- ``reinforced`` is bound to the affected-scope independent re-review loop;
- ``comprehensive`` is bound to the full-scope loop without an extra
  commit-ready review round;
- ``strict`` additionally requires a fresh commit-ready full-scope final
  review;
- report contracts carry level/scope/round/stage/blocking-count fields;
- stale three-level enumerations are not left in managed template files.

This test only parses template files; it never dispatches agents and needs no
network or hardware.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]  # templates/embedded-c-overlay/
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common.planning_gate import VALID_REVIEW_LEVELS  # noqa: E402

LEVELS = ("light", "standard", "reinforced", "comprehensive", "strict")

WORKFLOW = TEMPLATE_ROOT / ".trellis" / "workflow.md"
REVIEW_SKILL = (
    TEMPLATE_ROOT
    / ".agents"
    / "skills"
    / "__PROJECT_PREFIX__-trellis-review"
    / "SKILL.md"
)
REVIEW_AGENT_YAML = REVIEW_SKILL.parent / "agents" / "openai.yaml"
GRILL_ADAPTER = (
    TEMPLATE_ROOT
    / ".agents"
    / "skills"
    / "__PROJECT_PREFIX__-trellis-grill-adapter"
    / "SKILL.md"
)
CHANNEL_CHECK = TEMPLATE_ROOT / ".trellis" / "agents" / "check.md"
CLAUDE_CHECK = TEMPLATE_ROOT / ".claude" / "agents" / "trellis-check.md"
CODEX_CHECK = TEMPLATE_ROOT / ".codex" / "agents" / "trellis-check.toml"
CODEX_HOOK = TEMPLATE_ROOT / ".codex" / "hooks" / "inject-workflow-state.py"
PLANNING_GATE = TEMPLATE_ROOT / ".trellis" / "scripts" / "common" / "planning_gate.py"
OPENCODE_CHECK = TEMPLATE_ROOT / ".opencode" / "agents" / "trellis-check.md"
OPENCODE_REVIEW_SKILL = (
    TEMPLATE_ROOT
    / ".opencode"
    / "skills"
    / "__PROJECT_PREFIX__-trellis-review"
    / "SKILL.md"
)

# Files that enumerate the legal review-level values for users or agents.
LEVEL_CONSUMERS = (
    WORKFLOW,
    REVIEW_SKILL,
    REVIEW_AGENT_YAML,
    GRILL_ADAPTER,
    CHANNEL_CHECK,
    CLAUDE_CHECK,
    CODEX_CHECK,
    CODEX_HOOK,
    PLANNING_GATE,
    OPENCODE_CHECK,
    OPENCODE_REVIEW_SKILL,
)

# The independent reviewer definitions across every dispatch-capable path.
CHECK_AGENTS = (CHANNEL_CHECK, CLAUDE_CHECK, CODEX_CHECK, OPENCODE_CHECK)

REPORT_FIELDS = (
    "Review level",
    "Review scope",
    "Review round",
    "Review stage",
    "Blocking findings count",
)

# Exact three-adjacency spellings used before the five-level expansion.
# The five-level forms always insert reinforced/comprehensive between
# "standard" and "strict", so these literals can only match stale text.
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
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = len(rest)
    for marker in ("\n## ", "\n# "):
        idx = rest.find(marker)
        if idx != -1:
            end = min(end, idx)
    return rest[:end]


class ReviewProfileContractTests(unittest.TestCase):
    def test_planning_gate_declares_five_levels_in_order(self) -> None:
        self.assertEqual(
            VALID_REVIEW_LEVELS,
            ("light", "standard", "reinforced", "comprehensive", "strict"),
        )

    def test_five_level_names_present_in_every_consumer(self) -> None:
        for path in LEVEL_CONSUMERS:
            text = _read(path)
            for level in LEVELS:
                self.assertIn(
                    level,
                    text,
                    f"level drift: {level!r} missing from {path.relative_to(TEMPLATE_ROOT)}",
                )

    def test_canonical_five_value_sequence_in_prose_consumers(self) -> None:
        canonical_pipe = "|".join(LEVELS)
        self.assertIn(
            canonical_pipe,
            _read(WORKFLOW),
            "workflow.md must publish the light|standard|reinforced|comprehensive|strict set",
        )
        self.assertIn(
            canonical_pipe,
            _read(GRILL_ADAPTER),
            "grill adapter must accept the same five-value set",
        )
        self.assertIn(
            canonical_pipe,
            _read(CHANNEL_CHECK),
            "channel check report contract must enumerate all five levels",
        )
        skill = _read(REVIEW_SKILL)
        self.assertIn(
            "light < standard < reinforced < comprehensive < strict",
            skill,
            "review Skill must state the fixed strength order",
        )

    def test_reinforced_bound_to_affected_scope_loop(self) -> None:
        skill = _section(_read(REVIEW_SKILL), "## Reinforced")
        self.assertIn("affected-scope", skill)
        self.assertIn("fresh independent", skill)
        self.assertIn("zero blocking", skill)
        workflow = _read(WORKFLOW)
        self.assertIn("`reinforced`: dispatch an independent affected-scope", workflow)

    def test_comprehensive_full_scope_without_commit_ready_gate(self) -> None:
        skill = _section(_read(REVIEW_SKILL), "## Comprehensive")
        self.assertIn("full-scope", skill)
        self.assertIn("does NOT\n  add an extra commit-ready review round", skill)
        workflow = _read(WORKFLOW)
        self.assertIn("comprehensive", workflow)
        codex = _read(CODEX_CHECK)
        self.assertIn("does not add an extra commit-ready review round", codex)

    def test_strict_requires_fresh_commit_ready_final_review(self) -> None:
        skill = _section(_read(REVIEW_SKILL), "## Strict")
        self.assertIn("commit-ready", skill)
        self.assertIn("fresh independent", skill)
        self.assertIn("unconditional", skill)
        workflow = _read(WORKFLOW)
        self.assertIn("strict` additionally requires", workflow)
        self.assertIn("fresh independent full-scope commit-ready final review", workflow)
        codex = _read(CODEX_CHECK)
        self.assertIn("commit-ready final review", codex)

    def test_other_profiles_have_no_unconditional_commit_ready_round(self) -> None:
        workflow = _read(WORKFLOW)
        preamble = _section(
            workflow, "**Review-profile preamble**: before drafting commits,"
        )
        # The preamble must state that light..comprehensive need no extra round
        # and that only strict requires the fresh commit-ready review.
        self.assertIn(
            "require no extra commit-ready review round",
            preamble,
            "workflow Phase 3.4 preamble must keep non-strict profiles free of an extra round",
        )
        self.assertEqual(
            preamble.count("commit-ready final review"),
            1,
            "only the strict clause may require a commit-ready final review",
        )

    def test_default_stays_standard_for_missing_or_invalid(self) -> None:
        self.assertIn("otherwise default to `standard`", _read(WORKFLOW))
        self.assertIn("write and use\n`standard`", _read(REVIEW_SKILL))
        self.assertIn("otherwise persist\n   `standard`", _read(GRILL_ADAPTER))
        self.assertIn("use `standard` and must be reported", _read(CHANNEL_CHECK))
        self.assertIn("use `standard` and must be reported", _read(CODEX_CHECK))
        self.assertIn("use `standard` and must be", _read(CLAUDE_CHECK))
        self.assertIn("use `standard` and must be", _read(OPENCODE_CHECK))

    def test_opencode_review_skill_mirror_is_byte_identical(self) -> None:
        self.assertEqual(
            _read(REVIEW_SKILL),
            _read(OPENCODE_REVIEW_SKILL),
            "the OpenCode review Skill mirror must not drift from the "
            "authoritative .agents/skills copy",
        )

    def test_opencode_check_agent_carries_five_level_profile_matrix(self) -> None:
        text = _read(OPENCODE_CHECK)
        self.assertIn("## Review Profile", text)
        self.assertIn("`reinforced`: one affected-scope round", text)
        self.assertIn("comprehensive`:", text)
        self.assertIn("commit-ready-final", text)
        # OpenCode must not offer an opencode channel worker as a review path.
        self.assertNotIn("provider opencode", text)

    def test_evidence_invalidation_contract(self) -> None:
        skill = _section(_read(REVIEW_SKILL), "## Evidence Invalidation")
        self.assertIn("materially change", skill)
        self.assertIn("must run again", skill)
        workflow = _read(WORKFLOW)
        self.assertIn("invalidate prior evidence", workflow)
        self.assertIn("re-trigger the current profile's review", workflow)

    def test_check_agents_share_report_fields(self) -> None:
        for path in CHECK_AGENTS:
            text = _read(path)
            for field in REPORT_FIELDS:
                self.assertIn(
                    field,
                    text,
                    f"report drift: {field!r} missing from {path.relative_to(TEMPLATE_ROOT)}",
                )

    def test_report_stage_values_present_in_agents(self) -> None:
        for path in CHECK_AGENTS:
            text = _read(path)
            self.assertIn(
                "implementation-loop",
                text,
                f"{path.name} must define the implementation-loop stage",
            )
            self.assertIn(
                "commit-ready-final",
                text,
                f"{path.name} must define the commit-ready-final stage",
            )

    def test_no_stale_three_level_enumerations(self) -> None:
        for path in LEVEL_CONSUMERS:
            text = _read(path)
            for needle in STALE_ENUMERATIONS:
                self.assertNotIn(
                    needle,
                    text,
                    "stale three-level text in "
                    f"{path.relative_to(TEMPLATE_ROOT)}: {needle!r}",
                )

    def test_hook_stays_prompt_only(self) -> None:
        hook = _read(CODEX_HOOK)
        self.assertIn("light/standard/reinforced/comprehensive/", hook)
        # The hook must not grow review routing or gate logic.
        self.assertNotIn("VALID_REVIEW_LEVELS", hook)
        self.assertNotIn("validate_planning_gate", hook)


if __name__ == "__main__":
    unittest.main()
