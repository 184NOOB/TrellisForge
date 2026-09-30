# 模板单次派发走完执行计划链合同

父任务：`09-17-trellisforge-1-3-upgrade`（1.3 功能子任务；已用 `remove-subtask` + `add-subtask` 复核次序，固定收尾子任务 `09-17-readme-integration-guide-upgrade-patch` 仍在 `children` 末位）。

## Workflow Settings

- Review level: standard

## Goal

只改发布模板 `templates/embedded-c-overlay/`：把"一次 `trellis-implement` 派发 = 串行走完整条 phase 链，直到终端 report phase `done`"与"做不下去必须 `plan.py block` 并结构化上报，静默空返回属协议违规"写进三平台共享的派发合同文本，同时让 `plan.py status` 与每轮 `<execution-plan>` 面包屑直接显示"本轮应连续完成的链"，从文本与工具输出两侧消除"一个 phase = 一次派发"的误读诱因。**不动根目录自用 Trellis 运行时实现**（用户决定，且与 `.trellis/spec/main/tooling/templates-and-docs.md:14-22` 的默认归属一致）；根目录唯一可写文件是 `.trellis/spec/main/tooling/python.md`，且仅限定点新增一个 Scenario 条目记录本次模板合同（用户 2026-09-26 明确授权，先例为 `09-24` 子任务的 R5/AC7）。

## Background（实测证据，2026-09-26；锚点见 `research/`）

### B0. 触发本任务的真实事故（下游项目，非本仓库）

下游任务 `09-26-traffic-light-checkpoint-vision`（schema-3 计划，7 个 phase，`allow_parallel_tasks: false`）被主会话按 phase 逐格派发 implement 子代理；其中 `mission-core-semantics` 一轮子代理 7 分钟、7 次工具调用后**空返回**：零代码 diff、未 record 声明的 `mission-core-unittest`、未 `block`，审计日志只剩悬空 `task_started`（15:00:46Z），主会话靠人工 `git status` + 单测计数才发现白跑一轮。

### B1. 模板缺口（五处，均已核实为"文本不存在"而非"文本被忽略"）

- **G1**：`.trellis/scripts/common/subagent_prompt_policy.py::execution_contract()` 当前只讲批处理效率（批量读、别逐项 grep、别为注释重建、干完就停），**无链遍历义务、无失败上报义务**。该函数是三平台共享的唯一派发合同文本源（Claude hook / Codex hook import 取值；OpenCode 经 `--json` bridge 与 `.opencode/lib/session-utils.js:821-827` 的 `STATIC_EXECUTION_CONTRACT` 常量，三方逐字相等由 parity 测试锁定）。详见 `research/02-execution-contract-chain-A.md`。
- **G2**：`.trellis/scripts/common/execution_plan.py::plan_protocol_block()` 的"进行"分支（2148-2175 行）同样没有"不得单 phase 返回"。详见 `research/03-plan-protocol-block-chain-B.md`。
- **G3**：模板 `.trellis/workflow.md` 的 `[workflow-state:in_progress]` 块（241-263 行）写了 "between rounds run plan.py status to decide re-dispatch vs 2.2"，但**全模板从未定义 round 的粒度**；Phase 2.1 正文也只讲"派发 implement 子代理"。详见 `research/04-workflow-md-dispatch-text-C.md`。
- **G4**：四份 implement 代理定义（`.claude/agents/trellis-implement.md`、`.opencode/agents/trellis-implement.md`、`.codex/agents/trellis-implement.toml`、bundled runtime 卡 `.trellis/agents/implement.md`）的 "Executing: per phase ..." 与 "Stop on completion" 之间缺少禁令，"completion" 未定义是单个 phase 还是整个计划。详见 `research/05-implement-agent-definitions-D.md`。
- **G5**：`format_status()` 只输出 `next runnable: c, d`（1921-1922 行），且 `compute_status` 的 runnable 是 `sorted()` **字典序、不是拓扑序**（1849 行）；工具输出本身在诱导"一次做一格"。详见 `research/06-format-status-breadcrumb-E.md`。

### B2. 既有边界事实（决定写入范围）

