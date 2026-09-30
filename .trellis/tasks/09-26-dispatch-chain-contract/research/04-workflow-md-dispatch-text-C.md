# Research: C — 模板 workflow.md 派发粒度文本全景（条目 3）

- **Query**: in_progress 块 / Phase 2.1 及子步骤 / Guardrails / small-patch-sequel 门禁 / round·dispatch 语义位置 + 所有对 workflow.md 断言的模板测试
- **Scope**: internal
- **Date**: 2026-09-26

文件：`templates/embedded-c-overlay/.trellis/workflow.md`，共 **943 行**（`(Get-Content).Count` 实测）。

## 1. 关键区段行号地图

| 区段 | 行号 | 说明 |
|---|---|---|
| WORKFLOW-STATE BREADCRUMB CONTRACT 注释 | 99-142 | 编辑 tag 块前必读：tag 块是每轮 `<workflow-state>` 面包屑唯一真源（102-105）；`[required · once]` 步骤必须在对应 `[workflow-state:*]` 块有 enforcement 行的 INVARIANT（113-118）；编辑清单 135-141；引用的 `.trellis/spec/cli/backend/workflow-state-contract.md` 是上游路径，**模板内不存在**（glob 实测 0 命中） |
| Phase Index → Phase 2 摘要 | 216-219 | 2.1/2.2/2.3 列表 |
| 派发协议总述（tag 块外） | 227-239 | 三平台派发协议、`Active task:` 首行、OpenCode fail-closed |
| **`[workflow-state:in_progress]` 块** | **241-263** | 起 241、止 263。正文：242 Tools 行；243 Flow 行；244 Main-session default（审查 profile 派发 + 子代理自豁免 + “Dispatch is main session only”）；245 Dispatch prompt 首行与读序；**246 Execution plan 行（round 语义核心，见 §2）**；248-262 `### Sub-agent dispatch efficiency contract` 小节（批量派发效率合同） |
| `[workflow-state:in_progress-inline]` 块 | 270-275 | Codex inline 变体；274 行 Execution plan（main session as executor） |
| Rules | 297-303 | 步骤顺序规则 |
| Active Task Routing | 305-347 | 三平台路由（312-315 Claude implement 派发；335-339 OpenCode） |
| **Guardrails** | **349-357** | 357 行：Phase 2 source edits require an approved live execution-plan… “Task state advances only through plan.py … no hook is load-bearing” |
| Loading Step Detail | 359-370 | `get_context.py --mode phase --step <X.X> --platform ...` |
| **Phase 2 gate（small patch / sequel 门禁）** | **600-615** | 600 标题行；604 live/冻结计划布局；605 Round 1；606 两级验证；607 required_checks 不可绕过；608 状态只经 plan.py；609 record 是 attestation、block 审计失败；610 phase 循环 batch-shaped、hook 皆 display-only；**611 Between implement rounds（round 语义核心）**；612 崩溃恢复；613 审计损坏；614 Small patch 硬规则；615 Completion-state exit |
| **`#### 2.1 Implement`** | **617-644** | 619 组合平台标记 `[Claude Code, codex-sub-agent, OpenCode]`；621 “Spawn the implement sub-agent:”；623-625 Agent type / Task description / Dispatch prompt guard；627-632 hook 自动注入清单（632 行“Injects the execution-plan protocol block and the current plan state (round-1 plan creation or the live task loop from the plan gate above)”）；636-644 `[codex-inline]` 变体 |
| `#### 2.1.1` Codex Channel 派发与唯一等待 | 646-688 | `[Codex]` 块 648-688 |
| `#### 2.1.2` Codex 原生子代理派发与静默等待 | 690-724 | `[Codex]` 块 692-724 |
| `#### 2.2 Quality check` | 726-835 | 审查轮次语义（见 §2） |
| Phase 3.4 commit preamble | 867-871 | 871 行 Review-profile preamble |

## 2. 全部 round / re-dispatch / between rounds / dispatch 粒度语义位置

（`Select-String 'round|Round|dispatch|Dispatch|re-dispatch|between rounds'` 实测过滤后与“派发粒度”相关的条目）

