"""Contract tests for the OpenCode platform closure in the release template.

OpenCode is the third default delivery platform of the embedded-c overlay.
These tests prove the observable template contracts required by task
09-11-support-opencode-platform without pretending to run a real OpenCode
network session:

- the managed asset closure is complete: every path enumerated by upstream
  Trellis 0.6.10 ``collectOpenCodeTemplates()`` is present, plus the mirrored
  project-custom Skills (byte-identical to the authoritative .agents copies);
- each plugin module exposes exactly one default factory export (OpenCode
  1.2.x calls every export as a factory);
- Agent frontmatter/permissions match role boundaries;
- commands are routing-only and never clone review tables;
- Channel Skill docs keep worker providers at claude|codex;
- the bundled generic ``trellis-check`` Skill was rewritten to the
  five-level profile contract (no three-level / Web-lint / blanket-self-fix
  semantics remain in the .opencode tree);
- a Node harness exercises the real lib/plugin behavior: session-key parity,
  fail-closed isolation, Shell identity bridge, SessionStart dedup/compaction,
  per-turn state sourced from workflow.md tag blocks, sub-agent context
  ordering and budget notices, blocked-dispatch fail-closed, and parity
  between the JavaScript prompt path and the Python policy normalizer.

When Node is unavailable, the runtime cases are explicitly SKIPPED — Python
assertions never impersonate JavaScript execution.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]  # templates/embedded-c-overlay/
OPENCODE = TEMPLATE_ROOT / ".opencode"
TPL_PARENT_FOR_HARNESS = str(TEMPLATE_ROOT).replace("\\", "/")

_NODE = shutil.which("node")

LEVELS = ("light", "standard", "reinforced", "comprehensive", "strict")

STALE_ENUMERATIONS = (
    "light|standard|strict",
    "light/standard/strict",
    "light, standard, or strict",
    "`light`, `standard`, or `strict`",
    "`light`, `standard`, `strict`",
)

CUSTOM_MIRROR_PAIRS = (
    (".agents/skills/grill-me/SKILL.md", ".opencode/skills/grill-me/SKILL.md"),
    (
        ".agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md",
        ".opencode/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md",
    ),
    (
        ".agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md",
        ".opencode/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md",
    ),
    (".agents/skills/trellis-finish-work/SKILL.md", ".opencode/skills/trellis-finish-work/SKILL.md"),
    (".agents/skills/trellis-channel/SKILL.md", ".opencode/skills/trellis-channel/SKILL.md"),
    (
        ".agents/skills/trellis-channel/references/command-reference.md",
        ".opencode/skills/trellis-channel/references/command-reference.md",
    ),
    (
        ".agents/skills/trellis-channel/references/forum.md",
        ".opencode/skills/trellis-channel/references/forum.md",
    ),
    (
        ".agents/skills/trellis-channel/references/progress-debugging.md",
        ".opencode/skills/trellis-channel/references/progress-debugging.md",
    ),
    (
        ".agents/skills/trellis-channel/references/workers.md",
        ".opencode/skills/trellis-channel/references/workers.md",
    ),
    (
        ".agents/skills/trellis-channel/references/workflows.md",
        ".opencode/skills/trellis-channel/references/workflows.md",
    ),
)

# Roots every downstream OpenCode install needs regardless of Node presence.
REQUIRED_ROOTS = (
    ".opencode/package.json",
    ".opencode/lib/trellis-context.js",
    ".opencode/lib/session-utils.js",
    ".opencode/plugins/session-start.js",
    ".opencode/plugins/inject-workflow-state.js",
    ".opencode/plugins/inject-subagent-context.js",
    ".opencode/agents/trellis-research.md",
    ".opencode/agents/trellis-implement.md",
    ".opencode/agents/trellis-check.md",
    ".opencode/commands/trellis/start.md",
    ".opencode/commands/trellis/continue.md",
    ".opencode/commands/trellis/finish-work.md",
)
REQUIRED_GENERIC_SKILLS = (
    "trellis-before-dev",
    "trellis-brainstorm",
    "trellis-break-loop",
    "trellis-check",
    "trellis-update-spec",
    "trellis-meta",
    "trellis-session-insight",
    "trellis-spec-bootstrap",
    "trellis-channel",
)


def _read(rel: str) -> str:
    path = TEMPLATE_ROOT / rel
    assert path.is_file(), f"missing OpenCode platform file: {path}"
    return path.read_text(encoding="utf-8")


class OpenCodeClosureStaticTests(unittest.TestCase):
    def test_required_roots_present(self) -> None:
        for rel in REQUIRED_ROOTS:
            self.assertTrue((TEMPLATE_ROOT / rel).is_file(), f"missing {rel}")

    def test_generic_skill_roots_present(self) -> None:
        for skill in REQUIRED_GENERIC_SKILLS:
            self.assertTrue(
                (OPENCODE / "skills" / skill / "SKILL.md").is_file(),
                f"missing bundled skill {skill}",
            )

    @unittest.skipIf(_NODE is None, "node is not available; collector parity not executed")
    def test_collector_path_parity(self) -> None:
        # With `node -e`, forwarded args start at process.argv[1].
        script = (
            "const { pathToFileURL } = require('url');"
            "import(pathToFileURL(process.argv[1]).href).then(m => {"
            " process.stdout.write(JSON.stringify([...m.collectOpenCodeTemplates().keys()]));"
            "}).catch(e => { console.error(String(e)); process.exit(1); });"
        )
        pkg_entry = "D:/node/node_global/node_modules/@mindfoldhq/trellis"
        candidates = [pkg_entry]
        result = None
        for base in candidates:
            probe = subprocess.run(
                [_NODE, "-e", script, str((Path(base) / "dist/configurators/opencode.js").as_posix())],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            if probe.returncode == 0:
                result = probe
                break
        if result is None:
            self.skipTest("upstream @mindfoldhq/trellis 0.6.10 not installed here; "
                          "collector parity not run (roots above were checked)")
            return
        collector_paths = json.loads(result.stdout)
        self.assertTrue(len(collector_paths) >= 50, "collector returned an unexpected file set")
        for rel in collector_paths:
            disk = TEMPLATE_ROOT / Path(rel.replace("\\", "/"))
            self.assertTrue(disk.exists(), f"collector path missing from template closure: {rel}")

    def test_package_json_declares_plugin_dependency(self) -> None:
        data = json.loads(_read(".opencode/package.json"))
        deps = data.get("dependencies", {})
        self.assertIn("@opencode-ai/plugin", deps)
        self.assertTrue(deps["@opencode-ai/plugin"].lstrip("^~>= ").split(".")[0].isdigit())

    def test_plugins_have_only_one_default_export(self) -> None:
        pattern = re.compile(r"^export\s+(?!default)", re.M)
        for rel in (
            ".opencode/plugins/session-start.js",
            ".opencode/plugins/inject-workflow-state.js",
            ".opencode/plugins/inject-subagent-context.js",
        ):
            text = _read(rel)
            self.assertEqual(text.count("export default"), 1, f"{rel}: exactly one default export")
            self.assertIsNone(pattern.search(text), f"{rel}: named exports would be invoked as plugin factories")
        # Testable pure functions live in lib/, which plugins import.
        for rel in (".opencode/lib/trellis-context.js", ".opencode/lib/session-utils.js"):
            self.assertRegex(_read(rel), r"export (function|const|class)")

    def test_agent_frontmatter_and_role_boundaries(self) -> None:
        cases = {
            ".opencode/agents/trellis-research.md": ["mode: subagent", "task: deny"],
            ".opencode/agents/trellis-implement.md": ["mode: subagent", "task: deny"],
            ".opencode/agents/trellis-check.md": ["mode: subagent", "task: deny"],
        }
        for rel, needles in cases.items():
            text = _read(rel)
            self.assertTrue(text.startswith("---"), f"{rel} must start with frontmatter")
            front = text.split("---", 2)[1]
            self.assertIn("description:", front)
            for needle in needles:
                self.assertIn(needle, front, f"{rel} frontmatter missing {needle!r}")
        research = _read(".opencode/agents/trellis-research.md")
        self.assertIn("Write FORBIDDEN", research)
        self.assertIn("research/", research)
        implement = _read(".opencode/agents/trellis-implement.md")
        self.assertIn("Execution Plan Protocol", implement)
        self.assertIn("plan.py", implement)
        self.assertIn("Mandatory execution batches", implement)
        self.assertIn("git commit", implement)  # in the Forbidden Operations list
        check = _read(".opencode/agents/trellis-check.md")
        self.assertIn("PROJECT_PREFIX-trellis-review", check)
        self.assertIn("mechanical, small, and determinate", check)
        for level in LEVELS:
            self.assertIn(level, check, f"opencode check agent missing level {level}")

    def test_commands_are_routing_only(self) -> None:
        start = _read(".opencode/commands/trellis/start.md")
        self.assertIn("--platform opencode", start)
        for level in LEVELS:
            self.assertIn(level, start, f"start.md must accept level {level}")
        self.assertIn("task.py start", start)
        continue_cmd = _read(".opencode/commands/trellis/continue.md")
        self.assertIn("--step <X.X> --platform opencode", continue_cmd)
        self.assertIn("This command is only a routing entry point", continue_cmd)
        finish = _read(".opencode/commands/trellis/finish-work.md")
        self.assertIn("trellis-finish-work", finish)
        self.assertIn("Code commits belong to workflow Phase 3.4", finish)
        self.assertIn("Never push", finish)
        for rel, text in (("start", start), ("continue", continue_cmd), ("finish-work", finish)):
            for stale in STALE_ENUMERATIONS:
                self.assertNotIn(stale, text, f"stale three-level text in command {rel}")

    def test_custom_skill_mirrors_are_byte_identical(self) -> None:
        for src, dst in CUSTOM_MIRROR_PAIRS:
            self.assertEqual(
                (TEMPLATE_ROOT / src).read_text(encoding="utf-8"),
                (TEMPLATE_ROOT / dst).read_text(encoding="utf-8"),
                f"mirror drift: {dst}",
            )

    def test_channel_docs_keep_providers_claude_codex(self) -> None:
        skill = _read(".opencode/skills/trellis-channel/SKILL.md")
        self.assertIn("claude", skill.lower())
        self.assertIn("codex", skill.lower())
        for path in (OPENCODE / "skills" / "trellis-channel").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("provider opencode", text.lower(), path.name)
            self.assertNotIn("--provider <claude|codex|opencode", text)

    def test_bundled_check_skill_follows_five_level_contract(self) -> None:
        text = _read(".opencode/skills/trellis-check/SKILL.md")
        self.assertIn("PROJECT_PREFIX-trellis-review", text)
        for level in LEVELS:
            self.assertIn(level, text, f"bundled check skill missing level {level}")
        self.assertNotIn("TypeCheck: Passed", text)
        self.assertNotIn("fix them directly. Re-run project checks", text)
        self.assertIn("not applicable", text)
        self.assertIn("hardware validation", text.lower())

    def test_no_stale_semantics_anywhere_in_opencode_tree(self) -> None:
        for path in OPENCODE.rglob("*"):
            if not path.is_file() or path.suffix not in (".md", ".js", ".json"):
                continue
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(TEMPLATE_ROOT).as_posix()
            for line in text.splitlines():
                for stale in STALE_ENUMERATIONS:
                    self.assertNotIn(stale, line, f"stale three-level text in {rel}: {stale!r}")
                self.assertNotIn("--provider opencode", line, rel)
                self.assertNotIn("<PROJECT_PREFIX>", line, rel)
                self.assertNotIn("<PROJECT_NAME>", line, rel)
            # Blanket self-fix / web-lint assumptions must not survive.
            if path.suffix == ".md" and "skills/trellis-" in rel:
                forbidden = ("Fix issues yourself", "Run project's lint and typecheck", "self-fix issues")
                for needle in forbidden:
                    self.assertNotIn(
                        needle.lower(), text.lower(),
                        f"stale blanket-fix text {needle!r} in {rel}",
                    )

    def test_workflow_declares_three_platform_dispatch(self) -> None:
        workflow = (TEMPLATE_ROOT / ".trellis" / "workflow.md").read_text(encoding="utf-8")
        norm = re.sub(r"\s+", " ", workflow)
        self.assertIn("Sub-agent dispatch protocol in this project applies to Claude Code, Codex, and OpenCode", norm)
        self.assertNotIn("applies only to Claude Code and Codex", norm)
        self.assertIn("[OpenCode]", workflow)
        self.assertIn("`trellis channel` managed workers remain `--provider claude|codex`", norm)


_JS_RUNTIME_HARNESS = r"""
import { mkdtempSync, writeFileSync, readFileSync, mkdirSync, cpSync } from "fs"
import { join } from "path"
import { tmpdir } from "os"
import { pathToFileURL } from "url"
import process from "process"

