# Research: A — execution_contract() 全链路（条目 1）

- **Query**: execution_contract 当前文本、三平台消费点、注入位置与触发事件、锁定其文本/parity 的测试断言
- **Scope**: internal
- **Date**: 2026-09-26

以下所有路径均相对 `templates/embedded-c-overlay/`，行号为实测。

## 1. 函数当前完整文本

`.trellis/scripts/common/subagent_prompt_policy.py:194-203`：

```python
def execution_contract() -> str:
    """Return the shared runtime contract for implementer dispatch."""
    return (
        "Preserve task scope, acceptance criteria, and required validation commands. "
        "Treat per-item wording as report granularity, not one tool call per item. "
        "Batch independent reads and searches; perform targeted follow-up only when "
        "a batch result proves it is needed. Do not rebuild for comment or historical "
        "documentation matches. After a real code fix, rerun only affected checks "
        "and stop when scope, evidence, verification, and report are complete."
    )
```

同文件相关锚点：
- `_POLICY_MARKER = "[Trellis dispatch policy normalized]"`（28 行）；`policy_marker()`（189-191 行）。
- `--json` bridge 输出三键 `{"normalized_prompt", "execution_contract", "policy_marker"}`（209-213 注释、247-252 实现）；OpenCode 插件靠该 bridge 复用同一 Python 文本。

## 2. 三平台消费点（文件:行号 + 触发事件）

### Claude Code — `.claude/hooks/inject-subagent-context.py`

- 导入：38 行 `from subagent_prompt_policy import execution_contract, normalize_implement_prompt`。
- 消费点 1：`build_implement_prompt()`（628-662 行），646 行把 `{execution_contract()}` 嵌入
  `## Trellis execution contract (applies to the task below)` 小节（644 行标题），位于
  `## Your Context`（注入上下文）之后、`## Task requirements (normalized from the dispatch request)`（648 行）之前。
- 触发事件：**PreToolUse**（matcher `Task` 与 `Agent`），注册于 `.claude/settings.json:38-58`；
  main() 在 1177-1180 行对 `trellis-implement` 调 `build_implement_prompt`，
  以 `hookSpecificOutput.updatedInput.prompt` 整体重写派发 prompt（1204-1228 行）。
- 该文件同时兼容 Codex/Cursor/ZCode/Gemini 等事件形态（`_parse_hook_input`，1076-1116 行）。

### Codex — `.codex/hooks/inject-subagent-context.py`

- 导入：38 行（同上）。
- 消费点 1：`build_implement_prompt()` 646 行（与 Claude 副本同构；两副本 contract 段由测试断言逐字相等，见 §3）。
- 消费点 2：**SubagentStart 原生事件、无原始 prompt 时的 fallback**——999 行，
  `_handle_codex_subagent_start()`（941-1008 行）在 992-1000 行拼接
  `## Native dispatch fallback` + `## Trellis execution contract (applies to this task)` + `execution_contract()`。
- 消费点 3：**SubagentStart 异常兜底**——main() 1143-1151 行，异常时输出
  `## Trellis execution contract (fallback)` + `execution_contract()`（1148 行）。
- 触发事件注册：`.codex/hooks.json:14-25`，SubagentStart matcher
  `^(?:trellis-implement|trellis-check|trellis-research)$`；PreToolUse 路径与 Claude 副本共用同一 main()（1154-1229 行）。

### OpenCode — `.opencode/plugins/inject-subagent-context.js` + `.opencode/lib/session-utils.js`

- 插件导入：`inject-subagent-context.js:47-52`（`normalizePromptViaPython`、`planProtocolBlock`、`STATIC_EXECUTION_CONTRACT`）。
- 触发事件：插件钩子 **`tool.execute.before`**（433 行注册；493 行对 implement 调 `buildImplementPrompt`）。
- 正常路径：`buildImplementPrompt()`（172-223 行）→ 176-178 行经
  `normalizePromptViaPython`（session-utils.js:782-806，子进程调用
  `.trellis/scripts/common/subagent_prompt_policy.py --json`）取回 `bridge.execution_contract`，
  204-206 行渲染进 `## Trellis execution contract (applies to the task below)` 小节。
- 降级路径：bridge 抛错时 183-188 行改用 `STATIC_EXECUTION_CONTRACT` 并附
  `prompt normalization degraded` 显式说明。
- 静态兜底常量：`session-utils.js:821-827` `export const STATIC_EXECUTION_CONTRACT = "Preserve task scope, ... report are complete."`
  ——**与 Python 文本逐字节相同**；811-816 行注释明确“MUST stay byte-identical with
  subagent_prompt_policy.py (execution_contract()/policy_marker()); the platform contract test asserts equality”。
  `STATIC_POLICY_MARKER` 在 819 行。

### 注入位置小结（子代理最终 prompt 中的顺序）

三平台一致：`<!-- trellis-hook-injected -->` → `# Implement Agent Task` → `## Your Context`
（jsonl → prd → design → implement.md → **plan_protocol_block**）→ `## Trellis execution contract` →
`## Task requirements (normalized...)` → `## Important Constraints`
（Claude 版 631-662 行；OpenCode 版 191-222 行；Codex SubagentStart 走 additionalContext 同构文本）。

