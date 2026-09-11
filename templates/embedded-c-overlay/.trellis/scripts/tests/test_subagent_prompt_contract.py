"""Behavior tests for implement dispatch prompt normalization."""

import contextlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_module(relative_path: str, name: str):
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SubagentPromptContractTests(unittest.TestCase):
    def _sample_prompt(self):
        return (
            "目标：删除无关 handler。\n"
            "范围：protocol_app.c。\n"
            "非目标：不改变协议格式。\n"
            "验收条件：逐个 grep 全工程验证，每项单独构建。\n"
            "验证命令：\n"
            "```bash\n"
            "grep -R handler .\n"
            "```\n"
            "执行策略：逐个 grep handler；每项单独构建。"
        )

    def test_policy_preserves_acceptance_and_commands_but_rewrites_execution(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy"
        )
        normalized = policy.normalize_implement_prompt(self._sample_prompt())
        self.assertIn("## Goal", normalized)
        self.assertIn("## Scope", normalized)
        self.assertIn("## Non-goals", normalized)
        self.assertIn("逐个 grep 全工程验证，每项单独构建。", normalized)
        self.assertIn("grep -R handler .", normalized)
        self.assertIn("使用一次批量扫描全部目标", normalized)
        self.assertIn("按阶段统一构建一次", normalized)
        self.assertNotIn("## Business requirements (preserved", normalized)
        self.assertIn(policy.policy_marker(), normalized)

    def test_unclassified_tool_wording_is_business_text_not_execution_order(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_unknown"
        )
        normalized = policy.normalize_implement_prompt(
            "请逐个文件运行检查，但目标是保留现有行为。"
        )
        self.assertIn("Business requirements (preserved", normalized)
        self.assertIn("请逐个文件运行检查", normalized)
        self.assertIn("不构成强制执行顺序", normalized)

    def test_english_execution_variants_are_batched(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_en"
        )
        normalized = policy.normalize_implement_prompt(
            "Execution strategy:\nfor each handler, run grep\n"
            "rebuild after every small change"
        )
        self.assertIn("run one batch scan for all handler", normalized)
        self.assertIn("rebuild once after the phase is complete", normalized)

    def test_common_chinese_variants_and_wrapped_titles_are_batched(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_variants"
        )
        normalized = policy.normalize_implement_prompt(
            "**执行策略：** 每一个 handler 分别运行 `grep`。\n"
            "逐一检查所有字段。\n"
            "每次改动后重新编译。\n"
            "验收标准（必须通过）：每个目标都必须保留。"
        )
        self.assertIn("使用一次批量扫描全部 handler", normalized)
        self.assertIn("使用一次批量扫描全部字段", normalized)
        self.assertIn("阶段修改完成后统一验证一次", normalized)
        self.assertIn("每个目标都必须保留", normalized)

    def test_numbered_execution_steps_stay_in_execution_section(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_numbered"
        )
        normalized = policy.normalize_implement_prompt(
            "执行策略：\n"
            "1. 每一个 handler 分别运行 grep\n"
            "2. 每处重新编译\n"
            "验收条件：所有目标均通过测试。"
        )
        self.assertIn("使用一次批量扫描全部 handler", normalized)
        self.assertIn("按阶段统一构建一次", normalized)
        self.assertIn("所有目标均通过测试", normalized)
        self.assertNotIn("每一个 handler 分别运行 grep", normalized)

    def test_additional_chinese_per_item_variants_are_batched(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_more_variants"
        )
        normalized = policy.normalize_implement_prompt(
            "执行策略：\n每项分别检查字段。\n每处重新编译。"
        )
        self.assertIn("使用一次批量扫描全部字段", normalized)
        self.assertIn("按阶段统一构建一次", normalized)

    def test_execution_does_not_leak_across_unknown_heading(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_boundary"
        )
        normalized = policy.normalize_implement_prompt(
            "执行策略：逐个 grep handler。\n"
            "### 额外约束\n"
            "每一个目标必须单独记录审计证据。"
        )
        self.assertIn("使用一次批量扫描全部目标", normalized)
        self.assertIn("每一个目标必须单独记录审计证据", normalized)
        self.assertNotIn("使用一次批量扫描全部目标必须单独记录审计证据", normalized)

    def test_exact_injected_context_copy_is_omitted_only(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_dedup"
        )
        repeated = "验收依据：" + ("完整上下文内容。" * 40)
        normalized = policy.normalize_implement_prompt(
            f"目标说明\n{repeated}\n保留要求", f"=== prd.md ===\n{repeated}\n"
        )
        self.assertNotIn(repeated, normalized)
        self.assertIn("目标说明", normalized)
        self.assertIn("保留要求", normalized)
        self.assertIn("duplicate omitted", normalized)

    def test_claude_and_codex_builders_have_equivalent_behavior(self):
        original = self._sample_prompt()
        outputs = []
        for relative, name in (
            (".claude/hooks/inject-subagent-context.py", "claude_hook"),
            (".codex/hooks/inject-subagent-context.py", "codex_hook"),
        ):
            hook = load_module(relative, name)
            outputs.append(hook.build_implement_prompt(original, "curated context"))
        for output in outputs:
            self.assertIn("逐个 grep 全工程验证，每项单独构建。", output)
            self.assertIn("使用一次批量扫描全部目标", output)
            self.assertIn("Task requirements (normalized from", output)
        contract_sections = [
            output.split("## Trellis execution contract (applies to the task below)\n", 1)[1]
            .split("## Task requirements (normalized from the dispatch request)", 1)[0]
            for output in outputs
        ]
        self.assertEqual(contract_sections[0], contract_sections[1])

    def _run_pretool_main(self, relative, name):
        hook = load_module(relative, name)
        hook.find_repo_root = lambda _cwd: str(REPO_ROOT)
        hook.get_current_task = lambda *_args, **_kwargs: ".trellis"
        hook.get_implement_context = lambda *_args: "curated context"
        input_data = {
            "tool_name": "Task",
            "cwd": str(REPO_ROOT),
            "tool_input": {
                "subagent_type": "trellis-implement",
                "prompt": (
                    "目标：保留协议验收。\n"
                    "验收条件：必须通过现有测试。\n"
                    "验证命令：python -m unittest discover。\n"
                    "执行策略：逐个 grep handler。"
                ),
            },
        }
        output = io.StringIO()
        previous_stdin = sys.stdin
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            try:
                sys.stdin = io.StringIO(json.dumps(input_data))
                with self.assertRaises(SystemExit):
                    hook.main()
            finally:
                sys.stdin = previous_stdin
        return json.loads(output.getvalue())

    def test_claude_pretooluse_json_contains_normalized_prompt(self):
        payload = self._run_pretool_main(
            ".claude/hooks/inject-subagent-context.py", "claude_hook_main"
        )
        prompt = payload["hookSpecificOutput"]["updatedInput"]["prompt"]
        self.assertIn("保留协议验收", prompt)
        self.assertIn("必须通过现有测试", prompt)
        self.assertIn("python -m unittest discover", prompt)
        self.assertNotIn("逐个 grep handler", prompt)
        self.assertIn("Trellis execution contract", prompt)
        json.dumps(payload)

    def test_codex_pretooluse_json_contains_normalized_prompt(self):
        payload = self._run_pretool_main(
            ".codex/hooks/inject-subagent-context.py", "codex_hook_main"
        )
        prompt = payload["hookSpecificOutput"]["updatedInput"]["prompt"]
        self.assertIn("保留协议验收", prompt)
        self.assertIn("必须通过现有测试", prompt)
        self.assertIn("python -m unittest discover", prompt)
        self.assertNotIn("逐个 grep handler", prompt)
        self.assertIn("Trellis execution contract", prompt)
        json.dumps(payload)

    def _run_native_main(self, event, name="codex_native_main"):
        hook = load_module(".codex/hooks/inject-subagent-context.py", name)
        hook.find_repo_root = lambda _cwd: str(REPO_ROOT)
        hook.get_current_task = lambda *_args, **_kwargs: ".trellis"
        hook.get_implement_context = lambda *_args: "curated context"
        output = io.StringIO()
        previous_stdin = sys.stdin
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            try:
                sys.stdin = io.StringIO(json.dumps(event))
                with self.assertRaises(SystemExit):
                    hook.main()
            finally:
                sys.stdin = previous_stdin
        return hook, json.loads(output.getvalue())

    def test_codex_native_subagentstart_json_uses_same_builder(self):
        _, payload = self._run_native_main({
            "hookEventName": "SubagentStart",
            "agent_type": "trellis-implement",
            "session_id": "parent-session",
            "cwd": str(REPO_ROOT),
            "prompt": (
                "目标：保留协议验收。\n"
                "验收条件：必须通过现有测试。\n"
                "验证命令：python -m unittest discover。\n"
                "执行策略：逐个 grep handler。"
            ),
        })
        additional = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("保留协议验收", additional)
        self.assertIn("必须通过现有测试", additional)
        self.assertIn("python -m unittest discover", additional)
        self.assertNotIn("逐个 grep handler", additional)
        self.assertIn("Trellis execution contract", additional)
        json.dumps(payload)

    def test_codex_native_without_prompt_emits_fallback_contract(self):
        _, payload = self._run_native_main({
            "hookEventName": "SubagentStart",
            "agent_type": "trellis-implement",
            "session_id": "parent-session",
            "cwd": str(REPO_ROOT),
        }, "codex_native_no_prompt")
        additional = payload["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Native dispatch fallback", additional)
        self.assertIn("not a mandatory execution order", additional)
        self.assertIn("Trellis execution contract", additional)

    def test_codex_native_exception_path_emits_valid_minimal_json(self):
        hook = load_module(
            ".codex/hooks/inject-subagent-context.py", "codex_native_exception"
        )
        hook._handle_codex_subagent_start = lambda _event: (_ for _ in ()).throw(
            RuntimeError("fixture failure")
        )
        output = io.StringIO()
        previous_stdin = sys.stdin
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            try:
                sys.stdin = io.StringIO(json.dumps({"hookEventName": "SubagentStart"}))
                with self.assertRaises(SystemExit):
                    hook.main()
            finally:
                sys.stdin = previous_stdin
        payload = json.loads(output.getvalue())
        self.assertIn("Trellis execution contract", payload["hookSpecificOutput"]["additionalContext"])

    def test_channel_implement_template_contains_same_contract(self):
        template = (REPO_ROOT / ".trellis/agents/implement.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Execution batches (mandatory)", template)
        self.assertIn("report granularity", template)
        self.assertIn("call `grep` once per item", template)
        self.assertIn("Stop on completion", template)


