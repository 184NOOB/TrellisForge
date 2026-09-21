# Codex 原生静默等待与等待合同可达性：终态验收报告

- 任务：`09-21-codex-native-wait-quiet`（父任务 `09-17-trellisforge-1-3-upgrade`）
- 执行计划：`execution-plan.json` revision 1，7 个 phase（`p1`-`p7`）
- 审查等级：`reinforced`
- 日期：2026-09-22

## 任务目标与最终结论

修复模板等待合同送达链路的三处可达性缺陷（编号子步骤被截断、`[Codex]` / `[Claude Code]` 平台家族别名不匹配、Codex 入口不传 `--platform`），顺带修复同源的 `--platform claude` 丢派发指令与 `write_json` 的 CRLF 换行，并新增 Codex 主会话原生子代理静默等待合同 `#### 2.1.2`。**最终结论：AC1-AC12 全部通过；模板全量测试 201 例与根目录回归 154 例全绿；`git diff --check` 无输出；功能改动只落在 `templates/embedded-c-overlay/` 与任务目录；reinforced 独立审查 0 blocking，本轮非阻塞小修全部落实。**

## 逐阶段结果

| Phase | 内容 | 声明检查（真实退出码） |
| --- | --- | --- |
| `p1-tests-red-baseline` | 新增 `test_codex_native_wait_contract.py`（4 个 TestCase 类）与 `test_write_json_lf.py`；采集红基线 20 条断言失败到 `research/baseline-red.log` | `py-compile-new-tests`=0；`red-baseline-log-captured`=0（`--artifact research/baseline-red.log`） |
| `p2-workflow-phase-reachability` | `_STEP_HEADING_RE` 捕获完整编号、`get_step` 归并编号子步骤、`_platform_matches` 增加 codex / claude 家族别名，`git_context.py` 的 `--step` help 补 `2.1.1` | `unittest-step-extraction`=0（7/7）；`unittest-platform-alias`=0（7/7）；`cli-step-2-1-1-exit0`=0；`cli-claude-alias-delivers-dispatch`=0 |
| `p3-delivery-entry` | Loading Step Detail 追加三行 `--platform` 平台中立示例；`.codex/hooks/session-start.py:470` 提示串补 `--platform codex` | `workflow-platform-hints-present`=0；`codex-hook-hint-platform-codex`=0；`py-compile-codex-hook`=0 |
| `p4-native-wait-contract` | 新增 `#### 2.1.2` `[Codex]` 静默等待合同（8 条要点）；`TEMPLATE-CONTENTS.md` 登记两个新测试文件 | `unittest-native-wait-contract`=0（7/7）；`cli-step-2-1-codex-both-contracts`=0；`template-contents-registered`=0；另跑全文件 23/23 OK |
| `p5-write-json-lf` | `common/io.py` 的 `write_json` 以 `newline="\n"` 打开临时文件并补 docstring | `unittest-write-json-lf`=0；`py-compile-io`=0 |
| `p6-full-validation` | 全量验证与边界审计；把本任务与父任务 `task.json` 只改换行地规范化为 LF | `unittest-template-all`=0（201 例）；`unittest-root-all`=0（154 例）；`py-compile-touched`=0；`cli-matrix-manual`=0（批处理 10/10）；`git-diff-check`=0（无输出） |
| `p7-report` | 本报告；reinforced 审查三项小修后的终态复查 | `unittest-template-all`=0（201 例）；`unittest-root-all`=0（154 例）；`git-diff-check`=0（无输出）；`report-written`=0 |

## 交付清单

| 文件 | 说明 |
| --- | --- |
| `templates/embedded-c-overlay/.trellis/workflow.md` | Loading Step Detail 增加 `--platform` 三平台示例；新增 `#### 2.1.2` 原生静默等待合同；未改 2.1.1 |
| `templates/embedded-c-overlay/.trellis/scripts/common/workflow_phase.py` | `get_step` 支持编号子步骤归并；`_platform_matches` 增加 codex / claude 家族别名（对称表）；docstring 同步 |
| `templates/embedded-c-overlay/.trellis/scripts/common/git_context.py` | `--step` help 文案补 `2.1.1` 示例（仅文案） |
| `templates/embedded-c-overlay/.trellis/scripts/common/io.py` | `write_json` 以 `newline="\n"` 写出 LF；原子写与 JSON 内容不变 |
| `templates/embedded-c-overlay/.codex/hooks/session-start.py` | Step detail 提示串补 `--platform codex`（仅一行文案） |
| `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` | 以 1.3 新增登记两个测试文件（第 13-14 行） |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_codex_native_wait_contract.py` | 新增：真实 CLI 送达、别名矩阵、送达入口、2.1.2 冻结文本（23 用例） |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_write_json_lf.py` | 新增：`write_json` 仅输出 LF、回读相等、无 `.tmp` 残留 |
| `.trellis/tasks/09-21-codex-native-wait-quiet/research/cli_matrix.py` | 审查 should-fix 的可重放驱动：13 个 CLI 用例逐项 PASS/FAIL，失败退出 1 |