delete process.env.TRELLIS_CONTEXT_ID
delete process.env.OPENCODE_SESSION_ID
delete process.env.OPENCODE_SESSIONID
delete process.env.OPENCODE_RUN_ID

const TPL = process.argv[2]
let failures = 0
function check(name, cond, extra = "") {
  if (!cond) { failures++; console.log(`FAIL ${name} :: ${String(extra).slice(0, 220)}`) }
}
function ok(name) { console.log(`OK ${name}`) }

const mod = await import(pathToFileURL(join(TPL, ".opencode/lib/trellis-context.js")).href)
const su = await import(pathToFileURL(join(TPL, ".opencode/lib/session-utils.js")).href)
const subagentPlugin = (await import(pathToFileURL(join(TPL, ".opencode/plugins/inject-subagent-context.js")).href)).default
const wfPlugin = (await import(pathToFileURL(join(TPL, ".opencode/plugins/inject-workflow-state.js")).href)).default
const ssPlugin = (await import(pathToFileURL(join(TPL, ".opencode/plugins/session-start.js")).href)).default

// ---- temp Trellis project ----
const repo = mkdtempSync(join(tmpdir(), "octpl-"))
mkdirSync(join(repo, ".trellis"), { recursive: true })
cpSync(join(TPL, ".trellis/scripts"), join(repo, ".trellis/scripts"), { recursive: true })
writeFileSync(join(repo, ".trellis/config.yaml"), "context_injection:\n  max_file_bytes: 32768\n  max_artifact_bytes: 65536\n  max_total_bytes: 131072\n\nprompt_injection:\n  skip_keyword: \"no-trellis\"\n")
writeFileSync(join(repo, ".trellis/workflow.md"), "## Phase Index\n[workflow-state:no_task]\nOPENCODE-FIXTURE-NOTASK-BODY\n[/workflow-state:no_task]\n[workflow-state:in_progress]\nOPENCODE-FIXTURE-INPROG-BODY\n[/workflow-state:in_progress]\n## Phase 1: Plan\n")
const task = join(repo, ".trellis/tasks/t1")
mkdirSync(join(task, "research"), { recursive: true })
writeFileSync(join(task, "task.json"), JSON.stringify({ id: "t1", status: "in_progress" }))
writeFileSync(join(task, "prd.md"), "# PRD marker body")
writeFileSync(join(task, "design.md"), "# Design marker body")
writeFileSync(join(task, "implement.md"), "# Plan marker body")
mkdirSync(join(repo, ".trellis/spec/main"), { recursive: true })
writeFileSync(join(repo, ".trellis/spec/main/index.md"), "# main spec index marker")
writeFileSync(join(task, "implement.jsonl"), JSON.stringify({ file: ".trellis/spec/main/index.md", reason: "spec" }) + "\n")
writeFileSync(join(task, "check.jsonl"), JSON.stringify({ file: ".trellis/spec/main/index.md", reason: "spec" }) + "\n")
mkdirSync(join(repo, ".trellis/.runtime/sessions"), { recursive: true })
writeFileSync(join(repo, ".trellis/.runtime/sessions/opencode_ses_main.json"), JSON.stringify({ current_task: ".trellis/tasks/t1" }))