- `.trellis/spec/main/tooling/templates-and-docs.md:14-22`：面向下游的新功能只改 `templates/embedded-c-overlay/`；根目录 `.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.agents/` 只读参考；"改根必须同步模板"是单向约束，反向不成立。
- `.trellis/spec/main/tooling/python.md:19/70/129`：多处执行计划合同"目前只存在于模板，根目录自用尚未同步，不得把模板行为写成根目录已经具备的事实；根侧回移属根级工具修复、需单独任务授权"。
- `.trellis/spec/guides/cross-layer-thinking-guide.md:130-146、157-167`：改执行计划相关文本要核对 live 解析、三平台副本、runtime-parsed 模板（`workflow.md` 被 `get_context.py` / `workflow_phase.py` / SessionStart / 逐轮 hook 解析）与"更新后端 spec 所有者"。
- `templates/language-adaptation/` 全文无 `execution_contract` / `workflow-state:in_progress` / `plan_protocol_block` / `format_status` / `trellis-implement` 命中（实测 grep 0 结果），本任务无需同步语言适配文档。

## Spec References

- `.trellis/spec/main/tooling/templates-and-docs.md` — 发布边界与"下游功能只改模板"的默认归属（14-22 行），本任务写入范围的权威依据。
- `.trellis/spec/main/tooling/python.md` — 执行计划 live 指针 / `sequel` 合同、模板测试写法约定（`REPO_ROOT = parents[3]`、子进程带 `cwd`/`PYTHONIOENCODING`/`timeout`、不得硬编码模板路径）、以及"送达验证必须走真实 CLI，不得只做文本断言"的既有教训（105、165 行）。
- `.trellis/spec/main/tooling/index.md` — 开发前检查（`git status --short`、搜索消费者、确认测试命令）与质量检查命令清单。
- `.trellis/spec/shared/validation.md` — 验证命令与 `pass` / `fail` / `not run` / `not applicable` 报告口径。
- `.trellis/spec/shared/trellis-maintenance.md` — 受保护项目定制清单与更新后必跑检查（`test_planning_gate.py`、`test_active_task_session_isolation.py`、`py_compile`、`git diff --check`）。
- `.trellis/spec/guides/index.md` + `.trellis/spec/guides/cross-layer-thinking-guide.md` — 触发条件命中"改 `plan.py` 子命令 / 执行计划路径 / runtime-parsed 模板 / 多平台命令副本"，据其检查清单核对传导面。
- 任务内研究：`research/01`…`research/08`（基线数字、A–E 全链路锚点、断言破坏面、重复表述扫描）。

## Requirements

### R1. 派发合同文本增加链遍历义务与失败契约（G1）

- 在 `execution_contract()` 返回值中追加两层语义：① 一次派发覆盖剩余整条计划链——按 `start → 编辑（限该 phase 的 scope.write）→ 跑声明检查 → record → done` 逐 phase 串行推进，直到终端 report phase `done`；**不得在单个 phase `done` 后返回主会话**；② 无法继续时必须 `plan.py block <id> --reason "..."` 并返回结构化失败报告，静默空返回属协议违规。
- 必须同步 `.opencode/lib/session-utils.js` 的 `STATIC_EXECUTION_CONTRACT` 常量，使 Python 函数 ↔ `--json` bridge ↔ JS 常量三方逐字相等（`test_subagent_prompt_contract.py:339/380-386`、`test_opencode_platform_contract.py:434/436` 强制）。
- 保留既有批处理效率语义，不得删改原句（既有断言为动态 parity，删句不会红，但会丢失已交付合同）。
- 合法提前返回只有两种，必须在文本中写清：`block`；或上下文预算将尽时先把当前 phase `record`/`done` 收尾，再返回并列出剩余 runnable phase（工程决定，理由记入 `design.md`：预算耗尽不是"受阻"，误用 `block` 会污染计划语义）。

### R2. 执行计划协议块同步（G2）

- 在 `plan_protocol_block()` 的"进行"分支追加与 R1 同义的链遍历义务与失败契约（措辞可与 R1 不同，但语义必须一致，避免出现第二套口径）。
- 措辞必须**中性**：该协议块除注入子代理外，也被 inline 主会话经 `workflow.md` 引用（docstring 2051-2053 行明示），因此"不得返回主会话"这类只对子代理成立的表述要限定为"a dispatched sub-agent must not return …"，并补一句"主会话即实施者时（inline 或用户显式要求）同一链遍历义务与失败上报义务同样适用"。
- 硬约束：完成分支不得出现字符串 `Per phase loop`（`test_execution_plan.py:988` 的 `assertNotIn`）；head 标题串 `## Trellis execution plan protocol` 不变（`test_opencode_platform_contract.py:342-348`）；sequel 状态行三短语不变（`test_execution_plan.py:1113-1116`）。