| 行号 | 原文要点 | 语义类别 |
|---|---|---|
| 244 | “Main-session default: dispatch the implement sub-agent. … reinforced … re-dispatches a fresh agent after each blocking-fix round …” | **审查轮**（round = 一次 check 派发），非 implement 轮 |
| **246** | “Execution plan: the implement sub-agent creates/approves the live … **between rounds run `python .trellis/scripts/plan.py --task "<task-path>" status` to decide re-dispatch vs 2.2**. … The `<execution-plan>` breadcrumb is display-only.” | **implement 轮现状定义**：轮间由主会话跑 status 决定 re-dispatch；未定义一轮内部应走多少 phase（改动 C 的落点） |
| 272 | inline 块审查 profile 同款 “re-dispatches … after each blocking-fix round” | 审查轮 |
| **605** | “**Round 1**: the implementer reads PRD/Spec/code and writes the plan first …” | implement 轮：Round 1 = 建计划轮 |
| **611** | “**Between implement rounds** the main session runs `plan.py --task "<task-path>" status`: runnable tasks → **re-dispatch** (or continue inline); all completed → 2.2 quality check; blocked or plan_revised history → review the reason before proceeding.” | implement 轮：轮间判定表（与 246 行同源；改动 C 需同时覆盖两处，且注意用户已排除“返回后 gate”，611 行的现状描述保留与否属实施决策） |
| 621-625 | “Spawn the implement sub-agent” + Dispatch prompt guard | 单次派发动作本身 |
| 632 | hook 注入 “round-1 plan creation or the live task loop” | 轮语义引用 protocol block |
| 756-767 | reinforced/comprehensive 审查 “new full affected-scope round / Every re-review round uses a newly dispatched agent” | 审查轮 |
| 773-774 | “Blocking findings from any round are triaged in batches. Fix ownership … never schedules a review round” | 审查轮 |
| 790-795 | 2.2 末尾 “dispatch a new Implement Agent … independent round” | 修复轮 |
| 824-829 | Codex inline 各 profile 的 round 措辞 | 审查轮 |
| 835 | Final pass 各 profile round 汇总 | 审查轮 |
| 871 | 3.4 preamble “no extra commit-ready review round … after any blocking-fix round” | 审查轮 |

另：`execution_plan.py:2101`（protocol block Round 1 标题）、`.trellis/agents/implement.md:66`、
`.claude/agents/trellis-implement.md:53`、`.opencode/agents/trellis-implement.md:64`、
`.codex/agents/trellis-implement.toml:29` 均有 “Round 1 — plan generation” 同构条目（属 D 项文件）。

## 3. 所有对 workflow.md 文本做断言的模板测试（逐条）

### 3.1 `test_small_patch_and_sequel_contract.py`（normalized = 全文 `\s+`→单空格后 assertIn）

| 行号 | 断言 | 冲突面 |
|---|---|---|
| 104-121 | `test_workflow_carries_small_patch_hard_rules`：assertIn `Small patch (hard rule, bypasses plan.py)`、`when the user explicitly says this is a small patch (\`小修\`) or says not to go through \`plan.py\``、`no \`revise\`, no new phase, no new task`、`Blocking fixes from review or implementation default to a small patch`、`only blocking work that is too much, messy, and complex enough to need new steps/checks/report justifies a \`sequel\`` | 锁 614 行措辞；C 项新句子避开这些原文即可 |
| 123-133 | `test_workflow_carries_completion_state_exit`：assertIn `Completion-state exit`、`a small patch touches no execution-plan file at all`、`freezes the old plan with \`plan.py sequel --reason "..."\``、`\`revise\` never creates a sequel and can never rewrite a completed report phase into a normal phase`、`opens a new Trellis task` | 锁 615 行 |
| 135-145 | `test_workflow_gate_routes_by_plan_state_not_revise`：assertIn `Phase 2 source edits require an approved live`、`while the live plan is open`、`follow the small-patch /\`sequel\` exit instead of \`revise\``；**assertNotIn** 旧句 `Phase 2 source edits require an approved \`<task>/execution-plan.json\`;` | 锁 Guardrails 357 行；**新增句子不得复活被 assertNotIn 的旧措辞** |

### 3.2 `test_review_profile_contract.py`