const hooks = await subagentPlugin({ directory: repo, platform: "linux", env: {} })
const before = hooks["tool.execute.before"]

// context ordering: jsonl -> prd -> design -> implement -> plan protocol
const implArgs = { subagent_type: "trellis-implement", prompt: "Active task: .trellis/tasks/t1\n目标: 完成 X。\n执行策略: 每个符号逐个 grep。\n验收条件: python run_tests.py" }
await before({ tool: "task", sessionID: "ses_main" }, { args: implArgs })
const p = implArgs.prompt
const order = ["=== .trellis/spec/main/index.md ===", "=== .trellis/tasks/t1/prd.md (Requirements) ===", "=== .trellis/tasks/t1/design.md (Technical Design) ===", "=== .trellis/tasks/t1/implement.md (Execution Plan) ===", "## Trellis execution plan protocol"]
let pos = -1
for (const needle of order) {
  const idx = p.indexOf(needle)
  check("order-" + needle.slice(0, 20), idx > pos, `idx=${idx} pos=${pos}`)
  pos = idx
}
check("impl-normalized", p.includes("[Trellis dispatch policy normalized]") && !p.includes("逐个 grep"), p.slice(0, 120))
check("impl-acceptance-verbatim", p.includes("python run_tests.py"))
ok("implement-order-normalize")

