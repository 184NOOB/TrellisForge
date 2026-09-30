# 技术设计：模板单次派发走完执行计划链合同

任务：`09-26-dispatch-chain-contract`（父任务 `09-17-trellisforge-1-3-upgrade`）。
证据锚点全部来自 `research/01`–`research/08`（2026-09-26 实测，行号以当时模板状态为准；漂移时用本文件引用的内容锚点重定位）。

## 1. 问题与设计目标

模板把"phase 循环"写清楚了，却从未定义"一次派发覆盖多少 phase"，也从未规定"做不下去怎么收场"：

- `execution_contract()`（三平台共享派发合同）只讲批处理效率 → 子代理没有链遍历义务、没有失败上报义务（`research/02`）。
- `plan_protocol_block()` 进行分支只有 `Per phase loop: start → … → done`，循环主体是"一个 phase" → 语义上允许做完一格就停（`research/03`）。
- `workflow.md:246` 与 `611` 用 "between rounds" / "Between implement rounds" 但全模板无 round 粒度定义 → 主会话自然取"一个 phase = 一轮"（`research/04`）。
- 四份 implement 代理定义的 "Stop on completion" 未定义 completion → 单 phase 完成即可自认"complete"（`research/05`）。
- `format_status()` 只输出 `next runnable`（`sorted()` 字典序、单格视野）→ 工具输出本身在诱导逐格派发（`research/06:31,126`）。

设计目标：**文本层（A/B/C/D）给出唯一口径的链遍历义务与失败契约，工具层（E）让每轮状态输出直接显示本轮链**，两侧互相印证；不新增任何 gate、不新增 CLI 表面积、不改状态机语义。

## 2. 边界与所有权

| 层 | 文件 | 所有权 | 本次改动 |
|---|---|---|---|
| A 派发合同文本 | `templates/embedded-c-overlay/.trellis/scripts/common/subagent_prompt_policy.py::execution_contract()` | 三平台唯一文本源（Claude/Codex hook import 取值；OpenCode 经 `--json` bridge） | 追加链遍历义务 + 失败契约 |
| A' JS 常量副本 | `templates/embedded-c-overlay/.opencode/lib/session-utils.js:821-827 STATIC_EXECUTION_CONTRACT` | OpenCode 桥接失败时的静态兜底，必须与 Python 逐字相等 | 同步同一文本 |
| B 协议块 | `.trellis/scripts/common/execution_plan.py::plan_protocol_block()` **仅进行分支（2148-2175）** | 子代理 prompt 的执行计划协议 | 追加同义义务 |
| C 主会话面包屑/步骤 | `.trellis/workflow.md` `[workflow-state:in_progress]`（241-263，重点 246 行）+ Phase 2 gate 611 行 + `#### 2.1`（617-634） | 主会话每轮注入与步骤详情 | 定义 round、禁止逐格派发、状态所有权归子代理 |
| D 代理定义 | `.claude/agents/trellis-implement.md`(39-107/109-125/178-198)、`.opencode/agents/trellis-implement.md`(50-120/122-138/191-211)、`.codex/agents/trellis-implement.toml`(27-35/37-51/53-56)、`.trellis/agents/implement.md`(56-112/121-138/176-196) | 四份同族文本，被共享短语断言并列锁定 | 各按自身形态落位同一合同 |
| E 状态输出 | `.trellis/scripts/common/execution_plan.py::format_status()`（1919-1924 区、verbose 分支之外）+ 新辅助函数 | `plan.py status` CLI 与三平台 `<execution-plan>` 面包屑共用 | 新增 `dispatch chain:` 行 |
| 测试 | 新建 `.trellis/scripts/tests/test_dispatch_chain_contract.py`（A–E 断言集中一处）+ `TEMPLATE-CONTENTS.md` 登记一行；既有 4 个测试文件零改动 | 模板套件 | 锁定 A–E 并防漂移 |
| Spec | 根 `.trellis/spec/main/tooling/python.md` 新增一个 Scenario（用户授权的唯一定点例外） | 执行计划合同的 spec 所有者 | Phase 3.3 收敛 |