| 行号 | 断言（对 workflow.md） | 冲突面 |
|---|---|---|
| 141-147 | assertIn `light\|standard\|reinforced\|comprehensive\|strict`（canonical pipe 串） | 356 行已有；新增文本勿引入其它五级连写变体 |
| 165-171 | assertIn `` `reinforced`: dispatch an independent affected-scope `` | 锁 756 行开头 |
| 173-178 | assertIn `comprehensive` | 宽 |
| 182-189 | assertIn ``strict` additionally requires``、`fresh independent full-scope commit-ready final review` | 锁 871 行 |
| 193-209 | `_section(workflow, "**Review-profile preamble**: before drafting commits,")` 内 assertIn `require no extra commit-ready review round`；**assertEqual preamble.count("commit-ready final review") == 1**（205-208 行） | 3.4 preamble 段内该短语只能出现一次；C 项文本不要写进 871 行所在 section |
| 211-212 | assertIn `otherwise default to \`standard\`` | 锁 356 行 |
| 237-243 | assertIn `invalidate prior evidence`、`re-trigger the current profile's review` | 锁 829/835 行 |
| 269-278 | assertNotIn STALE_ENUMERATIONS（96-105 行定义：`light\|standard\|strict`、`standard/strict` 等 8 种三级旧写法） | 新增句子勿用这些组合 |

### 3.3 `test_codex_native_wait_contract.py`（经真实 CLI `get_context.py --mode phase` 取步骤正文）

| 行号 | 断言 | 冲突面 |
|---|---|---|
| 99-103 | `--step 2.1 --platform codex` 输出含 `write_stdin`、`yield_time_ms=300000` | 2.1 步骤抽取必须继续并入 2.1.1/2.1.2 子步骤 |
| 105-108 | `--step 2.1`（无平台）含 `write_stdin` | 同上 |
| 110-114 | `--step 2.1.1` 含 `write_stdin`、**assertNotIn `#### 2.2`** | 子步骤边界 |
| 116-120 | `--step 2.2` 不含 `write_stdin`、不含 `#### 2.1.1` | 子步骤不得漏进 2.2 |
| 129-133 | `--step 2.1 --platform claude` 含 **`Spawn the implement sub-agent`** 与 `trellis-implement` | **C 项改写 2.1 时必须保留 621 行原句** |
| 135-140 | 三平台（claude-code/codex/opencode）`--step 2.1` 均含 `Spawn the implement sub-agent` | 同上；新增内容须放在组合标记块内或平台无关位置 |
| 229-238 | `### Loading Step Detail` 段含三个 `--platform` 旗标 | 锁 359-370 行 |
| 248-254 | `--step 2.1.2` 含 STEP_2_1_2_TITLE（37 行冻结标题 `#### 2.1.2 Codex 主会话：原生子代理派发与静默等待`）与 NATIVE_WAIT_TERMS 17 个冻结词（40-58 行） | 勿动 2.1.2 标题与词表 |
| 256-262 | `--step 2.1`（含/不含平台）同时含 `write_stdin` 与 `wait_agent` | — |
| 264-267 | `--step 2.1.1` 不含 `wait_agent` | 2.1.1/2.1.2 边界 |
| 269-288 | claude 系平台 `--step 2.1`/`2.1.2` 输出不含 CODEX_ONLY_TERMS（61-68 行：`exec_command`、`write_stdin`、`yield_time_ms`、`session_id`、`wait_agent`、`spawn_agent`）及三个冻结短语（287 行） | **C 项若在 2.1 组合块新增文字，严禁出现这 6 个 Codex 终端术语**（组合块 `[Claude Code, codex-sub-agent, OpenCode]` 对 claude 平台可见） |
| 290-304 | 全文 assertNotIn `"timeout_ms":30000`；2.1.2 标题后必须紧跟 `[Codex]` 包裹（295-302 行正则） | 勿在 2.1.2 标题与 `[Codex]` 之间插入内容 |
| 306-309 | TEMPLATE-CONTENTS.md 含两个测试文件名 | 见基线文件 |

### 3.4 `test_trellis_channel_contract.py`