## AC 验收结论（AC1-AC12）

- [x] **AC1 pass**：`--step 2.1 --platform codex` 同时送达 2.1.1 Channel 合同与 2.1.2 原生合同。证据：`research/cli_matrix.py` 用例 `step-2.1-codex-both-contracts`（PASS）与 `TestStepExtraction` / `TestNativeWaitContractText`。
- [x] **AC2 pass**：同命令不带 `--platform`（下游 Codex 真实路径）同样送达两段合同。证据：用例 `step-2.1-plain-both-contracts`（PASS）与 `-k test_both_contracts_delivered_with_and_without_platform`。
- [x] **AC3 pass**：`--platform claude-code` 输出不含 `exec_command` / `write_stdin` / `yield_time_ms` / `session_id` / `wait_agent` / `spawn_agent` 正文（2.1.1 / 2.1.2 标题可见）。证据：用例 `step-2.1-claude-code-no-codex-terms`（PASS）与 `test_claude_platforms_never_see_codex_term_bodies`。
- [x] **AC4 pass**：`--platform claude` 输出含 `Spawn the implement sub-agent` 与 `trellis-implement`，不含 Codex 术语正文。证据：用例 `step-2.1-claude-dispatch-no-wait`（PASS）与 `test_claude_alias_delivers_dispatch_instructions`。
- [x] **AC5 pass**：`--step 2.1.1` / `2.1.2` 各自退出 0；`--step 2.2` 不含 2.1.x；裸 `--step 1|2|3` 退出 2。证据：用例 `step-2.1.1-exit0`、`step-2.1.2-exit0`、`step-2.2-clean`、`bare-step-1|2|3-exit2` 与对应测试。
- [x] **AC6 pass**：别名矩阵全绿——`[Codex]` 对 `codex-sub-agent` / `codex-inline` 都渲染，两者互不别名；`[Claude Code]` 对 `claude` / `claude-code` 都渲染；无跨家族别名。证据：`TestPlatformAlias` 7/7（含组合标记 `[Claude Code, codex-sub-agent, OpenCode]`）。
- [x] **AC7 pass**：2.1.2 合同包含全部必备要点与 17 个冻结子串（唯一派发、连续等待、`取该工具允许的最大值`、分钟级、`120000`、禁用 30000 短窗口、`timed_out` 非失败、禁止读代码或 diff 正文清单、两种最多一次进展确认、交互中断、最小最终结果、异常入口不循环、只约束 Codex 主会话）。证据：`TestNativeWaitContractText` 7/7。
- [x] **AC8 pass**：Loading Step Detail 含三平台示例；Codex Hook 提示串含 `--platform codex`，其余 Hook 行为不变。证据：`test_loading_step_detail_names_all_three_platforms`、`test_codex_session_start_hint_passes_platform` 与模板全量 201 例全绿。
- [x] **AC9 pass**：模板 `write_json` 写出的文件不含 `\r\n` 且有测试覆盖；根目录 `common/io.py` 无 diff。证据：`test_write_json_emits_lf_only` 与 `git status --short`。
- [x] **AC10 pass**：新测试通过（23/23）；模板套件 201 例全绿；根目录回归 154 例全绿；`py_compile` 通过；`git diff --check` 无输出。证据：p7 四条声明检查全部 exit 0。
- [x] **AC11 pass**：`git diff` 功能改动只在 `templates/embedded-c-overlay/`（6 个文件）外加任务目录；根 `.trellis/workflow.md`、`.trellis/scripts/common/workflow_phase.py`、`io.py`、`git_context.py` 无功能 diff。证据：`git diff --stat` 边界审计。
- [x] **AC12 pass**：全部模板 CLI 复核命令以模板根为 cwd（`cli_matrix.py` 自推 `TEMPLATE_ROOT`，未从仓库根误读）；`TEMPLATE-CONTENTS.md` 已登记两个新测试文件。证据：`cli_matrix.py` 输出 `template_root: .../templates/embedded-c-overlay` 与登记测试。

## 检查分类报告

| 类别 | 结果 |
| --- | --- |
| 模板全量测试 | pass — `Ran 201 tests ... OK`（含 OpenCode Node harness） |
| 根目录回归测试 | pass — `Ran 154 tests ... OK` |
| `py_compile` | pass — 6 个改动 Python 文件 + `research/cli_matrix.py` |
| CLI 矩阵 | pass — `research/cli_matrix.py` 13/13 PASS（p6 批处理 10/10 PASS） |
| `git diff --check` | pass — 无输出、退出码 0 |
| 构建 | not applicable — 本仓库不产出固件或可执行产品 |
| 部署 | not applicable — 无部署目标；模板由安装脚本分发，安装验证属目标仓库 |
| 硬件验证 | not applicable — 无硬件目标 |

## reinforced 独立审查结论与处置