// check context: jsonl + artifacts but NO plan protocol block (template parity)
const chkArgs = { subagent_type: "trellis-check", prompt: "Active task: .trellis/tasks/t1\nreview" }
await before({ tool: "task", sessionID: "ses_main" }, { args: chkArgs })
check("check-has-artifacts", chkArgs.prompt.includes("=== .trellis/tasks/t1/prd.md (Requirements) ==="))
check("check-no-planproto", !chkArgs.prompt.includes("## Trellis execution plan protocol"))
check("check-finding-handling", chkArgs.prompt.includes("## Finding handling") && chkArgs.prompt.includes("mechanical, small, and determinate"))
ok("check-shape")

// fail-closed: two parallel sessions, dispatch without session or hint
writeFileSync(join(repo, ".trellis/.runtime/sessions/opencode_ses_two.json"), JSON.stringify({ current_task: ".trellis/tasks/t1" }))
const blocked = { subagent_type: "trellis-implement", prompt: "work without binding" }
await before({ tool: "task" }, { args: blocked })
check("blocked-fail-closed", blocked.prompt.startsWith("<!-- trellis-hook-note: context injection blocked -->") && blocked.prompt.includes("work without binding"))
// hint rescues even with two sessions
const rescued = { subagent_type: "trellis-implement", prompt: "Active task: .trellis/tasks/t1\n继续" }
await before({ tool: "task" }, { args: rescued })
check("hint-rescues", rescued.prompt.includes("# Implement Agent Task"))
const outside = { subagent_type: "trellis-implement", prompt: "Active task: C:\\Windows\\not-a-task\n继续" }
await before({ tool: "task" }, { args: outside })
check("outside-workspace-blocked", outside.prompt.includes("context injection blocked"))
ok("fail-closed")
writeFileSync(join(repo, ".trellis/.runtime/sessions/opencode_ses_two.json"), "{}")

