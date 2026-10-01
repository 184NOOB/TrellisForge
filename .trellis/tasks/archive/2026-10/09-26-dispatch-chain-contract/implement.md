# 执行计划：模板单次派发走完执行计划链合同

任务：`09-26-dispatch-chain-contract`。设计见 `design.md`，需求与验收见 `prd.md`，锚点见 `research/01`–`research/08`。
所有命令在仓库根 `C:\Users\10671\Desktop\Study\TrellisForge` 下用 Windows PowerShell 执行（串联用 `;`，不用 `&&`）；标注"模板根"的命令必须以 `templates/embedded-c-overlay` 为 cwd（`python.md:74`：cwd 不对会误读仓库根 `workflow.md`）。

## 阶段清单（有序，每阶段末跑该阶段验证；红则回退本阶段）

### S1. 基线快照 `[必读，零文件改动]`

1. `git status --short` 与 `git diff --stat` 快照，记录用户既有脏改动与并行窗口任务文件（含 `09-22-task-dir-time-prefix`、`09-24-template-platform-hint-and-step-text`、`09-27-review-severity-readjudication`、`10-01-allow-plan-post-complete-edit`；快照内脏文件全程不触碰、不回滚）。
2. 三套件基线实跑并记录真实数字；**本快照即权威基线**（`research/01` 的模板 212 / 根 154 / 仓库级 48 例 26 失败仅作历史对照，不一致时以本次快照为准并在报告中说明）：
   - `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`
   - `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
   - `python -B -m unittest discover -s tests -p "test_*.py"`
3. 回滚点：无改动。

### S2. A / A' 派发合同文本（链遍历义务 + 失败契约）

1. 改 `templates/embedded-c-overlay/.trellis/scripts/common/subagent_prompt_policy.py::execution_contract()`：在既有批处理效率文本后追加 `design.md §3.1` 的英文段落（既有句子不删不改；追加段须把既有 `stop when … complete` 衔接为终端 report phase `done`）。
2. 同步 `templates/embedded-c-overlay/.opencode/lib/session-utils.js` 的 `STATIC_EXECUTION_CONTRACT`（821-827 区），与 Python 返回值**逐字相等**。
3. 自检：新文本不含 8 个 FORBIDDEN 短语、不含 `Per phase loop`、箭头用 ASCII `->`。
4. 验证：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_subagent_prompt_contract.py"`；`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_opencode_platform_contract.py"`（Node harness，本机 Node 不可用则记 `not run` + 原因，不得记假 pass）；`python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/subagent_prompt_policy.py`。
5. 回滚点：两文件文本追加，单独可退。

### S3. B 协议块进行分支

1. 改 `templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py::plan_protocol_block()`：**仅**在进行分支（2148-2175，`Per phase loop: …` 之后、terminal report phase 义务之前）插入 `design.md §3.2` 的 Chain duty 条目。
2. 严禁写进 `base`（2080-2095）或完成分支（2119-2147）。
3. 措辞中性自检（AC9②）：`不得返回主会话` 必须限定为 `A dispatched sub-agent must not return …`；必须含"主会话即实施者（Codex inline 或用户显式要求实施 / 显式要求先写 plan）时同一链遍历与失败上报义务适用"一句；不得出现无条件禁止主会话实施的表述。
4. 验证：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_execution_plan.py"`；`python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py`。
5. 回滚点：单文件文本追加。

### S4. E 链推导与状态行

1. 在 `execution_plan.py` 新增 `_dispatch_chain(plan) -> list[str]`（`design.md §4.1`：种子 = in_progress + runnable；反向邻接扩展；排除 completed/blocked 且不穿过 blocked；`allow_parallel_tasks=true` 时输出整棵剩余森林而非一枝；Kahn 拓扑 + plan 声明序 tie-break；整体 `try/except Exception: return []`）。
2. 在 `format_status()` 的 1919-1924 条件行区、**verbose 分支之外**追加 `dispatch chain: a -> b -> report` 行（仅链非空时）；不改 `next runnable` 行；新行不含 `frozen plans:` 子串、不模仿 verbose 任务行格式。
3. 验证：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_execution_plan.py"`；`py_compile` 同 S3；S7 的新测试文件落地后再跑全量。
4. 回滚点：函数 + 一处输出行，可独立回退（回退后 S7 相关断言需同步移除）。