- 审查结论：**0 blocking、1 should-fix、3 nit**（affected-scope，reinforced 分级）。
- 本轮落实的 3 项可执行小修：
  1. should-fix — `cli-matrix-manual` 审计可重放性：新增 `research/cli_matrix.py`（13 用例、逐项 `PASS/FAIL`、失败退出 1），真实运行 **13/13 PASS、exit 0**；`cli-matrix-manual` 的可重放工件＝`research/cli_matrix.py`。
  2. nit — `get_step` docstring 的 "column-0 `---`" 与实现 `line.strip() == "---"` 不符：措辞改为 "a `---` rule line"，判定逻辑未动。
  3. nit — `test_filtered_substep_does_not_leak_codex_body` 断言偏窄：改为对 `--step 2.1.2 --platform claude-code` 断言全部 6 个 `CODEX_ONLY_TERMS` 与 3 个中文冻结短语（`取该工具允许的最大值`、`交互中断`、`最小最终结果`）缺席，保留"退出码 0、标题行可见、不断言输出为空"的既有口径与注释。
- 审查的第 4 项发现（nit：`_PLATFORM_FAMILY_ALIASES` 对称语义使裸 `codex` 也能匹配 `[codex-sub-agent]` 块）由审查自身裁定为**可接受、无需改动**：CLI 路径必先经 `resolve_effective_platform` 命名空间化，裸 `codex` 到不了 `filter_platform`；即便绕过，也只是家族内超集渲染，不构成跨家族泄露（`test_no_cross_family_aliases` 已锁定）。记入下方"已知偏差与取舍"第 4 条。
- 除此之外审查无其他待落实项；reinforced 要求"阻塞发现为零"已满足，未触发新一轮独立复审（本轮改动均为非阻塞小修，由主会话独立复跑验证：模板 201 例、根 154 例、`cli_matrix.py` 13/13、`git diff --check` 均 exit 0）。

## 已知偏差与取舍

1. 父任务 `task.json` 出现一次性全文件换行 diff：HEAD 中 13 个 `task.json` 均为 CRLF；p6 只把本任务与父任务 `task.json` 的换行规范化为 LF，未改 JSON 内容。规范化后与 HEAD 的内容差异只有 `children` 新增 `"09-21-codex-native-wait-quiet"` 一行；`git diff` 因每行 CRLF→LF 仍显示 34/33 行变化，`git diff --check` 已无 trailing whitespace。
2. p6 的 `cli-matrix-manual` 记录使用描述性 command id：当时的批处理是带函数的多语句 PowerShell，记录时内嵌引号会被 PowerShell 5.1 原生传参拆散。本轮按审查补齐可重放工件（见上）。
3. 2.1.2 标题刻意留在 `[Codex]` 块外（与 2.1.1 一致的最小 diff）：`--step 2.1.2 --platform claude-code` 仍可见标题行、正文全部被过滤，测试按"标题可见、正文不泄露"断言，不断言输出为空。
4. 别名表为对称语义，`[codex-sub-agent]` 也会匹配裸平台名 `codex`；CLI 路径先经 `resolve_effective_platform` 命名空间化，不影响 AC6 矩阵与下游行为。

## 残余风险与后续候选任务

1. 根 `.trellis/scripts/common/io.py` 仍无 `newline="\n"`：根自用 `task.py` / `plan.py` 写出的 `task.json` 继续是 CRLF，每次 `git diff --check` 前仍需人工规范化（模板已修，根同步另议）。
2. 根自用 `.trellis/workflow.md`、`.trellis/scripts/common/workflow_phase.py`、`.trellis/scripts/common/git_context.py` 未同步模板修复：根路径仍存在 2.1.1 截断、`--platform claude` 丢块、`--platform codex` 丢 `[Codex]` 块等可达性缺陷。
3. `.claude/hooks/session-start.py:726` 与 `.opencode/lib/session-utils.js:626` 的 Step detail 提示串未带 `--platform`（各自命令文档已分别传 `--platform claude` / `--platform opencode`，本任务范围外）。
4. 模板 `task.py` 的 `--step 1` 失效提示文案（既存问题，与 Codex 等待无关）。
5. 其余 12 个 CRLF `task.json` 或 `.gitattributes` 统一策略，建议随发布收尾任务一并处理。
6. 下游兼容：若下游已提交 CRLF `task.json`，安装本模板后首次写盘会出现一次性全文件换行 diff，之后稳定（可接受、自愈）。

## 待主会话处理项

- Phase 3.3：在根 `.trellis/spec/main/tooling/python.md` 增加"模板等待合同可达性"场景（`get_step` 子步骤归并、Codex / Claude 平台家族别名矩阵、`--platform` 送达入口约定、模板测试要求（真实 CLI 子进程 + `TEMPLATE_ROOT` + `PYTHONIOENCODING`）、`write_json` 换行约定），并注明根自用实现尚未同步，不得写成根目录已具备的事实。
- Phase 3.4：提交本任务改动；`.trellis/config.yaml` 保持 `session_auto_commit: false`，提交前如需可再次把 `task.json` 换行规范化为 LF。