### R3. workflow.md 定义 round 并约束主会话派发粒度（G3）

- 在 `[workflow-state:in_progress]` 块内明确：一个 round = 一次 implement 派发 = 尽可能走完全部 runnable phase 直到 report phase 或 `block`；主会话不得按 phase 逐格派发；子代理派发模式下计划状态由 implement 子代理自己用 `plan.py` 推进，主会话只跑只读 `status` 决定"再派发 vs 进 2.2"。
- **上述约束一律写成默认口径，并同段给出用户显式指令优先的例外（用户 2026-09-26 明确要求）**：① 用户明确要求主会话自行实施时，主会话本轮充当实施者，自己用 `plan.py` 推进，此时链遍历义务与失败上报义务同样适用于主会话；② 用户明确要求"主会话先写好 plan"时，主会话可以创建并 `validate` 批准 `execution-plan.json`，随后派发 implement 子代理，该子代理从进行中的链接手执行，不重新造计划。例外句必须限定为"仅当用户显式要求"，不得写成主会话可随时自行实施。
- 例外不得削弱既有语义：`Round 1 — plan generation` 默认仍由实施者（通常是子代理）建计划；small patch 硬规则的"用户明确说小修"优先语义保持原样。
- `[workflow-state:in_progress-inline]`（Codex inline 变体）**不改**：inline 模式下主会话本身就是实施者，必须自己跑 `plan.py`，禁令不适用。
- 硬约束：2.1 正文必须保留 `Spawn the implement sub-agent`（`test_codex_native_wait_contract.py:129-140`）；平台可见文本不得出现 6 个 `CODEX_ONLY_TERMS`（同文件 269-288）；不得复活 `test_small_patch_and_sequel_contract.py:142-145` 的 `assertNotIn` 旧句；不得命中 `test_review_fix_ownership_contract.py:95-106` 的 8 个 FORBIDDEN 短语。
- 送达验证必须走真实 CLI（`get_context.py --mode phase --step 2.1 --platform claude|codex|opencode`），不得只做 `assertIn` 读原文（`python.md:105/165` 的既有教训）。

### R4. 四份 implement 代理定义同步（G4）

- `.claude/agents/trellis-implement.md`、`.opencode/agents/trellis-implement.md`、`.codex/agents/trellis-implement.toml`、`.trellis/agents/implement.md` 四份都要加：Executing 段"不得单 phase 返回"禁令；"Stop on completion" 补定义 completion = 整个计划（含终端 report phase）；报告格式增加 `Plan phases advanced: <ids>` 与 `Remaining runnable: <ids|none>` 两行。
- Codex TOML 注意：报告段无 `## Report Format` 标题（53-56 行是 "Before finishing, summarize" 清单），需按该文件既有形态承载同一信息；TOML 多行字符串转义与行继续符按既有写法。
- 无逐字节 mirror-parity 测试，但四份文件被同一批共享短语 `assertIn` 并列锁定（`test_small_patch_and_sequel_contract.py:147-158`、`test_opencode_platform_contract.py:206-210`、`test_subagent_prompt_contract.py:286-293`、`test_trellis_channel_contract.py:259-263`），漏改任一份会造成合同不一致。

### R5. 机械提醒：状态输出显示本轮链（G5）