| 行号 | 断言（对 workflow.md） | 冲突面 |
|---|---|---|
| 102-116 | CODEX_TERMS（32 行：`exec_command`、`write_stdin`、`yield_time_ms`、`session_id`）必须出现在全文且只出现在 `[Codex]` tag 块内；**assertNotIn 于 `[Claude Code]` 与 `[Claude Code, codex-sub-agent]` 块**（109-116 行） | 新句子避免这 4 词；注意 619 行组合标记是 `[Claude Code, codex-sub-agent, OpenCode]`，不在 109-111 行采集的两类块名内，但保守起见同样避免 |
| 118-122 | `[Codex]` 块含 `复用同一 ID`、`只对该 ID 调用 \`write_stdin\`` | 锁 2.1.1 正文（664-665 行） |
| 124-138 | `[Codex]` 块含 `yield_time_ms=300000`、`单次读取窗口`、`不是 Channel CLI \`--timeout\``、`总等待上限`；正则禁止 `yield_time_ms=30000(?!0)`；`[Claude Code]` 块不得含 `yield_time_ms=300000` | 锁 657-658、665-668 行 |

### 3.5 `test_review_fix_ownership_contract.py`（已实测展开常量区）

- 48 行 `WORKFLOW = TEMPLATE_ROOT/".trellis/workflow.md"`；64-74 行 `MANAGED_FILES` 把 workflow.md、
  review Skill、四份 check 代理、**OpenCode 插件与 Claude/Codex 两份 inject-subagent-context.py hook**
  全部纳管。
- 78-93 行 canonical anchors（必须在纳管文件中存在）：`mechanical, small, and determinate`、
  `reliably resume the original Implement Agent`、`dispatch a new Implement Agent`、`Codex inline`、
  REPORT_ONLY 两种拼写、`never schedules a review round`。
- 95-106 行 **FORBIDDEN 短语（不得出现在任何纳管文件，含 workflow.md 与两份 hook/plugin）**：
  `Fix issues yourself`、`Never resume an agent that already exited`、`do not resume an exited agent`、
  `fresh implementation pass`、`fresh implement agent`、`dispatch a fresh Check Agent`、
  `an extra review round`、`channel spawn`。
- 对 workflow 的断言：176 行 `test_workflow_carries_matching_routing`、211 行
  `test_managed_entries_free_of_old_policy_phrases`、227 行 `test_fix_ownership_never_schedules_review_rounds`。
- **C/D 项冲突面**：向 workflow.md、两份 Python hook、OpenCode 插件新增句子时，严禁使用上面 8 个 FORBIDDEN
  短语（例如新报告义务文案里写 “an extra review round” 或 “fresh implement agent” 会直接红）；
  同时不得删除/改写 anchors（workflow.md 790 行现有 “dispatch a new Implement Agent”）。

### 3.6 `test_opencode_platform_contract.py`

- 321 行 Node harness 用**自建 fixture workflow.md**（`OPENCODE-FIXTURE-INPROG-BODY`）验证插件从 tag 块取正文，
  不读模板真身 → 改模板 in_progress 块不影响该 harness。
- 391/399/406/409 行断言均针对 fixture。

## 4. C 项落点与冲突面小结

- 落点 1：`[workflow-state:in_progress]` 块（241-263），尤其 246 行 Execution plan 行；块内新增行不受任何逐字断言约束（现有测试只以 normalized assertIn 锁 614/615/357 行等短语），但按 99-142 行 BREADCRUMB CONTRACT 的 INVARIANT，`[required · once]` 类义务须在此块有对应 enforcement 行。
- 落点 2：Phase 2 gate 611 行（Between implement rounds）与 2.1（617-634）。2.1 内新增文字必须：保留 `Spawn the implement sub-agent`（129-140 行断言）、不出现 CODEX_ONLY_TERMS（269-288 行）、不破坏 `[平台标记]` 块配对（get_context 抽取按 619/634 行标记切块）。
- 状态所有权句（“主会话不得代跑 start/record/done”）现状：workflow.md 现有最接近表述是 357 行“Task state advances only through plan.py”与 246 行“the implement sub-agent creates/approves … advances only through plan.py”，**没有**明文禁止主会话代跑；新增该句为纯新增。
- 用户已排除“返回后 gate（git diff + check_recorded 验收关卡）”——本调研未将其纳入任何落点建议。
