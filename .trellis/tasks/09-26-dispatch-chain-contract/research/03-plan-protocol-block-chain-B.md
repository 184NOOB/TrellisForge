# Research: B — plan_protocol_block() 全链路（条目 2）

- **Query**: plan_protocol_block 完整文本结构、各平台调用事件、测试锁定、与 live plan / sequel / 冻结目录语义的交互
- **Scope**: internal
- **Date**: 2026-09-26

路径均相对 `templates/embedded-c-overlay/`，行号实测。

## 1. 函数结构（`.trellis/scripts/common/execution_plan.py:2048-2179`）

`plan_protocol_block(repo_root, task_dir) -> str`，docstring（2049-2054 行）自述：
“Works for every platform that consumes it (Claude PreToolUse rewrite, Codex SubagentStart,
inline main sessions via workflow.md): the protocol text is plain markdown around shared status output.”

固定骨架：

| 区段 | 行号 | 内容要点 |
|---|---|---|
| head | 2056 | `## Trellis execution plan protocol\n`（OpenCode harness 用该串做排序探针，见 §3） |
| state_line | 2064-2079 | live_number>1 时列出 `Live plan N files:` + “task-root execution-plan.json 只是 live pointer、其余 plans/<n>/ 是 frozen read-only history”；否则 `State files:` 两文件 |
| base | 2080-2095 | ① “plan.py is the ONLY sanctioned state advancer; never hand-edit task statuses”（2082）；② 命令行清单 `(validate/status/start/record/done/block/revise/sequel)`（2083-2084）；③ 两级验证 minimal/report 定义（2085-2087）；④ Small patch 硬规则四门禁（2088-2094） |
| 分支 1：无计划 | 2097-2110 | `**Round 1 — plan generation (MANDATORY before any source edit):**` + template/validate 三步 |
| 分支 2：计划未批准 | 2111-2118 | `Plan exists but is '<status>'. Finish edits, then run validate...` |
| 分支 3：计划全完成 | 2119-2147 | small patch / `sequel --reason` / 新任务三出口 + `revise` 语义 + 末尾 `format_status(..., verbose=True)`（2145） |
| 分支 4：进行中（正常派发路径） | 2148-2175 | `Approved at revision N. Current in_progress: ...; next runnable: ...`（2151-2152）→ **`Per phase loop: start → batch read/edit/check → record → done`（2153-2157）** → terminal report phase 义务（2158-2161）→ fail 永久、`block <id> --reason` → `revise` → edit → `validate` 恢复链（2162-2165）→ 小修留在当前 phase（2166-2169）→ `record --result pass` 是 attestation、独立验证归 Phase 2.2（2170-2171）→ 末尾 `format_status(verbose=True)`（2173） |
| 异常 | 2176-2179 | PlanError → head+base+错误说明；其他 Exception → 返回空串 |

**与改动方向 B 直接相关的现状**：分支 4 现有文本只描述“Per phase loop”（单 phase 循环）与 fail→block 恢复链；
没有任何“单次派发必须连续走完整条 phase 链 / 不得单 phase 返回 / 静默空返回属协议违规 / 唯一合法提前返回条件”的表述
（全模板关键词扫描见 `08-duplication-scan.md`）。

## 2. 调用点与触发事件（三平台）

| 平台 | 调用文件:行号 | 触发事件 |
|---|---|---|
| Claude | `.claude/hooks/inject-subagent-context.py:39`（import）、`562`（`get_implement_context` 第 5 步调用，561-566 行 try/except 吞异常） | **PreToolUse**（matcher Task/Agent，`.claude/settings.json:38-58`），随 `build_implement_prompt` 的 `## Your Context` 注入 |
| Codex | `.codex/hooks/inject-subagent-context.py:39`、`562`（同构副本） | **SubagentStart**（`.codex/hooks.json:14-25`，`_handle_codex_subagent_start` 975 行取 `get_implement_context`）；同文件 PreToolUse 兼容路径同样生效 |
| OpenCode | `.opencode/lib/session-utils.js:549-554`（`PLAN_PROTOCOL_PY` 内嵌 Python 片段直接 `from common.execution_plan import plan_protocol_block`）、`584-588`（`planProtocolBlock()`，经 `runPythonFragment` 556-574 行子进程执行，8s 超时，失败返回空串） | 插件 `tool.execute.before`：`.opencode/plugins/inject-subagent-context.js:105`（`getImplementContext` 第 5 步） |
| inline 主会话 | 不经 hook；workflow.md 文本引用同一协议（`.trellis/workflow.md:246`、600-615 行 Phase 2 gate），docstring 2051-2053 行明示该用途 | — |