class OpenCodePromptPolicyBridgeTests(unittest.TestCase):
    """The OpenCode plugin must reuse the Python policy through --json.

    JavaScript must never re-implement the normalization regex tables; these
    tests lock the bridge contract and the static degradation fallback text.
    """

    POLICY_SCRIPT = REPO_ROOT / ".trellis" / "scripts" / "common" / "subagent_prompt_policy.py"
    PLUGIN = REPO_ROOT / ".opencode" / "plugins" / "inject-subagent-context.js"
    SESSION_UTILS = REPO_ROOT / ".opencode" / "lib" / "session-utils.js"

    def _run_bridge(self, payload, extra_args=("--json",)):
        return subprocess.run(
            [sys.executable, "-B", str(self.POLICY_SCRIPT), *extra_args],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            env={k: v for k, v in os.environ.items() if k != "PYTHONHOME"},
        )

    def test_bridge_matches_import_api(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_bridge"
        )
        sample = (
            "目标：删除无关 handler。\n"
            "验收条件：逐个 grep 全工程验证，每项单独构建。\n"
            "验证命令：\n"
            "```bash\n"
            "grep -R handler .\n"
            "```\n"
            "执行策略：逐个 grep handler；每项单独构建。"
        )
        result = self._run_bridge(json.dumps({"prompt": sample, "injected_context": "ctx"}))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(
            data["normalized_prompt"],
            policy.normalize_implement_prompt(sample, "ctx"),
        )
        self.assertEqual(data["execution_contract"], policy.execution_contract())
        self.assertEqual(data["policy_marker"], policy.policy_marker())
        self.assertIn("使用一次批量扫描全部目标", data["normalized_prompt"])
        self.assertIn("grep -R handler .", data["normalized_prompt"])

    def test_bridge_rejects_invalid_inputs(self):
        for payload in (
            '"just a string"',
            "[1, 2]",
            '{"injected_context": "only"}',
            '{"prompt": 42}',
            '{"prompt": "x", "injected_context": null}',
            "not json at all",
        ):
            result = self._run_bridge(payload)
            self.assertNotEqual(result.returncode, 0, f"bridge accepted {payload!r}")
            self.assertIn("subagent_prompt_policy", result.stderr)

    def test_bridge_without_json_flag_prints_usage(self):
        result = self._run_bridge("{}", extra_args=())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("usage:", result.stderr)

    def test_import_semantics_unchanged_for_hook_callers(self):
        # The in-process API the Claude/Codex hooks use must keep working.
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_import"
        )
        self.assertIn(
            policy.policy_marker(),
            policy.normalize_implement_prompt("目标：X。\n执行步骤：每个符号逐个 grep", ""),
        )

    def test_js_static_fallback_strings_equal_python_canonical(self):
        policy = load_module(
            ".trellis/scripts/common/subagent_prompt_policy.py", "prompt_policy_static"
        )
        js = self.SESSION_UTILS.read_text(encoding="utf-8")
        marker_m = re.search(r'export const STATIC_POLICY_MARKER = "(.*)"', js)
        self.assertIsNotNone(marker_m, "STATIC_POLICY_MARKER constant not found")
        self.assertEqual(policy.policy_marker(), marker_m.group(1))
        contract_m = re.search(
            r"export const STATIC_EXECUTION_CONTRACT =\n((?:[ \t]+.*\n?)+)", js
        )
        self.assertIsNotNone(contract_m, "STATIC_EXECUTION_CONTRACT constant not found")
        parts = re.findall(r'"((?:[^"\\]|\\.)*)"', contract_m.group(1))
        js_contract = "".join(parts)
        self.assertEqual(policy.execution_contract(), js_contract)

    def test_plugin_uses_python_bridge_and_keeps_business_text(self):
        plugin = self.PLUGIN.read_text(encoding="utf-8")
        self.assertIn("normalizePromptViaPython", plugin)
        self.assertIn("## Task requirements (normalized from the dispatch request)", plugin)
        self.assertIn("## Trellis execution contract (applies to the task below)", plugin)
        self.assertIn("- Do NOT execute git commit, only code modifications", plugin)
        self.assertIn("The context above was prepared by Trellis", plugin)
        # The degradation path keeps the raw prompt + static contract, and the
        # plugin must say so explicitly instead of silently normalizing.
        self.assertIn("prompt normalization degraded", plugin)

    def test_js_check_prompt_section_matches_python_hook_builders(self):
        claude = load_module(
            ".claude/hooks/inject-subagent-context.py", "claude_check_shape"
        )
        codex = load_module(
            ".codex/hooks/inject-subagent-context.py", "codex_check_shape"
        )
        sections = []
        for hook in (claude, codex):
            prompt = hook.build_check_prompt("task facts", "curated context")
            body = prompt.split("## Finding handling", 1)[1].split("## Important Constraints", 1)[0]
            sections.append(re.sub(r"\s+", " ", body).strip())
        self.assertEqual(sections[0], sections[1])
        plugin = self.PLUGIN.read_text(encoding="utf-8")
        js_body = plugin.split("## Finding handling", 1)[1].split("## Important Constraints", 1)[0]
        js_norm = re.sub(r"\$\{[^}]*\}", "", js_body)
        js_norm = re.sub(r"\s+", " ", js_norm).strip()
        self.assertEqual(sections[0], js_norm,
                         "OpenCode check prompt must carry the same Finding-handling contract")


if __name__ == "__main__":
    unittest.main()
