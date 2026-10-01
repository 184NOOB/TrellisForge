"""Contract tests for the single-dispatch plan-chain contract (A-E).

A / A': ``execution_contract()`` carries the chain-traversal obligation and the
``block`` + structured-report failure contract while every original
batch-efficiency sentence survives; the Python function, the ``--json`` bridge,
and ``.opencode/lib/session-utils.js`` ``STATIC_EXECUTION_CONTRACT`` stay
byte-identical (all three values are read dynamically; the constant is never
copied into this file).

B: ``plan_protocol_block()`` adds the neutral Chain duty inside the in-progress
branch only; the completed branch must not carry the same phrase.

C: the ``[workflow-state:in_progress]`` tag block defines the round granularity,
the default subject, and the ``User instructions override these defaults``
exception with both ``explicitly asks`` cases. Delivery is asserted in two
channels on purpose: the tag block text is read from ``workflow.md``, while the
``#### 2.1`` dispatch-scope sentence goes through the real ``get_context.py``
CLI (cwd = template root) for claude / codex / opencode. The round definition
and the exception are never asserted on the ``--step 2.1`` output.

D: all four implement agent definitions carry the same new phrases.

E: ``_dispatch_chain`` derivation matrix (linear / diamond / blocked pruning /
completed pruning / all-done / malformed / parallel forest / declaration-order
tie-break) plus the ``format_status`` ``dispatch chain:`` line under the legacy
and sequel layouts, with fail-soft behavior.

No test here spawns or waits for a real agent, and none invokes
``trellis channel``.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


# Template root: when installed into a downstream repo this resolves to that
# repo root, so tests must never hardcode templates/embedded-c-overlay.
REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import execution_plan as ep  # noqa: E402

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - downstream 3.10 fallback
    tomllib = None  # type: ignore[assignment]

POLICY = REPO_ROOT / ".trellis" / "scripts" / "common" / "subagent_prompt_policy.py"
SESSION_UTILS = REPO_ROOT / ".opencode" / "lib" / "session-utils.js"
WORKFLOW = REPO_ROOT / ".trellis" / "workflow.md"

IMPLEMENT_AGENTS = (
    ".trellis/agents/implement.md",
    ".claude/agents/trellis-implement.md",
    ".codex/agents/trellis-implement.toml",
    ".opencode/agents/trellis-implement.md",
)

CODEX_ONLY_TERMS = (
    "exec_command",
    "write_stdin",
    "yield_time_ms",
    "session_id",
    "wait_agent",
    "spawn_agent",
)

# A / A' key phrases (the full contract is compared dynamically, never copied).
CHAIN_OWNERSHIP = "One dispatch owns the whole remaining plan chain"
BLOCK_CONTRACT = "run plan.py block <id> --reason"
SILENT_RETURN = "silent empty return is a protocol violation"
BUDGET_EXCEPTION = "context-budget exhaustion"
BATCH_EFFICIENCY = "Batch independent reads and searches"
STOP_SENTENCE = "stop when scope, evidence, verification, and report are complete"

# B / D phrase shared by the protocol block and the four agent definitions.
CHAIN_DUTY = "Chain duty: one execution round covers the whole remaining chain"
DISPATCHED_LIMIT = "A dispatched sub-agent must not return"
MAIN_IMPLEMENTER = "the same chain duty and the same failure reporting apply to it"

# C tag-block phrases.
ROUND_DEFAULT = "Dispatch granularity (default)"
DEFAULT_SUBJECT = "By default the implement sub-agent"
USER_OVERRIDE = "User instructions override these defaults"
INLINE_FORBIDDEN = (ROUND_DEFAULT, USER_OVERRIDE)

# D report lines.
REPORT_ADVANCED = "Plan phases advanced:"
REPORT_REMAINING = "Remaining runnable:"


def load_module(relative_path: str, name: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalized(relative_path: str) -> str:
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", text)


def tag_block(text: str, name: str) -> str:
    """Extract a real ``[workflow-state:name]`` block.

    The tag must own its line: the documented breadcrumb-contract comment also
    mentions the status names inline, and a naive ``str.index`` would start
    there and swallow the whole document.
    """
    pattern = re.compile(
        rf"^\[workflow-state:{re.escape(name)}\][ \t]*\r?$(.*?)"
        rf"^\[/workflow-state:{re.escape(name)}\][ \t]*\r?$",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match is None:
        raise AssertionError(f"[workflow-state:{name}] block not found")
    return match.group(1)


def run_step(*args: str) -> subprocess.CompletedProcess:
    """Run the real template CLI in the template root."""
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


def _task(task_id: str, status: str = "pending", deps=()) -> dict:
    return {
        "id": task_id,
        "title": task_id,
        "objective": task_id,
        "status": status,
        "depends_on": list(deps),
        "scope": {"read": ["src/a.c"], "write": ["src/a.c"]},
        "verification": {"level": "minimal", "required_checks": ["unit"]},
    }


def _plan(tasks: list[dict], *, parallel: bool = False, status: str = "approved") -> dict:
    return {
        "schema": 3,
        "task": "demo",
        "revision": 1,
        "status": status,
        "audit": {"required": True, "file": "execution-events.jsonl"},
        "created_by": "trellis-implement",
        "goal": "dispatch chain demo",
        "constraints": {
            "forbidden_git_operations": ["commit"],
            "max_tasks": 8,
            "max_edits_per_file": 4,
            "allow_parallel_tasks": parallel,
        },
        "tasks": tasks,
    }


def _write_plan(task_dir: Path, plan: dict) -> None:
    (task_dir / ep.PLAN_FILE).write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )


class DispatchContractTextTests(unittest.TestCase):
    """A / A': contract text plus the three-way dynamic parity."""

    def test_execution_contract_carries_chain_and_failure_duties(self) -> None:
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py",
            "dispatch_chain_policy",
        )
        contract = policy.execution_contract()
        for phrase in (
            CHAIN_OWNERSHIP,
            BLOCK_CONTRACT,
            SILENT_RETURN,
            BUDGET_EXCEPTION,
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, contract)
        # The original batch-efficiency contract must survive the append.
        for phrase in (BATCH_EFFICIENCY, STOP_SENTENCE):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, contract)
        # No double quotes may enter the shared text: the JS fallback is parsed
        # by stripping double-quoted segments, so a raw quote would break parity.
        self.assertNotIn('"', contract)

    def test_json_bridge_matches_import_api(self) -> None:
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py",
            "dispatch_chain_bridge_policy",
        )
        result = subprocess.run(
            [sys.executable, "-B", str(POLICY), "--json"],
            input=json.dumps({"prompt": "do the task", "injected_context": ""}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["execution_contract"], policy.execution_contract())

    def test_js_static_constant_equals_python_contract(self) -> None:
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py",
            "dispatch_chain_static_policy",
        )
        js = SESSION_UTILS.read_text(encoding="utf-8")
        match = re.search(
            r"export const STATIC_EXECUTION_CONTRACT =\n((?:[ \t]+.*\n?)+)", js
        )
        self.assertIsNotNone(match, "STATIC_EXECUTION_CONTRACT constant not found")
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', match.group(1))
        js_contract = "".join(parts)
        self.assertEqual(policy.execution_contract(), js_contract)
        self.assertIn(CHAIN_OWNERSHIP, js_contract)