// shell bridge powershell + posix + no-double
const winOut = { args: { command: "python ./.trellis/scripts/task.py current" } }
su.injectTrellisContextIntoShell(new mod.TrellisContext(repo), { sessionID: "ses_main" }, winOut, "win32", {})
check("pwsh-prefix", winOut.args.command.startsWith("$env:TRELLIS_CONTEXT_ID = 'opencode_ses_main'; "), winOut.args.command)
const gbOut = { args: { cmd: "task.py current" } }
su.injectTrellisContextIntoShell(new mod.TrellisContext(repo), { sessionID: "ses_main" }, gbOut, "win32", { MSYSTEM: "MINGW64" })
check("gitbash-cmd-field", gbOut.args.cmd.startsWith("export TRELLIS_CONTEXT_ID='opencode_ses_main'; "), gbOut.args.cmd)
const dbl = { args: { command: "export TRELLIS_CONTEXT_ID='keep'; python x.py" } }
check("no-double-inject", su.injectTrellisContextIntoShell(new mod.TrellisContext(repo), { sessionID: "ses_main" }, dbl, "linux", {}) === false)
ok("shell-bridge")

// per-turn workflow-state must come from workflow.md tag blocks (unique fixture bodies)
const wfHooks = await wfPlugin({ directory: repo })
const wfOut = { parts: [{ type: "text", text: "user ask" }] }
await wfHooks["chat.message"]({ sessionID: "ses_main", agent: "build" }, wfOut)
check("wf-body-from-tags", wfOut.parts[0].text.includes("OPENCODE-FIXTURE-INPROG-BODY"))
const wfNoTask = { parts: [{ type: "text", text: "hello" }] }
const repoNoTask = mkdtempSync(join(tmpdir(), "ocnt-"))
mkdirSync(join(repoNoTask, ".trellis"), { recursive: true })
cpSync(join(repo, ".trellis/scripts"), join(repoNoTask, ".trellis/scripts"), { recursive: true })
cpSync(join(repo, ".trellis/workflow.md"), join(repoNoTask, ".trellis/workflow.md"))
const wfHooks2 = await wfPlugin({ directory: repoNoTask })
await wfHooks2["chat.message"]({ sessionID: "ses_x" }, wfNoTask)
check("wf-no-task-tag", wfNoTask.parts[0].text.includes("OPENCODE-FIXTURE-NOTASK-BODY"))
const wfMissing = { parts: [{ type: "text", text: "hi" }] }
const repoBroken = mkdtempSync(join(tmpdir(), "ocbr-"))
mkdirSync(join(repoBroken, ".trellis"), { recursive: true })
writeFileSync(join(repoBroken, ".trellis/workflow.md"), "no tags at all\n")
const wfHooks3 = await wfPlugin({ directory: repoBroken })
await wfHooks3["chat.message"]({ sessionID: "ses_y" }, wfMissing)
check("wf-missing-tag-degrades", wfMissing.parts[0].text.includes("Refer to workflow.md for current step."))
const wfSubTurn = { parts: [{ type: "text", text: "child turn" }] }
await wfHooks["chat.message"]({ sessionID: "ses_main", agent: "trellis-check" }, wfSubTurn)
check("wf-subagent-no-breadcrumb", wfSubTurn.parts[0].text === "child turn")
ok("workflow-state")