**不改**：`plan.py` 状态机与子命令集合、`compute_status` 现有字段与 `next runnable` 行、`[workflow-state:in_progress-inline]`（270-275）、三平台 hook/plugin 代码、`plan-pretool-reminder.py`、审查侧合同、根目录任何运行时实现。

## 3. 合同文本（唯一口径）

### 3.1 A / A'：`execution_contract()` 追加段（Python 与 JS 常量逐字相同）

在既有批处理效率文本之后追加（保持既有句子不删不改）：

```text
One dispatch owns the whole remaining plan chain: after a phase reaches done, start the next runnable phase and continue (start -> edit inside that phase's scope.write -> run declared checks -> record -> done) until the terminal report phase is done. Never return to the main session after a single phase. If you cannot continue, run plan.py block <id> --reason "..." and return a structured failure report; a silent empty return is a protocol violation. The only other legitimate early return is context-budget exhaustion: record/done the current phase first, then return listing the remaining runnable phases.
```

设计要点：
- 用 ASCII `->` 而非 `→`：该串会进 OpenCode 静态常量、hook 注入与下游终端，ASCII 免除编码面风险（`plan.py` 自身已在 Windows reconfigure stdout，但下游 hook 环境不可控）。
- 明确"两种且仅两种合法提前返回"：`block`（真受阻）与预算耗尽（先收尾当前 phase 再报告剩余 runnable）。预算耗尽不得用 `block`，因为它不是受阻，误用会污染计划语义并触发 `revise` 流程。
- 措辞刻意避开 `test_review_fix_ownership_contract.py:95-106` 的 8 个 FORBIDDEN 短语（`Fix issues yourself`、`Never resume an agent that already exited`、`do not resume an exited agent`、`fresh implementation pass`、`fresh implement agent`、`dispatch a fresh Check Agent`、`an extra review round`、`channel spawn`），也避开字符串 `Per phase loop`（`test_execution_plan.py:988` 的 `assertNotIn` 只约束完成分支，但全局避开可消除落位漂移风险）。

### 3.2 B：`plan_protocol_block()` 进行分支（2148-2175）追加

在 `Per phase loop: …`（2153-2157）之后、terminal report phase 义务（2158-2161）之前插入与 3.1 同义的一段（可复用同一措辞，避免出现第二套口径）：

```text
- Chain duty: one execution round covers the whole remaining chain, not one phase. After each `done`, continue with the next runnable phase until the terminal report phase is done. A dispatched sub-agent must not return to the main session after a single phase; return early only via `block <id> --reason "..."` plus a structured failure report, or via context-budget exhaustion after `record`/`done` of the current phase (then list the remaining runnable phases). A silent empty return is a protocol violation. When the main session is the implementer (Codex inline, or because the user explicitly asked it to implement or to write the plan first), the same chain duty and the same failure reporting apply to it.
```

措辞中性的理由：该协议块除注入子代理外，也被 inline 主会话经 `workflow.md` 引用（docstring 2051-2053），因此"不得返回主会话"必须限定为 `a dispatched sub-agent`，并显式覆盖"主会话即实施者"两种来源（inline 模式、用户显式指令）。

**硬约束**：只能加在进行分支。`base`（2080-2095）是四个分支共享的，写进 `base` 会让"计划全完成"分支也出现链遍历文案，撞 `test_execution_plan.py:980-988`（完成分支 `assertNotIn "Per phase loop"`，语义上也不该在完成后要求继续走链）。

### 3.3 C：`workflow.md` 三处落点

1. **`[workflow-state:in_progress]` 块内、246 行 Execution plan 行之后**新增一行（主会话视角，块内新增行无逐字断言约束；按 99-142 行 BREADCRUMB CONTRACT 的 INVARIANT，`[required]` 类义务须在本块有 enforcement 行）：