class ProtocolBlockChainDutyTests(unittest.TestCase):
    """B: the Chain duty lands in the in-progress branch only."""

    def _in_progress_text(self, root: Path) -> str:
        task_dir = root / "in-progress"
        task_dir.mkdir()
        _write_plan(
            task_dir,
            _plan(
                [
                    _task("first", "completed"),
                    _task("second", "in_progress", ["first"]),
                    _task("third", deps=["second"]),
                    _task(
                        "verify-final",
                        deps=["third"],
                    ),
                ]
            ),
        )
        return ep.plan_protocol_block(REPO_ROOT, task_dir)

    def _completed_text(self, root: Path) -> str:
        task_dir = root / "completed"
        task_dir.mkdir()
        _write_plan(task_dir, _plan(_completed_plan_tasks()))
        return ep.plan_protocol_block(REPO_ROOT, task_dir)

    def test_in_progress_branch_carries_neutral_chain_duty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = self._in_progress_text(Path(tmp))
        self.assertIn("## Trellis execution plan protocol", text)
        self.assertIn(CHAIN_DUTY, text)
        self.assertIn(DISPATCHED_LIMIT, text)
        self.assertIn(MAIN_IMPLEMENTER, text)
        self.assertIn(SILENT_RETURN, text)
        # The prohibition must stay scoped to a dispatched sub-agent.
        self.assertIn(
            "A dispatched sub-agent must not return to the main session "
            "after a single phase",
            text,
        )

    def test_completed_branch_has_no_chain_duty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            text = self._completed_text(Path(tmp))
        self.assertIn("fully completed", text)
        self.assertNotIn(CHAIN_DUTY, text)
        self.assertNotIn("Per phase loop", text)


def _completed_plan_tasks() -> list[dict]:
    return [
        _task("first", "completed"),
        _task("verify-final", "completed", ["first"]),
    ]