// session-start: persistent one-shot + compaction reset
const seen = []
const fakeClient = { session: { messages: async () => ({ data: seen }) } }
const ssHooks = await ssPlugin({ directory: repo, client: fakeClient })
const ssOut = { parts: [{ type: "text", text: "turn one" }] }
await ssHooks["chat.message"]({ sessionID: "ses_s1", agent: "build" }, ssOut)
check("ss-injects", ssOut.parts[0].text.includes("<session-context>") && ssOut.parts[0].metadata.trellis.sessionStart === true)
seen.push({ info: { role: "user" }, parts: [{ type: "text", text: "x", metadata: { trellis: { sessionStart: true } } }] })
ssHooks.event({ event: { type: "session.compacted", properties: { sessionID: "ses_s1" } } })
const ssOut2 = { parts: [{ type: "text", text: "after compact" }] }
await ssHooks["chat.message"]({ sessionID: "ses_s1", agent: "build" }, ssOut2)
check("ss-history-dedup", ssOut2.parts[0].text === "after compact")
ok("session-start")

// normalization parity: the JS plugin's Python bridge output must equal the
// expected values computed by the Python import API (passed in via argv[3]).
const expected = JSON.parse(readFileSync(process.argv[3], "utf-8"))
for (const [idx, sample] of expected.samples.entries()) {
  const jsBridge = su.normalizePromptViaPython(repo, sample, "ctx")
  check(`bridge-strings-${idx}`, typeof jsBridge.normalized_prompt === "string" && jsBridge.policy_marker.length > 0)
  check(`normalize-parity-${idx}`, jsBridge.normalized_prompt === expected.normalized[idx],
        "JS bridge differs from the Python normalize_implement_prompt output")
  check(`contract-parity-${idx}`, jsBridge.execution_contract === expected.contract)
}
check("static-contract-parity", su.STATIC_EXECUTION_CONTRACT === expected.contract && su.STATIC_POLICY_MARKER === expected.marker)
ok("normalization-parity")