```text
Dispatch granularity (default): one implement round = one dispatch = the whole remaining runnable chain (the sub-agent walks phase after phase up to the terminal report phase), not one phase per dispatch. In sub-agent dispatch modes the implement sub-agent advances plan state itself (start/record/done/block); by default the main session runs only read-only `plan.py status` between rounds to decide re-dispatch vs 2.2, and does not advance plan state on the sub-agent's behalf. The `<execution-plan>` breadcrumb prints the current round's `dispatch chain:` line.
User instructions override these defaults: when the user explicitly asks the main session to implement directly, the main session acts as the implementer for that round and advances `plan.py` itself, with the same chain duty and the same failure reporting; when the user explicitly asks the main session to write the plan first, the main session may create and `validate` the execution plan and then dispatch an implement sub-agent that picks up the in-progress chain instead of re-planning.
```

例外句设计要点（用户 2026-09-26 明确要求）：
- 默认口径与例外分两句写，例外句以 `User instructions override these defaults` 开头，且两种情形都带 `explicitly asks` 限定词，避免被读成"主会话随时可自行实施"。
- 与既有语义不冲突：`Round 1 — plan generation`（protocol block 2101、四份代理定义同构条目）默认仍由实施者建计划，例外句只是允许"用户点名时由主会话建计划"；small patch 硬规则里已有同类先例（`when the user explicitly says this is a small patch`，`workflow.md:614`，被 `test_small_patch_and_sequel_contract.py:104-121` 锁定），本次沿用同一"用户显式声明优先"的口径，不改其原文。
- 例外句同样避开 8 个 FORBIDDEN 短语与 6 个 CODEX_ONLY_TERMS。

2. **Phase 2 gate 611 行（Between implement rounds）**：保留既有轮间判定表，补一句界定"一轮"的边界（runnable 非空 → 再派发一次并期望其走完整条链；不得按 phase 拆成多次派发）。不新增任何主会话验收关卡（用户已排除返回后 gate）。

3. **`#### 2.1`（617-634，组合标记 `[Claude Code, codex-sub-agent, OpenCode]` 块内）**：在 621 行 `Spawn the implement sub-agent:` 之后补一句派发范围说明（一次派发覆盖剩余整条链）。硬约束：保留 `Spawn the implement sub-agent` 原句（`test_codex_native_wait_contract.py:129-140` 三平台断言）；不得出现 6 个 CODEX_ONLY_TERMS（`exec_command`、`write_stdin`、`yield_time_ms`、`session_id`、`wait_agent`、`spawn_agent`，同文件 269-288）；不得破坏 619/634 行的平台标记配对（`get_context` 按标记切块）；不得触碰 2.1.2 标题与紧随的 `[Codex]` 包裹（290-304 行正则）。

`[workflow-state:in_progress-inline]`（270-275）**零 diff**：inline 模式主会话本身就是实施者，"不得代跑 plan.py" 的禁令不适用；该块的 274 行 Execution plan（main session as executor）保持原样。

### 3.4 D：四份代理定义落位

| 文件 | 落点 | 形态 |
|---|---|---|
| `.claude/agents/trellis-implement.md` | Executing（65-71）末尾 + Stop on completion（122-125）+ Report Format（178-198） | Markdown 段落 / 列表项 |
| `.opencode/agents/trellis-implement.md` | Executing（76-82）+ Stop on completion（135-138）+ Report Format（191-211） | 同上 |
| `.codex/agents/trellis-implement.toml` | Execution Plan Protocol 第 30 行长句 + 第 43 行 Stop on completion + 53-56 行 "Before finishing, summarize" 清单 | 压缩单行体；三引号 `"""` 内不得出现 `"""`，现有文本无反斜杠，新增文本同样避免反斜杠 |
| `.trellis/agents/implement.md`（channel worker 卡） | Executing（79-87）+ Stop on completion（134-138）+ Report Format（176-196） | 与 148-159 的 Channel Termination Contract 衔接：该卡已有"不得静默挂起"义务，新增文本须与之一致而非重复冲突 |