class WorkflowRoundContractTests(unittest.TestCase):
    """C channel 1: the tag block text; C channel 2: the real CLI delivery."""

    def setUp(self) -> None:
        self.workflow = WORKFLOW.read_text(encoding="utf-8")
        self.in_progress = tag_block(self.workflow, "in_progress")
        self.inline = tag_block(self.workflow, "in_progress-inline")

    def test_in_progress_block_defines_round_and_default_subject(self) -> None:
        block = re.sub(r"\s+", " ", self.in_progress)
        self.assertIn(ROUND_DEFAULT, block)
        self.assertIn(DEFAULT_SUBJECT, block)
        self.assertIn("one implement round = one dispatch", block)
        self.assertIn("terminal report phase", block)

    def test_in_progress_block_carries_both_user_exception_cases(self) -> None:
        block = re.sub(r"\s+", " ", self.in_progress)
        self.assertIn(USER_OVERRIDE, block)
        self.assertGreaterEqual(block.count("explicitly asks"), 2)
        self.assertIn("the main session acts as the implementer for that round", block)
        self.assertIn("write the plan first", block)
        self.assertIn("in-progress chain instead of re-planning", block)

    def test_inline_block_stays_unchanged(self) -> None:
        for phrase in INLINE_FORBIDDEN:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.inline)

    def test_existing_semantics_survive(self) -> None:
        self.assertIn("(or continue inline)", self.workflow)
        self.assertIn(
            "Round 1: the implementer reads PRD/Spec/code and writes the plan first",
            self.workflow,
        )
        self.assertIn("when the user explicitly says this is a small patch", self.workflow)
        self.assertIn("小修", self.workflow)

    def test_step_2_1_delivers_dispatch_scope_on_all_platforms(self) -> None:
        for platform in ("claude", "codex", "opencode"):
            with self.subTest(platform=platform):
                result = run_step("--step", "2.1", "--platform", platform)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Spawn the implement sub-agent", result.stdout)
                self.assertIn(
                    "one dispatch covers the whole remaining chain", result.stdout
                )
                # The round definition / exception belong to the tag block only.
                self.assertNotIn(ROUND_DEFAULT, result.stdout)
                self.assertNotIn(USER_OVERRIDE, result.stdout)

    def test_claude_family_step_output_has_no_codex_terms(self) -> None:
        for platform in ("claude", "opencode"):
            with self.subTest(platform=platform):
                result = run_step("--step", "2.1", "--platform", platform)
                self.assertEqual(result.returncode, 0, result.stderr)
                for term in CODEX_ONLY_TERMS:
                    self.assertNotIn(term, result.stdout)


class ImplementAgentChainContractTests(unittest.TestCase):
    """D: the four implement definitions share the same three new phrases."""

    def test_implement_agents_carry_chain_completion_and_report_lines(self) -> None:
        for relative in IMPLEMENT_AGENTS:
            with self.subTest(agent=relative):
                text = normalized(relative)
                self.assertIn("Do not return after a single phase", text)
                self.assertIn("not the end of the current phase", text)
                self.assertIn(REPORT_ADVANCED, text)
                self.assertIn(REPORT_REMAINING, text)

    @unittest.skipIf(tomllib is None, "tomllib unavailable; TOML parse not executed")
    def test_codex_toml_is_parseable(self) -> None:
        raw = (REPO_ROOT / ".codex" / "agents" / "trellis-implement.toml").read_text(
            encoding="utf-8"
        )
        tomllib.loads(raw)