- `format_status()` 在 1919-1924 行的条件行区域（**verbose 分支之外**，否则进不了 `verbose=False` 的面包屑）追加一行显示从 in_progress + runnable 出发沿 `depends_on` 正向可达的剩余链，顺序为拓扑序而非字典序，终端 report phase 收尾。
- 链推导新增独立辅助函数：可复用反向邻接范式（`execution_plan.py:805-807`）与 DFS 步行范式（816-829）、环检测（`_find_cycle` 844-866）；`validate` 已保证 DAG 与 report 终端性，推导可假设无环，但仍需对损坏/异常计划 fail soft（不抛异常、退化为不显示该行），因为 `plan_breadcrumb` 的承诺是"永不抛错"。
- 文本硬约束：新行不得包含子串 `frozen plans:`（`test_execution_plan.py:978` 的 `assertNotIn`）；不得模仿 verbose 任务行的 `[<status右对齐12>] <id>` 格式（同文件 1111 行 `assertNotIn`）。
- 传导面（零代码改动自动生效）：`plan.py status` CLI（plan.py:145）、Claude/Codex 逐轮面包屑（`.claude/hooks/inject-workflow-state.py:365-378`、`.codex/hooks/inject-workflow-state.py:378-380`）、OpenCode 逐轮与 SessionStart（`.opencode/plugins/inject-workflow-state.js:121-130`、`.opencode/lib/session-utils.js:680-687`）、`plan_protocol_block` 末尾状态区（2145/2173）。
- 工程决定：**不新增 `plan.py dispatchable` 子命令**（研究 `research/06` §6 的形态二）。理由：形态二需改 3+ 文件并新增下游 CLI 表面积，其额外价值是"强制主会话把链贴进派发 prompt"——即给主会话增加新义务，而用户已明确排除同类的主会话侧关卡；形态一 2 文件即达成同一提醒效果且自动传导三平台。记入 `design.md`。

### R6. 测试与登记（新建独立测试文件）

- 新建 `templates/embedded-c-overlay/.trellis/scripts/tests/test_dispatch_chain_contract.py`，把 A–E 的断言集中在一处（用户 2026-09-26 最终决定；先前的"加进既有 4 个文件"方案已撤回），覆盖：
  - A / A'：`execution_contract()` 含链遍历义务与 `block` 义务关键短语、原有批处理效率短语仍在；Python 函数 ↔ `--json` bridge ↔ JS `STATIC_EXECUTION_CONTRACT` 三方逐字相等（沿用既有动态取值范式，**不得把常量复制进测试**）。
  - B：`plan_protocol_block()` 进行分支含 Chain duty 短语与"主会话即实施者时同一义务适用"中性句；**完成分支 `assertNotIn` 同一短语**（锁定落位）。
  - C：`[workflow-state:in_progress]` 块同时含默认句与 `User instructions override these defaults` 例外句，例外句含 `explicitly asks` 限定词并覆盖"主会话自行实施"与"主会话先写 plan 再派发"两种情形（缺任一即红）；`[workflow-state:in_progress-inline]` 块不含该短语（inline 零改动）；既有 `Round 1 — plan generation` 与 small patch"用户明确说小修"原文仍在（防削弱）；**三平台真实 CLI** `--step 2.1 --platform claude|codex|opencode` 退出码 0 且输出含 round 定义与例外句，claude 系平台输出不含 CODEX_ONLY_TERMS。
  - D：`IMPLEMENT_AGENTS` 四文件循环断言三条新短语（不得单 phase 返回 / completion = 整个计划 / 报告两行），沿用 `test_small_patch_and_sequel_contract.py:46-51/147-158` 范式。
  - E：`_dispatch_chain` 推导矩阵（线性链、菱形依赖、blocked 剪枝且不穿过、completed 剪枝、全完成 → 空、畸形/损坏 plan → 空且不抛）+ `format_status` 在 `verbose=False` 含 `dispatch chain:` 行、全完成时不含、新行不含 `frozen plans:` 子串、legacy 与 sequel 布局下不冲突。
- 既有 4 个测试文件**零改动**（`test_subagent_prompt_contract.py`、`test_execution_plan.py`、`test_small_patch_and_sequel_contract.py`、`test_codex_native_wait_contract.py`），只要求它们保持全绿作为回归防线。
- 在 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 按既有表格行格式登记该新测试文件一行（标注 1.3 新增）。
- 只锁关键短语、落位与送达，不复述整段合同文本，避免脆断言。
- 测试写法遵循 `python.md:111` 约定：`REPO_ROOT = Path(__file__).resolve().parents[3]`、`SCRIPTS_DIR = parents[1]`、子进程 `[sys.executable, "-B", ...]` 带 `cwd=str(REPO_ROOT)`、`env` 补 `PYTHONIOENCODING=utf-8`、`encoding="utf-8", errors="replace"`、固定 `timeout`；不得硬编码 `templates/embedded-c-overlay`；不得真实 spawn/wait agent 或调用 `trellis channel`。
- C 的送达断言必须以模板根为 cwd 跑真实 `get_context.py`，覆盖三平台（`python.md:105/165`：只做文本断言曾漏掉可达性缺陷）。