// budget notices identical wording
const tiny = new mod.ContextBudget(500)
writeFileSync(join(repo, "bigfile.md"), "字".repeat(100))
const block = mod.materializeFile(repo, "bigfile.md", "why", { max_file_bytes: 10, max_artifact_bytes: 20, max_total_bytes: 40 }, new mod.ContextBudget(500))
check("utf8-truncate-notice", block.includes("[Trellis: truncated at 10 bytes — read bigfile.md for the full content]"), block.slice(-90))
const exhausted = mod.materializeFile(repo, "bigfile.md", "why", { max_file_bytes: 10, max_artifact_bytes: 20, max_total_bytes: 40 }, new mod.ContextBudget(10))
check("budget-index-notice", exhausted.startsWith("[Trellis: not inlined (total context limit reached) — bigfile.md"), exhausted.slice(0, 80))
ok("budget-notices")

console.log(failures === 0 ? "NODE-HARNESS-OK" : `NODE-FAILURES=${failures}`)
process.exit(failures === 0 ? 0 : 1)
"""


@unittest.skipIf(_NODE is None, "node is not available; OpenCode runtime contracts NOT executed")
class OpenCodeRuntimeNodeTests(unittest.TestCase):
    PARITY_SAMPLES = (
        "目标：删除无关 handler。\n验收条件：逐个 grep 全工程验证，每项单独构建。\n验证命令：\nmake test\n执行策略：逐个 grep handler；每项单独构建。",
        "Execution strategy:\nfor each handler, run grep\nrebuild after every small change\nGoal: keep behavior\nAcceptance criteria: tests pass",
    )

    def test_runtime_contracts(self) -> None:
        policy_spec = importlib.util.spec_from_file_location(
            "policy_for_parity",
            TEMPLATE_ROOT / ".trellis" / "scripts" / "common" / "subagent_prompt_policy.py",
        )
        policy = importlib.util.module_from_spec(policy_spec)
        assert policy_spec.loader is not None
        policy_spec.loader.exec_module(policy)
        expected = {
            "samples": list(self.PARITY_SAMPLES),
            "normalized": [policy.normalize_implement_prompt(s, "ctx") for s in self.PARITY_SAMPLES],
            "contract": policy.execution_contract(),
            "marker": policy.policy_marker(),
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
            json.dump(expected, handle, ensure_ascii=False)
            expected_path = handle.name
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as handle:
            handle.write(_JS_RUNTIME_HARNESS)
            script = handle.name
        try:
            result = subprocess.run(
                [
                    _NODE,
                    script,
                    str(TPL_PARENT_FOR_HARNESS),
                    expected_path.replace("\\", "/"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,
            )
        finally:
            os.unlink(script)
            os.unlink(expected_path)
        output = (result.stdout or "") + (result.stderr or "")
        self.assertEqual(result.returncode, 0, f"node harness failed:\n{output}")
        self.assertIn("NODE-HARNESS-OK", output)


if __name__ == "__main__":
    unittest.main()
