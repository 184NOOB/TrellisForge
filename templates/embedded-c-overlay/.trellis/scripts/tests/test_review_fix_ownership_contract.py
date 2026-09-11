"""Cross-file contract test for Check Agent fix ownership and routing.

The fix-ownership contract answers only *who fixes a finding* and must never
schedule review rounds. It is replicated across the template workflow, the
authoritative review Skill, the Channel/Claude/Codex Check Agents, and the
Claude/Codex context-injection Hook check prompts. These files cannot share one
Python constant at the prose layer, so this test locks the R1-R4 contract:

- the Check Agent may directly fix only issues that are simultaneously local,
  mechanical, small, determinate, and inside the current task scope, and must
  record each fix and its verification;
- everything else (design/judgment issues, implementation blocking defects,
  planning defects, out-of-task-scope findings) is report-only;
- the Check Agent never dispatches or resumes the Implement Agent;
- the main session routes implementation defects: Codex inline is fixed by the
  main session itself, otherwise reliably resuming the original Implement
  Agent is preferred, otherwise small clear-boundary fixes go to the main
  session and complex implementation repairs get a new Implement Agent;
- fix routing never schedules a review round; the selected review profile and
  evidence invalidation decide all subsequent reviews;
- the two Hook builders emit a semantically equivalent Finding Handling block
  that never re-introduces unconditional self-fix or bypasses the grading.

This test only parses template files and loads the two Hook modules; it never
dispatches agents and needs no network or hardware. Before the template policy
was aligned, the assertions in this file were red against the current snapshots
(the drift it guards against: unconditional ``Fix issues yourself`` in Claude
agent and both Hooks, ``do not resume an exited agent`` in the Channel agent,
``Never resume an agent that already exited`` and forced ``fresh implement
agent`` routing in the review Skill, and ``fresh implementation pass`` in the
template workflow). Prose line-wrapping differs per file, so phrase matching is
whitespace-normalized and case-insensitive for the semantic anchors.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import unittest


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]  # templates/embedded-c-overlay/

WORKFLOW = TEMPLATE_ROOT / ".trellis" / "workflow.md"
REVIEW_SKILL = (
    TEMPLATE_ROOT
    / ".agents"
    / "skills"
    / "__PROJECT_PREFIX__-trellis-review"
    / "SKILL.md"
)
CHANNEL_CHECK = TEMPLATE_ROOT / ".trellis" / "agents" / "check.md"
CLAUDE_CHECK = TEMPLATE_ROOT / ".claude" / "agents" / "trellis-check.md"
CODEX_CHECK = TEMPLATE_ROOT / ".codex" / "agents" / "trellis-check.toml"
CLAUDE_HOOK = TEMPLATE_ROOT / ".claude" / "hooks" / "inject-subagent-context.py"
CODEX_HOOK = TEMPLATE_ROOT / ".codex" / "hooks" / "inject-subagent-context.py"

MANAGED_FILES = (
    WORKFLOW,
    REVIEW_SKILL,
    CHANNEL_CHECK,
    CLAUDE_CHECK,
    CODEX_CHECK,
    CLAUDE_HOOK,
    CODEX_HOOK,
)

THREE_AGENTS = (CHANNEL_CHECK, CLAUDE_CHECK, CODEX_CHECK)

# Canonical anchors the implementation must introduce everywhere. They double
# as the drift detectors: if a managed entry drops or widens any of them, the
# contract test turns red and the entry reintroduces policy drift.
DIRECT_FIX = "mechanical, small, and determinate"
RESUME_ORIGINAL = "reliably resume the original Implement Agent"
NEW_IMPLEMENT = "dispatch a new Implement Agent"
CODEX_INLINE = "Codex inline"
REPORT_ONLY = (
    "design/judgment issues, implementation blocking defects, planning "
    "defects, and out-of-task-scope findings"
)
HOOK_REPORT_ONLY = (
    "design/judgment issues, implementation blocking defects, planning "
    "defects, or out-of-task-scope findings"
)
NEVER_SCHEDULES = "never schedules a review round"

# Old drift phrases that must stay out of every managed entry.
FORBIDDEN_UNCONDITIONAL_SELF_FIX = "Fix issues yourself"
FORBIDDEN_BLANKET_NO_RESUME = "Never resume an agent that already exited"
FORBIDDEN_CHANNEL_NO_RESUME = "do not resume an exited agent"
FORBIDDEN_FRESH_PASS = "fresh implementation pass"
FORBIDDEN_FRESH_IMPLEMENT = "fresh implement agent"
FORBIDDEN_OWNERSHIP_FRESH_CHECK = "dispatch a fresh Check Agent"
FORBIDDEN_OWNERSHIP_EXTRA_ROUND = "an extra review round"

# Platform command leaks that fix responsibility must not clone into these
# entries: dispatch decisions stay in the workflow/review Skill.
FORBIDDEN_PLATFORM_DISPATCH = "channel spawn"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing managed template file: {path}"
    return path.read_text(encoding="utf-8")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _section(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = len(rest)
    for marker in ("\n## ", "\n# "):
        idx = rest.find(marker)
        if idx != -1:
            end = min(end, idx)
    return rest[:end]


def _has(text: str, phrase: str) -> bool:
    return phrase.lower() in _norm(text).lower()


def _lacks(text: str, phrase: str) -> bool:
    return phrase not in _norm(text)


def _load_module(relative_repo_path: str, name: str):
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / relative_repo_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_check_prompt(relative_repo_path: str, name: str) -> str:
    hook = _load_module(relative_repo_path, name)
    return hook.build_check_prompt(
        "Active task: .trellis/tasks/demo. Fix the mechanical issues.",
        "curated check context",
    )


class ReviewFixOwnershipContractTests(unittest.TestCase):
    def test_skill_declares_direct_fix_boundary(self) -> None:
        skill = _read(REVIEW_SKILL)
        self.assertTrue(_has(skill, DIRECT_FIX))
        self.assertTrue(_has(skill, "records"))
        self.assertTrue(_has(skill, "report"))

    def test_skill_carries_full_main_session_routing(self) -> None:
        ownership = _section(_read(REVIEW_SKILL), "## Blocking-Finding Ownership")
        for phrase in (
            RESUME_ORIGINAL,
            NEW_IMPLEMENT,
            CODEX_INLINE,
            "Phase 1",
            "main session",
            "complex",
        ):
            self.assertTrue(_has(ownership, phrase), phrase)
        self.assertTrue(_lacks(ownership, "fix it yourself, never fix it at all"))

    def test_workflow_carries_matching_routing(self) -> None:
        workflow = _read(WORKFLOW)
        for phrase in (
            DIRECT_FIX,
            RESUME_ORIGINAL,
            NEW_IMPLEMENT,
            CODEX_INLINE,
            "Phase 1",
        ):
            self.assertTrue(_has(workflow, phrase), phrase)

    def test_three_check_agents_share_direct_fix_set(self) -> None:
        for path in THREE_AGENTS:
            self.assertTrue(
                _has(_read(path), DIRECT_FIX),
                f"direct-fix boundary drift in {path.name}: {DIRECT_FIX!r}",
            )

    def test_three_check_agents_share_report_only_set(self) -> None:
        for path in THREE_AGENTS:
            self.assertTrue(
                _has(_read(path), REPORT_ONLY),
                f"report-only set drift in {path.name}: {REPORT_ONLY!r}",
            )

    def test_check_agents_never_dispatch_or_resume_implement(self) -> None:
        for path in THREE_AGENTS:
            text = _read(path)
            self.assertTrue(
                _has(text, "never dispatch or resume the Implement Agent"),
                f"{path.name} must prohibit dispatching/resuming the Implement Agent",
            )
            self.assertTrue(_has(text, NEVER_SCHEDULES), path.name)
            self.assertTrue(_lacks(text, FORBIDDEN_UNCONDITIONAL_SELF_FIX), path.name)

    def test_managed_entries_free_of_old_policy_phrases(self) -> None:
        for path in MANAGED_FILES:
            text = _read(path)
            rel = path.relative_to(TEMPLATE_ROOT)
            for forbidden in (
                FORBIDDEN_UNCONDITIONAL_SELF_FIX,
                FORBIDDEN_BLANKET_NO_RESUME,
                FORBIDDEN_CHANNEL_NO_RESUME,
                FORBIDDEN_FRESH_PASS,
                FORBIDDEN_FRESH_IMPLEMENT,
            ):
                self.assertTrue(
                    _lacks(text, forbidden),
                    f"stale policy phrase {forbidden!r} in {rel}",
                )

    def test_fix_ownership_never_schedules_review_rounds(self) -> None:
        ownership = _section(_read(REVIEW_SKILL), "## Blocking-Finding Ownership")
        self.assertTrue(_has(ownership, NEVER_SCHEDULES))
        # Fix ownership must not add fresh-reviewer triggers of its own.
        self.assertTrue(_lacks(ownership, FORBIDDEN_OWNERSHIP_FRESH_CHECK))
        self.assertTrue(_lacks(ownership, FORBIDDEN_OWNERSHIP_EXTRA_ROUND))
        for path in THREE_AGENTS:
            self.assertTrue(
                _has(_read(path), NEVER_SCHEDULES),
                f"{path.name} fix routing must not schedule a review round",
            )

    def test_routing_stays_out_of_platform_dispatch_commands(self) -> None:
        ownership = _section(_read(REVIEW_SKILL), "## Blocking-Finding Ownership")
        self.assertTrue(_lacks(ownership, FORBIDDEN_PLATFORM_DISPATCH))

    def test_hooks_generate_equivalent_finding_handling(self) -> None:
        outputs = [
            _build_check_prompt(
                ".claude/hooks/inject-subagent-context.py", "claude_check_hook"
            ),
            _build_check_prompt(
                ".codex/hooks/inject-subagent-context.py", "codex_check_hook"
            ),
        ]
        for output in outputs:
            self.assertTrue(_lacks(output, FORBIDDEN_UNCONDITIONAL_SELF_FIX))
            self.assertTrue(_has(output, DIRECT_FIX), "hook must keep the direct-fix boundary")
            self.assertTrue(_has(output, HOOK_REPORT_ONLY), "hook must keep the report-only set")
            self.assertTrue(_has(output, NEVER_SCHEDULES))
            self.assertTrue(_has(output, "review profile"))
        # The Finding Handling section is semantically identical across the two
        # Hooks, so one platform can never drift ahead of the other.
        sections = [
            _norm(_section(output, "## Finding handling")) for output in outputs
        ]
        self.assertEqual(sections[0], sections[1])

    def test_hook_check_prompt_does_not_clone_dispatch_commands(self) -> None:
        for relative, name in (
            (".claude/hooks/inject-subagent-context.py", "claude_check_hook_dispatch"),
            (".codex/hooks/inject-subagent-context.py", "codex_check_hook_dispatch"),
        ):
            prompt = _build_check_prompt(relative, name)
            self.assertTrue(_lacks(prompt, FORBIDDEN_PLATFORM_DISPATCH))


if __name__ == "__main__":
    unittest.main()