class DispatchChainDerivationTests(unittest.TestCase):
    """E: the pure derivation matrix and the fail-soft status line."""

    def test_linear_chain_in_topological_order(self) -> None:
        plan = _plan(
            [
                _task("a", "completed"),
                _task("b", "in_progress", ["a"]),
                _task("c", deps=["b"]),
                _task("r", deps=["c"]),
            ]
        )
        chain = ep._dispatch_chain(plan)
        self.assertEqual(chain, ["b", "c", "r"])
        self.assertNotIn("a", chain)  # completed phases are pruned

    def test_diamond_dependencies(self) -> None:
        plan = _plan(
            [
                _task("a", "completed"),
                _task("b", "in_progress", ["a"]),
                _task("c", deps=["a"]),
                _task("d", deps=["b", "c"]),
                _task("r", deps=["d"]),
            ]
        )
        self.assertEqual(ep._dispatch_chain(plan), ["b", "c", "d", "r"])

    def test_blocked_phase_prunes_downstream_without_traversal(self) -> None:
        plan = _plan(
            [
                _task("a", "completed"),
                _task("b", "blocked", ["a"]),
                _task("c", deps=["b"]),
                _task("x"),
            ]
        )
        chain = ep._dispatch_chain(plan)
        self.assertEqual(chain, ["x"])
        self.assertNotIn("c", chain)  # blocked branch never traversed

    def test_declaration_order_tie_break_not_lexicographic(self) -> None:
        plan = _plan(
            [
                _task("z"),
                _task("a"),
                _task("r", deps=["z", "a"]),
            ]
        )
        self.assertEqual(ep._dispatch_chain(plan), ["z", "a", "r"])

    def test_parallel_plan_still_emits_the_whole_remaining_forest(self) -> None:
        plan = _plan(
            [
                _task("a", "completed"),
                _task("b", deps=["a"]),
                _task("c", deps=["a"]),
                _task("d", deps=["b", "c"]),
                _task("r", deps=["d"]),
            ],
            parallel=True,
        )
        self.assertEqual(ep._dispatch_chain(plan), ["b", "c", "d", "r"])

    def test_all_completed_yields_empty(self) -> None:
        plan = _plan([_task("a", "completed"), _task("r", "completed", ["a"])])
        self.assertEqual(ep._dispatch_chain(plan), [])

    def test_malformed_or_cyclic_plan_fails_soft(self) -> None:
        for broken in (
            {},
            {"tasks": "nope"},
            {"tasks": [None, 42, "x"]},
            _plan([_task("a", "in_progress", ["b"]), _task("b", deps=["a"])]),
        ):
            with self.subTest(plan=repr(broken)[:60]):
                self.assertEqual(ep._dispatch_chain(broken), [])

    def test_format_status_chain_line_in_non_verbose_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _write_plan(
                task_dir,
                _plan(
                    [
                        _task("first", "completed"),
                        _task("second", "in_progress", ["first"]),
                        _task("third", deps=["second"]),
                        _task("verify-final", deps=["third"]),
                    ]
                ),
            )
            text = ep.format_status(task_dir, REPO_ROOT, verbose=False)
            chain_line = next(
                line for line in text.splitlines() if line.startswith("dispatch chain:")
            )
            self.assertEqual(
                chain_line, "dispatch chain: second -> third -> verify-final"
            )
            self.assertNotIn("frozen plans:", chain_line)
            self.assertNotIn("[", chain_line)  # never mimics the verbose task rows

    def test_format_status_hides_chain_when_all_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _write_plan(
                task_dir,
                _plan([_task("a", "completed"), _task("r", "completed", ["a"])]),
            )
            text = ep.format_status(task_dir, REPO_ROOT, verbose=False)
            self.assertNotIn("dispatch chain:", text)
            self.assertIn("ALL TASKS COMPLETED", text)

    def test_format_status_malformed_plan_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _write_plan(task_dir, {"schema": 3, "tasks": "nope"})
            text = ep.format_status(task_dir, REPO_ROOT, verbose=False)
            self.assertNotIn("dispatch chain:", text)

    def test_format_status_damaged_audit_does_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            _write_plan(
                task_dir,
                _plan(
                    [
                        _task("first", "completed"),
                        _task("second", "in_progress", ["first"]),
                        _task("third", deps=["second"]),
                    ]
                ),
            )
            (task_dir / ep.EVENTS_FILE).write_text(
                "{not valid json at all\n", encoding="utf-8", newline="\n"
            )
            text = ep.format_status(task_dir, REPO_ROOT, verbose=False)
            self.assertIn("AUDIT DAMAGED", text)
            chain_line = next(
                line for line in text.splitlines() if line.startswith("dispatch chain:")
            )
            self.assertEqual(chain_line, "dispatch chain: second -> third")

    def test_format_status_sequel_layout_keeps_chain_separate_from_frozen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task_dir = Path(tmp)
            (task_dir / ep.PLAN_FILE).write_text(
                json.dumps({"schema": 3, "live": 2}),
                encoding="utf-8",
                newline="\n",
            )
            frozen_dir = task_dir / ep.PLANS_DIR / "1"
            frozen_dir.mkdir(parents=True)
            _write_plan(
                frozen_dir,
                _plan([_task("old", "completed"), _task("old-r", "completed", ["old"])]),
            )
            live_dir = task_dir / ep.PLANS_DIR / "2"
            live_dir.mkdir()
            _write_plan(
                live_dir,
                _plan(
                    [
                        _task("first", "completed"),
                        _task("second", "in_progress", ["first"]),
                        _task("third", deps=["second"]),
                    ]
                ),
            )
            text = ep.format_status(task_dir, REPO_ROOT, verbose=False)
            self.assertIn("frozen plans:", text)
            chain_line = next(
                line for line in text.splitlines() if line.startswith("dispatch chain:")
            )
            self.assertEqual(chain_line, "dispatch chain: second -> third")
            self.assertNotIn("frozen plans:", chain_line)


if __name__ == "__main__":
    unittest.main()