三处共同内容（各按自身句式落位，共享关键短语以便 parity 断言）：
- 禁令：`Do not return after a single phase`（继续到下一个 runnable phase，直到终端 report phase done）。
- 定义：`Stop on completion` 的 completion = 整个计划（含终端 report phase），不是当前 phase。
- 报告两行：`Plan phases advanced: <ids>`、`Remaining runnable: <ids|none>`（Codex TOML 落在 "Before finishing, summarize" 清单内）。

## 4. E：链行推导与输出

### 4.1 新辅助函数

```python
def _dispatch_chain(plan: dict[str, Any]) -> list[str]:
    """Remaining phases for the current dispatch round, in topological order."""
```

- 输入：已加载的 plan dict（与 `compute_status` 同源）；输出：phase id 列表，空列表表示不显示该行。
- 种子：`status == "in_progress"` 的 id（按 plan 声明序）+ runnable id（pending 且全部 `depends_on` 已 completed）。
- 扩展：沿**反向邻接**（谁依赖我，范式见 `execution_plan.py:805-807`）向前 BFS/DFS，只纳入 `pending` / `in_progress` 节点；`completed` 与 `blocked` 不入链，且**不穿过 blocked 节点**继续扩展（被阻塞分支的下游本轮不可达）。
- 排序：对纳入的节点做 Kahn 拓扑排序，入度为 0 的并列节点按 **plan 声明序**（不用 `sorted()` 字典序，`compute_status` 的 runnable 是字典序，不能复用其顺序）；终端 report phase 因传递依赖全部节点，天然排在最后。
- 前置条件：`validate` 已保证无环（`_find_cycle` 844-866）与 report 终端性（798-835），因此可假设 DAG；仍对残余环做保护（Kahn 未排空即放弃并返回已排部分或空列表，不抛异常）。
- **fail soft**：整体包在 `try/except Exception: return []` 内。理由：`plan_breadcrumb`（2034-2045）承诺"永不抛错"，审计损坏 / 指针歧义 / 计划畸形时状态行必须退化为不显示，而不是让每轮面包屑变成错误块。

### 4.2 输出行

在 `format_status()` 的 1919-1924 条件行区（`blocked:` 行之后、verbose 任务行之前，即 **verbose 分支之外**）追加：

```text
dispatch chain: mission-core-semantics -> mission-node-speed -> config-policy-points -> verify-final
```

- 仅当 `_dispatch_chain` 非空时显示；计划全完成（已有 `ALL TASKS COMPLETED` 行，1960-1961）或无 in_progress/runnable 时不显示。
- 放 verbose 分支之外才能进 `plan_breadcrumb`（`verbose=False`，2042 行），从而自动出现在 Claude/Codex 逐轮面包屑、OpenCode 逐轮与 SessionStart、`plan.py status` CLI（plan.py:145）、`plan_protocol_block` 末尾状态区（2145/2173）——**三平台 hook/plugin 零改动**。
- 文本硬约束：不得含子串 `frozen plans:`（`test_execution_plan.py:978 assertNotIn`）；不得模仿 verbose 任务行的 `[<status 右对齐 12>] <id>` 格式（同文件 1111 行 `assertNotIn "[   completed] discover"`）。
- `next runnable` 行保持原样，链行是新增行而非替换（既有断言面不动）。
- 性能：O(V+E) 纯内存，V ≤ 8（`max_tasks`）；OpenCode 桥接子进程 8s 超时（`session-utils.js:560`）无风险。

### 4.3 形态选择（已决）

不新增 `plan.py dispatchable` 子命令（`research/06` §6 形态二）。理由：形态二必改 3 文件（`plan.py` 90-162 argparse + main 分派、`execution_plan.py`、测试）并建议同步 protocol block 命令枚举（2083-2084）与可选 5-9 处文档，新增下游 CLI 表面积；其相对形态一的唯一增益是"强制主会话把链贴进派发 prompt"，即给主会话增加新义务——而用户已明确排除同类的主会话侧关卡（返回后 gate）。形态一 2 文件即达成同一提醒效果且自动传导三平台。

## 5. 数据流与验证层