### R7. 变更边界与回归基线

- 允许写入：`templates/embedded-c-overlay/` 内的 `.trellis/scripts/common/subagent_prompt_policy.py`、`.trellis/scripts/common/execution_plan.py`、`.trellis/workflow.md`、四份 implement 代理定义、`.opencode/lib/session-utils.js`（仅 `STATIC_EXECUTION_CONTRACT` 常量）、新增 `.trellis/scripts/tests/test_dispatch_chain_contract.py`、`TEMPLATE-CONTENTS.md`（仅登记该新测试文件一行）、本任务目录；根 `.trellis/spec/main/tooling/python.md`（仅 R8 的定点 Scenario）。
- 禁止写入：根目录 `.trellis/scripts/`、`.trellis/workflow.md`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`（唯一例外是 R8 授权的根 `python.md` 定点条目）；模板既有 4 个测试文件（`test_subagent_prompt_contract.py`、`test_execution_plan.py`、`test_small_patch_and_sequel_contract.py`、`test_codex_native_wait_contract.py`）——只跑不改；`VERSION`、`history/`、版本 manifest、结构迁移链、`README.md`、`docs/接入指南.md`（固定收尾子任务职责）；`tools/`；并行窗口任务 `09-22-task-dir-time-prefix`、`09-24-template-platform-hint-and-step-text` 的文件与用户既有脏改动（开工前以 `git status` 快照为准，快照内脏文件一律不触碰、不回滚）。
- 回归三套件（2026-09-26 实测基线，见 `research/01-baseline-regression.md`）：① 模板套件 `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` → **212 例 OK**，交付后须 ≥212+新增且全绿；② 根套件 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` → **154 例 OK**（只读运行，不改根文件）；③ 仓库级 `python -B -m unittest discover -s tests -p "test_*.py"` → **48 例、26 失败**（全部在 `tests/test_overlay_tools.py`，根因是 live 模板领先冻结的 1.2 manifest 触发安装器 fail-closed，属 1.3 开发期结构性红基线），开工前与提交前各跑一次，**失败集合必须完全一致**，不得新增红项，也不得为修绿触碰 manifest / history / VERSION。
- 其余：改动的 Python 文件 `python -m py_compile` 通过；`session-utils.js` 改动由既有 Node harness 覆盖，本机 Node 不可用则报 `not run` 并说明，不得记假 pass；`git diff --check` 无输出；构建 / 部署 / 硬件验证 `not applicable`（本仓库不产出固件或可执行产品）。

### R8. Spec 收敛（Phase 3.3，根 `python.md` 定点例外）

- 在根 `.trellis/spec/main/tooling/python.md` 新增一个 Scenario 条目，按该文件既有 7 段结构（Scope / Trigger、Signatures、Contracts、Validation & Error Matrix、Good/Base/Bad Cases、Tests Required、Wrong vs Correct）记录本次模板合同：单次派发链遍历义务、失败契约（`block` + 结构化报告，禁止静默空返回）、`format_status` 链行的推导与 fail-soft 语义、以及 A/B/C/D 四处文本同步点。
- 只新增该条目，不动 `python.md` 其他 Scenario；既有"合同只存在于模板、根目录自用尚未同步、不得把模板行为写成根目录已经具备的事实"的事实表述（19/70/129 行）必须保留原样，新条目同样要写明根侧未同步。
- 该文件其余部分零 diff；不得把根目录自用实现描述为已具备本次合同。

## Acceptance Criteria