## 3. 锁定文本 / parity 的测试断言（决定改文本的破坏面）

### `.trellis/scripts/tests/test_subagent_prompt_contract.py`

| 行号 | 断言形态 | 内容 | 改 execution_contract() 文本的影响 |
|---|---|---|---|
| 158-163 | `assertEqual(contract_sections[0], contract_sections[1])` | Claude hook 与 Codex hook 的 `build_implement_prompt` 中 `## Trellis execution contract (applies to the task below)\n` 与 `## Task requirements (normalized from the dispatch request)` 之间正文逐字相等 | 两 hook 副本同引一个 Python 函数 → 天然满足；若只在单侧 hardcode 新文本会失败 |
| 203 | `assertIn("Trellis execution contract", prompt)` | Claude PreToolUse 重写后的 prompt 含小节标题 | 只锁标题串，不锁正文 |
| 215 | `assertIn("Trellis execution contract", prompt)` | Codex PreToolUse 同上 | 同上 |
| 252 | `assertIn("Trellis execution contract", additional)` | Codex SubagentStart（有 prompt）同上 | 同上 |
| 263-265 | `assertIn("Native dispatch fallback", ...)`、`assertIn("not a mandatory execution order", ...)`、`assertIn("Trellis execution contract", ...)` | Codex SubagentStart 无 prompt 的 fallback | 锁 fallback 引导语，不锁 contract 正文 |
| 284 | `assertIn("Trellis execution contract", payload[...]["additionalContext"])` | Codex SubagentStart 异常兜底 | 同上 |
| 339 | `assertEqual(data["execution_contract"], policy.execution_contract())` | `--json` bridge 输出与 import API 相等 | 动态 parity，改文本自动跟随 |
| 377-379 | 正则 `r'export const STATIC_POLICY_MARKER = "(.*)"'` + `assertEqual` | marker 与 JS 常量相等 | 与 contract 无关 |
| 380-386 | 正则 `r"export const STATIC_EXECUTION_CONTRACT =\n((?:[ \t]+.*\n?)+)"` 抽取 JS 多行字符串拼接后 `assertEqual(policy.execution_contract(), js_contract)` | **Python 文本 ↔ session-utils.js 静态常量逐字相等** | **改 Python 文本必须同步改 session-utils.js:821-827，否则此断言失败** |
| 388-397 | `assertIn("normalizePromptViaPython", plugin)` 等 5 条 | 插件保留 bridge 调用与降级说明文案 | 不锁 contract 正文 |

### `.trellis/scripts/tests/test_opencode_platform_contract.py`（Node harness）

| 行号 | 断言形态 | 内容 |
|---|---|---|
| 428-435 | JS `check(\`contract-parity-${idx}\`, jsBridge.execution_contract === expected.contract)` | bridge 返回的 contract 必须等于 Python 端 `policy.execution_contract()`（expected 在 468-473 行由 Python 生成） |
| 436 | JS `check("static-contract-parity", su.STATIC_EXECUTION_CONTRACT === expected.contract && su.STATIC_POLICY_MARKER === expected.marker)` | **JS 静态常量 ↔ Python 文本逐字相等**（第二处 parity 锁） |
| 460-499 | `test_runtime_contracts`：node 缺失时 skip（453 行 `@unittest.skipIf(_NODE is None, ...)`）；成功判据 `NODE-HARNESS-OK`（499 行） | 上述 JS 检查的执行载体 |

### 结论（改动破坏面）

- **没有任何测试把 execution_contract 的具体句子写成冻结字面量**（tests 目录 grep `Preserve task scope|Batch independent reads` 零命中）。
- 全部是**动态 parity**：Python 函数 ↔ `--json` bridge ↔ JS `STATIC_EXECUTION_CONTRACT` 三方相等。
- 因此改 A 的最小同步集合是两处文本：
  1. `subagent_prompt_policy.py:194-203`（唯一真源）；
  2. `.opencode/lib/session-utils.js:821-827`（静态兜底，逐字节镜像）。
  改完后 `test_subagent_prompt_contract.py:380-386` 与 `test_opencode_platform_contract.py:436`（node 可用时）自动验证。
- 三个 hook/plugin 都通过函数或 bridge 取值，无需改 hook 正文。

## Caveats / 未确认

- `_NODE` 可用性：harness 依赖本机 node（test_opencode_platform_contract.py:453 skipIf）。本次实跑输出为纯 `OK`（无 `OK (skipped=N)` 字样），unittest 只在存在 skip 时才追加该标记，故本机 node 可用、Node parity 检查已实际执行。
- OpenCode 插件在 bridge 降级时把 `STATIC_EXECUTION_CONTRACT` 同时拼进 normalized 正文（186 行）与 contract 变量（187 行），即降级 prompt 中该文本出现两次；新增句子会同样出现两次，属既有行为。