### S5. C workflow.md 三处落点

1. `[workflow-state:in_progress]` 块（241-263）：先把 246 行主语改成 `By default the implement sub-agent creates/approves`（其余 two-level / sequel / breadcrumb display-only 原文保留），再在其后新增 `design.md §3.3` 第 1 条的 Dispatch granularity 默认句 **+ 紧随其后的 `User instructions override these defaults` 例外句**（两种情形：用户显式要求主会话自行实施；用户显式要求主会话先写/批准 plan 再派发子代理从进行中的链接手）。默认句在前、例外句在后，两句都不得省略。
2. Phase 2 gate 611 行（Between implement rounds）补一句界定"一轮 = 一次派发 = 剩余整条链"，保留既有判定表（含 `(or continue inline)`），**不新增任何主会话验收关卡**。
3. `#### 2.1`（617-634，`[Claude Code, codex-sub-agent, OpenCode]` 块内）在 `Spawn the implement sub-agent:` 之后补派发范围一句（一次派发覆盖剩余整条链）。**不要**把 round 定义或用户例外句写入 2.1——那两句只属于 in_progress 块。
4. 自检：`[workflow-state:in_progress-inline]`（270-275）与 `[codex-inline]` 变体（636-644）零 diff；新文本不含 6 个 CODEX_ONLY_TERMS、不含 8 个 FORBIDDEN 短语、不复活 `test_small_patch_and_sequel_contract.py:142-145` 的 `assertNotIn` 旧句；2.1.2 标题与紧随 `[Codex]` 之间无插入；平台标记配对完整。
5. 例外句自检（AC9①③④）：例外句含 `explicitly asks` 限定词且覆盖两种情形；`Round 1 — plan generation` 默认由实施者建计划的原文与 614 行 small patch"用户明确说小修"原文均未被改写或削弱；611 行既有轮间判定表与 `(or continue inline)` 保留，且未新增任何主会话验收关卡。
6. 验证（分通道；真实 CLI 必须以模板根为 cwd，否则会读仓库根 `workflow.md`）：
    - 读 `templates/embedded-c-overlay/.trellis/workflow.md` 的 in_progress 块：含 round 定义、`By default the implement sub-agent`、例外句与两种 `explicitly asks`。
    - 在模板根执行三次 CLI，退出码 0 且输出含派发范围句与 `Spawn the implement sub-agent`（**不**要求含 round/例外句）：
      - `Push-Location templates/embedded-c-overlay; python -B .trellis/scripts/get_context.py --mode phase --step 2.1 --platform claude; Pop-Location`
      - `Push-Location templates/embedded-c-overlay; python -B .trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex; Pop-Location`
      - `Push-Location templates/embedded-c-overlay; python -B .trellis/scripts/get_context.py --mode phase --step 2.1 --platform opencode; Pop-Location`
    - `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_codex_native_wait_contract.py"`；同跑 `test_small_patch_and_sequel_contract.py`、`test_review_profile_contract.py`、`test_review_fix_ownership_contract.py`、`test_trellis_channel_contract.py`。
7. 回滚点：单文件三处文本 + 246 主语改写，可整体回退。

### S6. D 四份 implement 代理定义

1. 按 `design.md §3.4` 表格落位：`.claude/agents/trellis-implement.md`、`.opencode/agents/trellis-implement.md`、`.codex/agents/trellis-implement.toml`、`.trellis/agents/implement.md`（均在 `templates/embedded-c-overlay/` 下）。
2. 三份共同内容：`Do not return after a single phase` 禁令、`Stop on completion` 的 completion 定义（整个计划含终端 report phase）、报告两行 `Plan phases advanced:` / `Remaining runnable:`；Codex TOML 落在 53-56 行 "Before finishing, summarize" 清单内，三引号串内不得出现 `"""` 与反斜杠；worker 卡与 148-159 的 Channel Termination Contract 衔接不重复冲突。
3. 验证：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_small_patch_and_sequel_contract.py"`、`test_subagent_prompt_contract.py`、`test_opencode_platform_contract.py`、`test_trellis_channel_contract.py`；TOML 可解析：`python -c "import tomllib,pathlib; tomllib.loads(pathlib.Path(r'templates/embedded-c-overlay/.codex/agents/trellis-implement.toml').read_text(encoding='utf-8')); print('toml ok')"`。
4. 回滚点：四文件文本追加，可整体回退。

