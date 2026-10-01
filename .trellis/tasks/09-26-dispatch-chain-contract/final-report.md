# 最终验收报告 — 模板单次派发走完执行计划链合同

- 任务：`.trellis/tasks/09-26-dispatch-chain-contract`
- Live plan：任务根 `execution-plan.json`（legacy 单文件布局，revision 2，唯一 terminal report phase = `verify-final`）
- 实施者：`trellis-implement` 子代理；本任务全程未执行 `git commit` / `push` / `merge`
- Revision 2 说明：final acceptance 期间发现 AC5 的"审计损坏布局"尚无测试锁定，按协议 `plan.py block verify-final` → `plan.py revise` 进入 revision 2。根目录自用 `plan.py`（根侧未同步，见 python.md Scenario 事实）不允许把已完成 phase 改回 `pending`，因此把补测并入已按 revise 合法重置的 `verify-final`：新增声明检查 `audit-damage-coverage`，同步 objective / scope.write 后重新 `validate` 批准。其余 7 个 phase 保持 completed。

## 1. 改动文件

| 文件 | 变更 |
| --- | --- |
| `templates/embedded-c-overlay/.trellis/scripts/common/subagent_prompt_policy.py` | `execution_contract()` 追加"单次派发拥有剩余整条链 / `block` + 结构化报告 / 静默空返回违规 / 预算耗尽例外"段落，既有批处理效率句零删改 |
| `templates/embedded-c-overlay/.opencode/lib/session-utils.js` | `STATIC_EXECUTION_CONTRACT` 与 Python 返回值逐字同步（三方 parity） |
| `templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py` | `plan_protocol_block()` 进行分支插入中性 Chain duty；新增 `_dispatch_chain()`；`format_status()`（verbose 分支之外）新增 `dispatch chain:` 行 |
| `templates/embedded-c-overlay/.trellis/workflow.md` | 246 行主语改 `By default the implement sub-agent`；新增 Dispatch granularity 默认句与 `User instructions override these defaults` 例外句；611 行补一轮边界并保留 `(or continue inline)`；2.1 补派发范围 bullet（保留 `Spawn the implement sub-agent`） |
| `templates/embedded-c-overlay/.claude/agents/trellis-implement.md` | Chain duty 禁令、completion 定义、报告两行 |
| `templates/embedded-c-overlay/.opencode/agents/trellis-implement.md` | 同上 |
| `templates/embedded-c-overlay/.codex/agents/trellis-implement.toml` | 同上（压缩单行体，无新增反斜杠，TOML 可解析） |
| `templates/embedded-c-overlay/.trellis/agents/implement.md` | 同上（与 Channel Termination Contract 衔接） |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_dispatch_chain_contract.py` | 新建 A–E 合同测试（25 例） |
| `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` | 新增该测试文件一行登记（1.3 新增） |
| `.trellis/spec/main/tooling/python.md` | 新增一个 Scenario（57 行，仅新增；19/70/129 行既有事实原样保留） |
| `.trellis/tasks/09-26-dispatch-chain-contract/` | `execution-plan.json`、`execution-events.jsonl`、`final-report.md`（本报告） |

## 2. 阶段结果

| Phase | 结果 | 说明 |
| --- | --- | --- |
| `baseline-snapshot` | completed | 只读 S1 快照：模板 246 / 根 154 / 仓库级 48 例 26 失败；脏文件清单记录在案 |
| `contract-text` | completed | A/A' 文本 + JS parity |
| `protocol-and-chain` | completed | B 进行分支 Chain duty；E `_dispatch_chain` + 链行 |
| `workflow-md-contract` | completed | C 三处落点；inline 变体零 diff |
| `agent-definitions` | completed | D 四份代理；TOML 解析通过 |
| `dispatch-chain-test` | completed（rev 1） | 新测试文件 24 例 + 清单一行的基线版本；rev 2 由 `verify-final` 的 `audit-damage-coverage` 补齐第 25 例 |
| `spec-entry` | completed | R8 根 `python.md` 定点 Scenario |
| `verify-final` | completed（rev 2） | 7 项终验检查全 pass；本报告即其交付物 |

## 3. 检查结果（rev 1 + rev 2，全部 pass，无 fail 记录）

- rev 1：`contract-parity`（22 tests）、`opencode-parity`（13 tests，含 Node harness）、`py-compile-policy`、`execution-plan-regression`、`py-compile-execution-plan`、`workflow-regression`（82 tests / 6 文件）、`step-2-1-delivery`（三平台真实 CLI）、`agent-shared-regression`（59 tests）、`toml-parse`、`new-contract-test`（24 tests）、`template-full-suite`（270 tests）、`py-compile-new-test`、`root-suite`（154 tests）、`diff-check-spec`（scoped `git diff --check`）
- rev 2：`audit-damage-coverage`（25 tests，新增 degraded-audit 用例）、`template-final`（271 tests）、`root-final`（154 tests）、`repo-baseline-match`（失败集合 26/26 与 S1 逐例一致）、`py-compile-final`（3 个 Python 文件）、`git-diff-check-final`（scoped 无输出）、`scope-diff-final`（git status 白名单核对通过）

## 4. AC1–AC9 逐项结论与证据

| AC | 结论 | 证据 |
| --- | --- | --- |
| AC1 | pass | `execution_contract()` 含 `One dispatch owns the whole remaining plan chain` / `run plan.py block <id> --reason` / `silent empty return is a protocol violation` / `context-budget exhaustion`，且既有批处理效率句与末句保留；Python ↔ `--json` bridge ↔ JS 常量动态三方相等（`test_subagent_prompt_contract.py` 22 例、`test_opencode_platform_contract.py` 13 例、新测试 A 组） |
| AC2 | pass | Chain duty 仅在进行分支；完成分支无该短语且仍无 `Per phase loop`；head 标题串未动（`test_execution_plan.py` 全绿、新测试 B 组） |
| AC3 | pass | in_progress 块含 `Dispatch granularity (default)`、`By default the implement sub-agent`、`User instructions override these defaults` 与两处 `explicitly asks`；inline 块零 diff；三平台 `--step 2.1` 真实 CLI（cwd=模板根）退出码 0 且含派发范围句与 `Spawn the implement sub-agent`，claude/opencode 无 6 个 Codex 术语；round/例外未对 2.1 输出断言（新测试 C 组） |
| AC4 | pass | 四份代理定义（含 TOML 与 channel worker 卡）均含 `Do not return after a single phase`、`not the end of the current phase`、`Plan phases advanced:`、`Remaining runnable:`；`tomllib` 解析通过（新测试 D 组 + 59 例共享短语回归） |
| AC5 | pass | `format_status(verbose=False)` 含拓扑序 `dispatch chain:` 行、全完成/无 runnable 不显示、行内无 `frozen plans:` 且不模仿 verbose 任务行；legacy、sequel、审计损坏、畸形计划/残余环均不抛异常（新测试 E 组 25 例；`plan.py status` verbose 输出亦含该行） |
| AC6 | pass | 模板套件 271 全绿（246 + 25 新增）；根套件 154 全绿；仓库级失败集合与 S1 逐例一致（26/26，无新增红）；改动 Python `py_compile` 通过；Node harness 实际执行（node v22.16.0）通过；scoped `git diff --check` 无输出（全局输出仅剩 S1 既存 CRLF `task.json`，见第 6 节） |
| AC7 | pass | 功能 diff 仅在 `templates/embedded-c-overlay/`（10 文件）+ 根 `python.md` 定点条目 + 本任务目录；模板新增文件仅 `test_dispatch_chain_contract.py`，清单仅多一行；根 `.trellis/scripts/`、根 `workflow.md`、根 `.claude/`、`.codex/`、`.opencode/`、`.agents/`、`tools/`、`docs/`、`README.md`、`VERSION`、`history/` 零 diff；`git status` 白名单核对通过（`scope-diff-final`） |
| AC8 | pass | 根 `python.md` 仅新增一个 Scenario（7 段结构），覆盖链遍历义务、失败契约、用户例外、`_dispatch_chain` fail-soft、A/B/C/D 同步点，`Tests Required` 点名新测试文件与 4 个既有回归文件；新条目自身写明根侧未同步；diff 仅 57 行新增 |
| AC9 | pass | 246 行默认主语 + 两条 `explicitly asks` 例外（主会话自行实施 / 先写 plan 再派发）；协议块含"主会话即实施者同一义务适用"中性句且禁令限定 `A dispatched sub-agent`；`Round 1 — plan generation` 与 small patch 原有语义未动（既有断言全绿）；例外句未命中 8 个 FORBIDDEN 短语与 6 个 CODEX_ONLY_TERMS |

## 5. 三套件数字（对照 S1 实跑基线）

| 套件 | S1 基线 | 交付后 | 结论 |
| --- | --- | --- | --- |
| 模板 `templates/embedded-c-overlay/.trellis/scripts/tests` | 246 OK | 271 OK | +25（本次新增测试文件）且全绿 |
| 根 `.trellis/scripts/tests` | 154 OK | 154 OK | 全绿，与 S1 一致（未改根运行时代码） |
| 仓库级 `tests` | 48 例 / 26 失败（全为 `test_overlay_tools.py` 冻结 1.2 manifest 项） | 48 例 / 26 失败 | 失败集合逐例一致，无新增红项 |

## 6. 未运行 / 不适用项

- 构建 / 部署 / 硬件验证：**not applicable**（本仓库不产出固件或可执行产品，见 `AGENTS.md`）。
- Node harness：**已实际执行**（node v22.16.0），非 not run。
- 全局 `git diff --check`：命令仍会输出 `task.json`（本任务目录）的 CRLF 尾随空白告警。该文件在 S1 快照前即为 CRLF 脏文件（根侧 `io.py` 未同步的既有事实，见 `python.md` 常见错误），本次实施未触碰该文件；本任务功能 diff 的等价 scoped 检查 `git diff --check -- templates/embedded-c-overlay .trellis/spec/main/tooling/python.md` 无输出。按"不触碰 S1 脏文件"边界未做换行规范化。

## 7. 已知风险与残余项

- 根目录自用实现（根 `plan.py`/`execution_plan.py`、根 `workflow.md`、根代理与 hooks）未同步本次合同，属用户明确划定的范围外（需根级任务授权）；下游项目执行 `trellis update` 前不受影响。
- 链行文本合同无编译器保护，靠 A–E 测试、三方 parity 与既有 4 个回归文件共同锁定。
- `_dispatch_chain` 对残余环返回已排部分而非 `[]`（validate 已保证合法 DAG 无环；畸形用例已测不抛异常）。
- 链行可能被误读为"可并行"：合同文本与 workflow/协议块均写明"一次派发串行走完"来消解。
- 本报告 2 节记录的 revision-2 流程依赖根侧 `plan.py` 的既有能力；若将来根侧同步模板的 sanctioned reopen，本任务的这条历史流程仍是审计可读的合法路径。

## 8. 延后候选（未建任务）

- 根侧回移（R1–R5 的根目录同步）：需单独任务授权。
- `plan.py dispatchable` 子命令（研究形态二）：本任务已决定不做，理由见 `design.md` §4.3。
- 主会话"返回后 gate"：用户 2026-09-26 明确排除，如后续改变决定需新授权。