```
execution_contract()  ──┬─ Claude hook inject-subagent-context.py:39/562 (PreToolUse)
                        ├─ Codex hook inject-subagent-context.py:39/562 (SubagentStart)
                        └─ OpenCode --json bridge → session-utils.js STATIC 常量兜底
                                     ↓ 子代理 prompt
plan_protocol_block() ─── 同三平台注入（进行分支）
                                     ↓
format_status() ── plan_breadcrumb() ── 三平台 <execution-plan> 面包屑 + plan.py status
                                     ↓
workflow.md in_progress 块 ── 每轮 <workflow-state> 面包屑（主会话）
workflow.md 2.1 / 611 ── get_context.py --mode phase --step 2.1 --platform X（主会话步骤详情）
四份代理定义 ── 各平台子代理系统提示
```

验证层（对应 AC；新增断言集中在新建的 `test_dispatch_chain_contract.py`，既有 4 个测试文件零改动、只作回归防线）：A/A' 三方 parity 由既有 `test_subagent_prompt_contract.py:339/380-386` + `test_opencode_platform_contract.py:434/436`（Node harness）动态锁定，新文件补"新短语存在"断言并复用同一动态取值范式（不复制常量）；B 由 `test_execution_plan.py:980-988/1104-1116` 既有断言保护边界，新文件补进行分支短语 + 完成分支 `assertNotIn`；C **必须走真实 CLI**（`python.md:105/165` 的既有教训：只做 `assertIn` 读原文曾漏掉可达性缺陷），三平台各跑一次 `--step 2.1`，沿用 `test_codex_native_wait_contract.py` 的 `run_step` 子进程范式但写在新文件内；D 沿用 `test_small_patch_and_sequel_contract.py:46-51` 的 `IMPLEMENT_AGENTS` 四文件循环范式；E 用进程内单测覆盖推导矩阵 + `format_status` 输出断言。

## 6. 兼容性

- **legacy 单文件布局 / sequel live 指针布局 / 冻结目录**：`_dispatch_chain` 只吃已加载的 plan dict，布局解析仍由 `resolve_live_plan`（223-313）负责；冻结目录不会被 `format_status` 当作 live（`_frozen_plan_summaries` 1856-1881 单独出 `frozen plans:` 行），链行只反映 live 计划。
- **审计损坏**：`format_status` 已有 `AUDIT DAMAGED` 分支（1897-1899、1910-1918）；链推导 fail soft 返回空 → 不显示该行，不影响既有损坏提示。
- **上游 `trellis update`**：`workflow.md` 的 tag 块是 block-level managed replacement 单位，本次改的是 `[workflow-state:in_progress]` 块正文，属该机制正常覆盖范围；块外的 2.1 / 611 行属普通正文合并面，与既有 09-21/09-24 改动同级。
- **Codex inline 模式**：`[workflow-state:in_progress-inline]` 与 2.1 的 `[codex-inline]` 变体（636-644）零 diff，inline 主会话仍自己推进 plan.py。
- **OpenCode 桥接失败**：`runPythonFragment` 失败返回空串（`session-utils.js:570-573`），此时子代理 prompt 靠代理定义（D）与 `STATIC_EXECUTION_CONTRACT`（A'）兜底 —— 这正是 A' 必须逐字同步的原因。
- **既有测试零破坏**：研究确认 A–E 全部为纯新增面，无逐字冻结断言冲突（`research/02`–`06`）；三套件基线为模板 212 绿 / 根 154 绿 / 仓库级 48 例 26 失败（1.3 结构性红，失败集合须逐例一致）。

## 7. 权衡