### S7. 新建测试文件与清单登记（断言集中一处）

1. 新建 `templates/embedded-c-overlay/.trellis/scripts/tests/test_dispatch_chain_contract.py`，按 A–E 分组写 TestCase（分组便于分阶段跑绿子集），覆盖：
   - A / A'：`execution_contract()` 含链遍历义务与 `block` 义务关键短语、原有批处理效率短语仍在；Python 函数 ↔ `--json` bridge ↔ JS `STATIC_EXECUTION_CONTRACT` 三方逐字相等（**动态取值，不得把常量复制进测试**）。
   - B：`plan_protocol_block()` 进行分支含 Chain duty 短语与"主会话即实施者时同一义务适用"中性句、`must not return` 前有 `dispatched sub-agent` 限定；**完成分支 `assertNotIn` 同一短语**（锁定落位）。
    - C：分通道。① 读 `[workflow-state:in_progress]` 块含 round 定义默认句、`By default the implement sub-agent`、`User instructions override these defaults` 例外句，例外句含 `explicitly asks` 且覆盖"主会话自行实施"与"主会话先写 plan 再派发"两种情形（缺任一即红）；`[workflow-state:in_progress-inline]` 块不含这些新短语；既有 `Round 1 — plan generation` 与 small patch"用户明确说小修"原文仍在；611 行仍含 `(or continue inline)`。② **三平台真实 CLI**（cwd=模板根）`--step 2.1 --platform claude|codex|opencode` 退出码 0 且输出含派发范围句与 `Spawn the implement sub-agent`，claude 系平台输出不含 CODEX_ONLY_TERMS；**不得**断言 round/例外句出现在 `--step 2.1` 输出中。
    - D：`IMPLEMENT_AGENTS` 四文件循环断言三条新短语（不得单 phase 返回 / completion = 整个计划 / 报告两行）。
    - E：`_dispatch_chain` 推导矩阵（线性链、菱形依赖、blocked 剪枝且不穿过、completed 剪枝、全完成 → 空、畸形/损坏 plan → 空且不抛、`allow_parallel_tasks=true` 下多个独立 runnable 仍输出整棵剩余森林）+ `format_status` 在 `verbose=False` 含 `dispatch chain:` 行、全完成时不含、新行不含 `frozen plans:` 子串、legacy 与 sequel 布局下不冲突。
2. 写法遵循 `python.md:111`：`REPO_ROOT = Path(__file__).resolve().parents[3]`、`SCRIPTS_DIR = parents[1]`、子进程 `[sys.executable, "-B", ...]` 带 `cwd=str(REPO_ROOT)`、`env` 补 `PYTHONIOENCODING=utf-8`、`encoding="utf-8", errors="replace"`、固定 `timeout`；不得硬编码 `templates/embedded-c-overlay`；不得真实 spawn/wait agent 或调用 `trellis channel`。
3. 既有 4 个测试文件（`test_subagent_prompt_contract.py`、`test_execution_plan.py`、`test_small_patch_and_sequel_contract.py`、`test_codex_native_wait_contract.py`）**只跑不改**，作为回归防线。
4. 在 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 按既有表格行格式（13-14 行样式，标注 1.3 新增）登记该新测试文件一行。
5. 验证：
   - `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_dispatch_chain_contract.py"`
    - `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`（全量，期望 ≥ S1 模板用例数 + 本次新增，全绿）
   - `python -m py_compile templates/embedded-c-overlay/.trellis/scripts/tests/test_dispatch_chain_contract.py`
6. 回滚点：新文件 + 一行登记，删除即回退；与被测文本属同一回滚单元。

### S8. R8 根 spec 定点同步（Phase 3.3）