check/research 上下文**不**注入 protocol block：`get_check_context`（Claude hook 571-616 行）无第 5 步；
OpenCode harness 显式断言 `check-no-planproto`（见 §3）。

## 3. 锁定 protocol block 文本的测试

### `.trellis/scripts/tests/test_execution_plan.py`

| 行号 | 断言 | 内容 |
|---|---|---|
| 980-988 | `test_protocol_block_offers_small_patch_and_sequel_when_complete` | 计划全完成分支：assertIn `fully completed` / `Small patch (hard rule)` / `touch any execution-plan file` / `sequel --reason` / `new Trellis task`；**assertNotIn `Per phase loop`（988 行）**——完成分支不得出现进行中循环文案 |
| 1104-1116 | `test_status_and_protocol_show_only_the_live_plan` | sequel 后：protocol assertIn `Live plan 2 files:`（1114）/ `live pointer`（1115）/ `frozen read-only history`（1116） |

### `.trellis/scripts/tests/test_opencode_platform_contract.py`（Node harness）

| 行号 | 断言 | 内容 |
|---|---|---|
| 342-348 | `order` 探针数组最后一项 `"## Trellis execution plan protocol"`，逐一 `indexOf` 递增 | implement prompt 中 protocol block 必须排在 jsonl/prd/design/implement.md 之后（head 串被锁定） |
| 357 | `check("check-no-planproto", !chkArgs.prompt.includes("## Trellis execution plan protocol"))` | check 派发不得含 protocol block |

### 其它

- `test_subagent_prompt_contract.py` 不直接断言 protocol 文本（只断言 contract 小节与 normalization）。
- `test_small_patch_and_sequel_contract.py:147-158` 锁的是四份 implement 代理定义文件里的同类措辞（见 `05-implement-agents-D.md`），不是 protocol block 本体。

**结论**：进行分支（2148-2175 行）正文没有逐字冻结断言；现有断言只锁
① head 标题串、② 完成分支的五个短语 + “不得出现 Per phase loop”、③ sequel 状态行三短语。
在完成分支之外的“进行中”分支追加句子属低冲突面；但若新句子含 `Per phase loop` 字样并出现在完成分支会撞 988 行 assertNotIn。

## 4. 与 live plan / sequel / 冻结目录语义的交互点

- `resolve_live_plan(task_dir)`：`execution_plan.py:223-313`。两种合法布局（legacy 单文件 → `(1, task_dir)`；
  sequel pointer `{"schema":3,"live":N}` → `(N, task_dir/plans/N)`），一切歧义（pointer 缺失/嵌套/混入 tasks、
  root 全量计划与 plans/ 并存）抛 `PlanError` fail-closed。protocol block 在 2060-2063 行先行调用它，
  PlanError 时返回 `Plan state error: ...`（2063、2176-2177 行）。
- `cmd_sequel`：`execution_plan.py:1173-1333`。冻结旧计划到 `plans/<n>/`、写 `plan_sequel` 事件
  （测试锁定 `test_execution_plan.py:1020-1022`）、新 live plan 为 proposed；
  “live plan is now 2” 输出被 `994、1051、1087` 行断言；开放 phase 时拒绝（1054-1060 行，`open phase`）、
  无 terminal report 时拒绝（1062-1071 行，`terminal report`）。
- `plan_path`/`events_path`（316-322 行）都经 `resolve_live_plan` 解析；`_frozen_plan_summaries`（1856-1881 行）
  给 `format_status` 提供 `frozen plans:` 行；`is_plan_history_dir`（344 行）+ `_require_live_task_dir`（349 行）
  拒绝在冻结目录上做任何 mutation（测试 1118-1134 行）。
- 交互含义：B 项新文本若引用“当前 phase 链”，其状态来源必须继续走 `compute_status`/`resolve_live_plan`，
  protocol block 本身在 2119 行已调用 `compute_status(plan)`，可直接复用该局部变量。

## Caveats

- `get_implement_context` 的 protocol block 注入受上下文预算 `_Budget` 影响吗？——不受：561-566 行直接 append，
  不经 `_budgeted_block`；但整体 prompt 仍可能被平台截断（Codex 有 `Full hook output saved to:` 机制，
  `.codex/agents/trellis-implement.toml:21`）。
- OpenCode bridge 失败静默返回空串（session-utils.js:570-573），此时子代理 prompt 无 protocol block，
  依赖代理定义文件自带协议正文兜底（插件 107-109 行注释明说）。