| 决策 | 选择 | 放弃项与理由 |
|---|---|---|
| 提醒形态 | `format_status` 加链行（形态一） | `plan.py dispatchable`：新增 CLI 表面积 + 3 文件 + 文档同步，增益是强加主会话义务，与用户排除返回后 gate 的取向冲突 |
| 提前返回 | 允许 `block` 与"预算耗尽先收尾再报告"两种 | 只允许 `block`：预算耗尽不是受阻，会把可用 phase 标成 blocked 并逼出 `revise` |
| 失败检测 | 只靠子代理自报（block + 结构化报告）与状态输出可见性 | 主会话返回后 gate（diff + check_recorded）：用户 2026-09-26 明确排除 |
| 链行顺序 | 拓扑序 + plan 声明序 tie-break | 复用 `compute_status.runnable`：那是 `sorted()` 字典序，表达不了执行顺序 |
| 箭头字符 | ASCII `->` | `→`：与既有面包屑风格更接近，但给下游终端/hook 增加编码风险 |
| 测试落位 | 新建 `test_dispatch_chain_contract.py`，A–E 断言集中一处（用户最终决定） | 加进既有 4 个文件（规划中途的方案 1，已撤回）：不新增文件但断言分散 4 处、文件名与"派发链"无关，将来定位成本高。集中一处的代价是多一个永久文件 + 一行清单登记，收益是可发现性与职责边界清晰（先例：`09-24` 的 `test_step_detail_platform_hints.py`） |
| 纯 spec 提醒（无任何测试） | 不采纳 | 文字改动无编译器保护；本项目 09-21 已发生过"合同写在文件里但平台收不到"且无哨兵拦截的事故（`python.md:105/165`），spec 提醒不构成机械防线 |
| 主会话约束强度 | 写成默认口径 + "用户显式指令优先"例外（主会话可自行实施，也可先写/批准 plan 再派发） | 写成绝对禁令：会堵死用户点名要主会话下场或先出计划的合法用法，且与既有 small-patch"用户明确说小修"优先口径不一致 |
| 例外的实现形态 | 仅合同文本（workflow.md / protocol block），不加机械门禁 | 用 hook/插件强制拦截主会话实施：属新增拦截通道，超出本任务范围且与"hook 永不 load-bearing"的项目约束冲突 |

## 8. 回滚

- 全部改动为文本追加 + 一个纯函数 + 一个新测试文件 + 一行清单登记；无 schema、无状态机、无文件格式变更 → 单 commit `git revert` 即可完整回滚，不留残余状态。
- 分阶段回滚点：A/A'（含 parity）→ B → E（函数 + 行）→ C → D → S7 测试与登记 → R8 spec。每阶段结束跑模板套件，红则回退该阶段而不影响已完成阶段；S7 的断言与被测文本属同一回滚单元（先加文本再加断言，回退时同时撤掉）。
- 下游已安装项目不受影响，直到执行 `trellis update`；根目录自用实现零改动，本仓库自身工作流行为不变。

## 9. 风险

1. **A' 漏改**：Python 与 JS 常量不一致 → 既有 parity 测试立即红（安全网已存在，属可接受风险）。
2. **C 文本踩雷**：FORBIDDEN 8 短语 / CODEX_ONLY_TERMS 6 词 / `assertNotIn` 旧句 / 2.1.2 标题与 `[Codex]` 之间的插入禁令 → 新测试与既有 5 个测试文件共同覆盖；实施前按 `research/04` §3 清单逐条自检。
3. **B 落位错分支**：写进 `base` 会污染完成分支 → 新测试对完成分支做 `assertNotIn` 锁定。
4. **链行语义误读**：链行是"本轮应连续完成的剩余 phase"，不是"并行可做"（`allow_parallel_tasks: false`）→ 行文本与 C/D 文案都写明串行推进。
5. **面包屑变长**：每轮多一行（≤ 8 个 id）→ 可忽略；OpenCode 桥接 8s 超时不受影响。
6. **例外句被过度解读**：`User instructions override these defaults` 可能被读成"主会话随时可自行实施/自行写 plan" → 两种情形都带 `explicitly asks` 限定词，并在测试里断言限定词与例外句同时存在（缺一即红）；默认句在前、例外句在后，保持"默认优先、例外需点名"的阅读顺序。
7. **仓库级 26 失败基线漂移**：若开工前基线与 `research/01` 不一致（并行窗口改动导致），以开工前实跑快照为准并要求提交前失败集合一致，不得为修绿触碰 manifest/history/VERSION。