1. 在根 `.trellis/spec/main/tooling/python.md` **新增一个 Scenario 条目**（沿用该文件既有 7 段结构：Scope / Trigger、Signatures、Contracts、Validation & Error Matrix、Good/Base/Bad Cases、Tests Required、Wrong vs Correct），记录：链遍历义务、失败契约（`block` + 结构化报告、禁止静默空返回、预算耗尽例外）、用户显式指令优先例外（主会话可自行实施 / 可先写 plan 再派发）、`_dispatch_chain` 推导与 fail-soft、A/A'/B/C/D 文本同步点与 parity 约束。`Tests Required` 段点名新建的 `test_dispatch_chain_contract.py`（断言落点）与 4 个既有回归文件（zero-diff 防线）。
2. 硬边界：不动该文件其他 Scenario；保留 19/70/129 行"合同只存在于模板、根侧尚未同步"的事实表述；新条目自身写明根侧未同步；根目录其他一切文件零 diff。
3. 验证：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`（154 例全绿）；`git diff --check`；`git diff --stat -- .trellis/spec/main/tooling/python.md` 确认只有新增条目。
4. 回滚点：单文件新增段落。

### S9. 终验与报告 `[level=report]`

1. 三套件复跑：模板全量（报实际用例数，≥ S1 + 新增）、根套件与 S1 一致全绿、仓库级失败集合与 S1 逐例一致（不得新增红项，不得为修绿触碰 manifest / history / VERSION）。
2. `python -m py_compile` 覆盖本次改动的全部 Python 文件；`git diff --check` 无输出。
3. 边界自检（对应 AC7）：`git status --short` + `git diff --stat`，确认功能改动只落在 `templates/embedded-c-overlay/` + 本任务目录 + 根 `python.md` 定点条目；根 `.trellis/scripts/`、`.trellis/workflow.md`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`、`tools/`、`docs/`、`README.md`、`VERSION`、`history/` 零 diff；S1 快照内的脏改动与 `09-27` / `10-01` 文件未被触碰。
4. 写 `final-report.md`：改动文件清单、**AC1–AC9** 逐项结论与证据命令、三套件数字（对照 S1）、`not run` / `not applicable` 项及原因（构建 / 部署 / 硬件验证 `not applicable`；Node harness 不可用时 `not run`）、残余风险与延后候选（根侧回移、`plan.py dispatchable`、主会话返回后 gate）。

## 全程禁止事项

- 不改根目录任何运行时实现（`.trellis/scripts/`、`.trellis/workflow.md`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`）；根 `python.md` 仅限 S8 定点条目。
- 不新增主会话"返回后 gate"（用户明确排除）；不新增 `plan.py` 子命令；不改状态机语义与 `compute_status` 现有字段。
- 不动 `[workflow-state:in_progress-inline]`、`[codex-inline]` 变体、2.1.2 标题与 `[Codex]` 包裹、审查侧合同、channel 运行时行为。
- 不改模板既有 4 个测试文件（`test_subagent_prompt_contract.py`、`test_execution_plan.py`、`test_small_patch_and_sequel_contract.py`、`test_codex_native_wait_contract.py`）——只跑不改；新断言集中写进新建的 `test_dispatch_chain_contract.py`，`TEMPLATE-CONTENTS.md` 只加一行登记。
- 不碰 `VERSION`、`history/`、版本 manifest、结构迁移链、`README.md`、`docs/接入指南.md`、`tools/`（固定收尾子任务职责）。
- 不预支、不回写 `10-01-allow-plan-post-complete-edit` 的完成态 `revise` 语义；重叠的 `workflow.md:246` 只改 default 主语并追加链合同。
- 不执行 `git commit` / `push` / `merge` / `reset`；不回滚用户既有脏改动；不触碰并行窗口任务文件。
- 不把不可执行的检查伪造为 `pass`；按 `pass` / `fail` / `not run` / `not applicable` 如实报告并附命令或原因。

## 审查门（Review level: reinforced）

实施完成后由主会话按 `reinforced` 派发独立 affected-scope `trellis-check`；若当轮独立报告仍有 blocking，先批量修完再派发新的 Check Agent 全量复审 affected-scope，直到最新独立报告 blocking 为 0。不额外做 commit-ready 终审。blocking 发现按小修默认处理（`python.md:63` 与模板 small-patch 硬规则），修完再跑受影响阶段的验证命令。