- [ ] **AC1**：`execution_contract()` 新文本含"单次派发串行走完整条链、不得单 phase 返回"与"无法继续必须 `block` + 结构化报告、静默空返回属违规"两层语义，且原有批处理效率语义未丢失；Python 函数 ↔ `--json` bridge ↔ `session-utils.js` 的 `STATIC_EXECUTION_CONTRACT` 三方逐字相等（parity 测试实跑绿）。
- [ ] **AC2**：`plan_protocol_block()` 进行分支含同义义务；完成分支不含 `Per phase loop`；head 标题串与 sequel 状态行短语未变；`test_execution_plan.py` 相关断言全绿。
- [ ] **AC3**：模板 `workflow.md` 的 `[workflow-state:in_progress]` 块明确定义 round 与主会话派发粒度默认禁令，`[workflow-state:in_progress-inline]` 零 diff；`get_context.py --mode phase --step 2.1 --platform claude|codex|opencode` 三次真实 CLI 调用退出码 0 且各自输出含新 round 定义文本，`--platform claude|opencode` 输出不含 6 个 Codex 专用术语，2.1 仍含 `Spawn the implement sub-agent`。
- [ ] **AC4**：四份 implement 代理定义（含 `.trellis/agents/implement.md` 与 Codex TOML）都含新禁令、completion 定义与报告两行；四份文件的共享短语断言全绿；TOML 可被解析（无转义/行继续错误）。
- [ ] **AC5**：`plan.py status`（verbose 与非 verbose）与三平台 `<execution-plan>` 面包屑都出现链行；链为拓扑序并以终端 report phase 收尾；legacy 单文件布局、sequel live 指针布局、审计损坏布局下均不抛异常且不与 `frozen plans:` / verbose 任务行格式冲突；计划全完成时**不显示**链行（既有 `ALL TASKS COMPLETED` 行已表达终态），无 in_progress 且无 runnable 时同样不显示，两种情况都由测试锁定。
- [ ] **AC6**：模板套件全绿（报告实际用例数，≥212+新增）；既有 4 个测试文件零改动且各自全绿；根套件 154 例全绿；仓库级 48 例失败集合与开工前基线逐例一致、无新增；改动 Python 文件 `py_compile` 通过；Node harness 相关测试 pass 或明确 `not run` + 原因；`git diff --check` 无输出。
- [ ] **AC7**：功能 diff 只出现在 `templates/embedded-c-overlay/`（外加本任务目录与 R8 授权的根 `python.md` 定点 Scenario）；模板内新增文件只有 `test_dispatch_chain_contract.py`，`TEMPLATE-CONTENTS.md` 只多一行登记；根 `.trellis/scripts/`、`.trellis/workflow.md`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`、`tools/`、`docs/`、`README.md`、`VERSION`、`history/` 零 diff；并行窗口任务与用户既有脏改动未被触碰或回滚。
- [ ] **AC8**：根 `.trellis/spec/main/tooling/python.md` 新增一个 Scenario 条目，覆盖链遍历义务、失败契约、用户显式指令优先例外、`format_status` 链行推导与 fail-soft、A/B/C/D 文本同步点五项合同，且 `Tests Required` 段点名承载断言的 4 个既有测试文件；该文件其余部分零 diff；既有"合同只存在于模板、根侧尚未同步"的事实表述（19/70/129 行）保持原样，且新条目自身也写明根侧未同步。
- [ ] **AC9**：用户显式指令优先例外被文本与测试双重锁定 —— ① `[workflow-state:in_progress]` 块内含"用户显式要求时主会话可自行实施"与"用户显式要求时主会话可先写/批准 plan 再派发子代理从进行中的链接手"两句例外，且两句都带"仅当用户显式要求"限定词（不得写成主会话可随时自行实施）；② `plan_protocol_block()` 进行分支含"主会话即实施者时同一链遍历与失败上报义务适用"的中性表述，且"不得返回主会话"限定为 dispatched sub-agent；③ 既有 `Round 1 — plan generation` 默认由实施者建计划的语义与 small patch"用户明确说小修"优先语义未被削弱（`test_small_patch_and_sequel_contract.py` 既有断言全绿）；④ 例外句不命中 8 个 FORBIDDEN 短语与 6 个 CODEX_ONLY_TERMS。

## Out Of Scope

- **主会话"返回后 gate"**（子代理返回后强制核对 `git diff --stat` + `check_recorded` 才放行）——用户 2026-09-26 明确排除。
- **根目录自用 Trellis 实现的同步**：根 `.trellis/scripts/common/subagent_prompt_policy.py`、`execution_plan.py`、根 `.trellis/workflow.md`、根三份代理定义与 hooks（按 `python.md:19/70/129` 属根级工具修复，需单独任务授权）。
- **新增 `plan.py dispatchable` 子命令**（研究中的形态二）——本任务不做，理由见 R5。
- 主会话侧新增 Hook / 插件拦截通道；`plan-pretool-reminder.py` 的行为变更。
- 为"主会话自行实施 / 主会话先写 plan"新增任何机械门禁或平台机制：本次只在合同文本里写清用户显式指令优先的例外口径（R3/AC9），不改 hook、插件、`task.py` 或 `plan.py` 的行为。
- 修改模板既有 4 个测试文件（断言集中到新建的 `test_dispatch_chain_contract.py`；既有文件只跑不改，作为回归防线）。
- 审查侧合同（`trellis-check` 代理、review profile skill）、`trellis channel` worker 运行时行为。
- `VERSION`、canonical 对象库、版本 manifest、结构迁移链、`README.md`、`docs/接入指南.md`、升级补丁（固定收尾子任务负责）。
- 下游项目 `09-26-traffic-light-checkpoint-vision` 的实际返工与 `mission-core-semantics` 重做。
- `templates/language-adaptation/`（实测无相关命中）。
- 并行窗口任务 `09-22-task-dir-time-prefix`、`09-24-template-platform-hint-and-step-text` 与用户既有脏改动。

## Technical Notes

- 权威锚点集中在 `research/01`–`research/08`；实施时若行号漂移，以内容锚点重定位（先例：`09-24` PRD 用唯一字符串 `Full guide: .trellis/workflow.md. Step detail:` 重定位）。
- 重复表述扫描结论（`research/08-duplication-scan-G.md`）：目标语义在模板内 0 命中，属纯新增；但有 12 处语义相邻文本（批处理效率、小修门槛、sequel 出口、审查轮次），新文本必须与之衔接而非冲突。
- `format_status` 的 `next runnable` 行保持原样（既有语义与断言面），链行是**新增**行而非替换。
- 测试落位决定：断言集中在**新建**的 `test_dispatch_chain_contract.py`（跨 A–E 五层与三平台，独立成文件便于将来一处定位；先例 `09-24` 的 `test_step_detail_platform_hints.py`）。规划中途曾按用户意见改为"加进既有 4 个文件"，用户 2026-09-26 最终撤回该方案、改回新建文件，故既有 4 个测试文件零改动、只作为回归防线；R8 的 spec 新条目在 `Tests Required` 段点名该新文件与 4 个既有回归文件。
- 换行事实：仓库 `core.autocrlf=false`，模板 `io.py` 已写 LF（09-21 交付），本任务不预期新增 CRLF 噪声，但提交前仍跑 `git diff --check`。
- 延后候选（未建任务）：根侧同步（R1–R5 的根目录回移）、`plan.py dispatchable`、主会话返回后 gate（用户已排除，如后续改变决定需新授权）。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
- 已解决的用户决策：① 只改发布模板、不动根目录自用工作流运行时实现（2026-09-26）；② 排除主会话"返回后 gate"（git diff + check_recorded 验收关卡）（2026-09-26）；③ 根 `.trellis/spec/main/tooling/python.md` 允许定点同步——先答"不允许"后于同轮更正为"spec 可以同步"，最终取允许，边界为仅新增一个 Scenario 条目（2026-09-26）；④ 任务挂在 `09-17-trellisforge-1-3-upgrade` 下（2026-09-26）；⑤ 新增约束不得完全阻止主会话实施——用户显式要求时主会话可充当实施代理，也可先写/批准 plan 再派发子代理按 plan 实施，故所有主会话侧约束一律写为默认口径 + 用户显式指令优先例外（2026-09-26）；⑥ 测试哨兵形态：先选方案 1（断言加进既有 4 个文件），随后于同日撤回并改回**新建独立测试文件** `test_dispatch_chain_contract.py` + `TEMPLATE-CONTENTS.md` 登记一行，既有 4 个测试文件零改动（2026-09-26 最终决定）。
- 已解决的工程决策（理由见 `design.md` §4.3、§7）：机械提醒取形态一（`format_status` 新增 `dispatch chain:` 行）而非新增 `plan.py dispatchable` 子命令；合法提前返回限定为 `block` 与"上下文预算耗尽先收尾当前 phase 再报告剩余 runnable"两种；链行顺序取拓扑序 + plan 声明序 tie-break（不复用字典序的 runnable）；箭头用 ASCII `->`；测试断言集中在新建的 `test_dispatch_chain_contract.py`（跨 A–E 与三平台，一处定位），既有 4 个测试文件零改动只作回归防线；`[workflow-state:in_progress-inline]` 与 `[codex-inline]` 变体零改动（inline 模式主会话本就是实施者，禁令不适用）。
- Review level：`standard`（用户未显式指定，按 adapter 规则取默认并在此明示，不因 AI 风险判断上调）。
