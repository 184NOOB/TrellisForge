# Final Report — 10-01-allow-plan-post-complete-edit

## Goal

下游模板中，同一份 live 执行计划在全部阶段（含终态 `report`）完成后，仍可原地 `plan.py revise` 补加/重开步骤并重跑终态验收；`plan.py sequel` 与 `plans/<n>/` 指针布局保留为「显式另开一本计划」的兼容路径，不再是完成后必经。根目录自用 Trellis 运行时不在本任务写入范围内。

## Changed Files

模板交付物（全部在 `templates/embedded-c-overlay/`）：

- `.trellis/scripts/common/execution_plan.py` — 完成态重开引擎：`effective_completion_events` / `effective_completed_ids` / `pending_sanctioned_reopens`；`cmd_revise` 全完成时重置唯一 report 为 `pending` 并清 managed 字段；`cmd_validate` sanctioned 重开（清 managed 字段、fingerprint 只比对仍生效的最后一次 `task_completed`、`plan_approved` 原子写追加 `task_reopened`、完成态 report 必须保持 `level=report` 且 `pending`）；`replay_statuses` / `_replay_start_index` 处理 `task_reopened`；`plan_protocol_block` 完成态出口改为原地 `revise`（进行中分支同步改为「大改就地 revise，sequel 在未完成时会被拒」）。
- `.trellis/scripts/plan.py` — 模块说明：`revise` 是完成态默认出口，`sequel` 为兼容命令。
- `.trellis/workflow.md` — 246 / 274 / 357 / 604 / 614 / 615 六处完成态出口文案改为原地 `revise`，604 保留指针/冻结布局事实，sequel 降级为显式兼容。
- `.trellis/agents/implement.md`、`.claude/agents/trellis-implement.md`、`.codex/agents/trellis-implement.toml`、`.opencode/agents/trellis-implement.md` — 四平台「Same-task sequel」改为「Completion-state reopen（原地 revise）」。
- `.claude/hooks/plan-pretool-reminder.py` — 全完成时两条提示指向 `revise --reason`；指针文件「written only by plan.py sequel」保留。
- `.trellis/scripts/tests/test_execution_plan.py` — 新增/更新完成态重开、补加阶段重跑 report、fingerprint 门槛、report 降级/再标 completed 拒绝、协议块与 CLI revise 流测试；sequel 冻结/指针/只读测试全部保留。
- `.trellis/scripts/tests/test_small_patch_and_sequel_contract.py` — workflow / 四平台 Agent / Claude hook 断言改为原地 `revise` 完成态出口（`assertNotIn "Same-task sequel"`；CLI `--help` 仍含 sequel）。

仓库 Spec（合同文档，任务明确授权）：

- `.trellis/spec/main/tooling/python.md` — 「模板执行计划 live 指针与 sequel」场景更新为完成态原地重开合同（签名、`task_reopened`、错误矩阵、测试清单、Wrong/Correct）。

任务状态文件（非交付物）：`.trellis/tasks/10-01-allow-plan-post-complete-edit/` 下的 plan/events/task 文件由 `plan.py` 推进。

## Phase Results

| Phase | 结果 | 说明 |
| --- | --- | --- |
| engine-and-tests | completed | 引擎规则 + 单测（246 例全绿） |
| text-and-contract-tests | completed | workflow/Agent/Hook/CLI 文案与契约测试 |
| spec-contract | completed | 模板合同 Spec 更新 |
| verify-final | completed | 本报告 |

## Check Results

- `template-tests`（verify-final 重跑）：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` → **pass**，Ran 246 tests, OK。
- `root-tests`（只读回归）：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` → **pass**，Ran 154 tests, OK。
- `py-compile`：`python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py templates/embedded-c-overlay/.trellis/scripts/plan.py templates/embedded-c-overlay/.claude/hooks/plan-pretool-reminder.py` → **pass**，exit 0；Codex TOML 另用 `tomllib` 解析通过。
- `diff-check`（本任务写入路径）：`git diff --check -- templates/embedded-c-overlay .trellis/spec/main/tooling/python.md` → **pass**，exit 0。
- `git diff --check`（全局）→ **fail（非本任务产物）**：仓库工作区存在预先存在/主会话并发改动的 CRLF `task.json`（如 `.trellis/tasks/09-17-trellisforge-1-3-upgrade/task.json`、`.trellis/tasks/09-26-dispatch-chain-contract/task.json`），被 Git 判为 trailing whitespace。这是 `.trellis/spec/main/tooling/python.md`「常见错误」记录的根目录 `io.py` 换行缺陷（根侧修复需单独任务授权），与本任务改动无关；本任务所有写入路径的 diff 已用上面的 scoped 命令证明干净。
- 构建 / 部署 / 硬件验证：**not applicable**（本仓库不产出固件或可执行产品，无硬件目标）。

## Acceptance Criteria Evidence

- **AC1**：`test_add_phase_after_completion_validates_and_reruns_report`（`test_execution_plan.py`）——全完成 live plan 不跑 `sequel`、不新建任务，`cmd_revise` 后补加 `extra` 阶段并通过 `cmd_validate`；同时 `test_revise_cli_flow_after_completion_stays_in_place` 走 CLI `revise` 子命令且不产生 `plans/`。
- **AC2**：同一测试继续断言未改动的 `discover`/`edit` 仍 `completed`、`report` 为 `pending` 且 `depends_on` 覆盖新阶段，随后 `start/record/done` 重跑并写出新的 live `final-report.md`，`plan_completed` revision=2。
- **AC3**：`test_completed_task_reopen_is_sanctioned_and_requires_rerun`（重开非 report 步骤、记录 `task_reopened`、手工再标 completed 被拒）与 `test_completed_step_fingerprint_change_requires_pending_first`（仍 `completed` 时改 guarded 正文仍拒 `rewritten after completion`）。
- **AC4**：`test_report_demotion_after_completion_is_rejected`（改成 `level=minimal` 拒 `must stay level=report`）与 `test_report_marked_completed_again_is_rejected`（再标 completed 拒 `must be reset to pending`）。
- **AC5**：既有 sequel 测试全部保留并绿：`test_sequel_freezes_completed_plan_and_opens_live_two`、`test_frozen_plan_directories_refuse_mutations`、`test_pointer_fail_closed_variants`、`test_status_and_protocol_show_only_the_live_plan`、`test_third_sequel_yields_live_three_with_frozen_history`、`test_sequel_rollback_clears_empty_freeze_dir_so_retry_works`。
- **AC6**：`test_protocol_block_offers_small_patch_and_in_place_revise_when_complete` + `test_small_patch_and_sequel_contract.py`（workflow、四平台 implement Agent、Claude hook 均断言原地 `revise --reason`，且不再含 "Same-task sequel" / 完成后必须 sequel 的驱动句）。
- **AC7**：`git diff --name-only -- .trellis/workflow.md .trellis/scripts/common/execution_plan.py` 输出为空——根目录 workflow 与根目录 `execution_plan.py` 均未写入。
- **AC8**：模板与根目录单测、`py_compile`、scoped `git diff --check` 全绿；构建/硬件 `not applicable`。

## Known Notes / Risks

- **完成态重开的审计语义**：`task_reopened` 与 `plan_approved` 同一次原子写落账；`cmd_validate` 只在“JSON `pending` + 历史 `task_completed`”被识别为 sanctioned 重开时清 managed 字段，手改状态或账本仍 fail closed。回滚需在未发布/可弃账本时进行（新事件不被旧代码识别），本任务不提供迁移器——与 design.md 一致。
- **sequel 兼容**：`cmd_sequel`、指针 JSON、冻结只读、错误矩阵均未改动；完成后大修只是不再被导向它。
- **根侧有意分叉**：根目录自用 `.trellis/scripts/common/execution_plan.py` 与 `.trellis/workflow.md` 仍是旧完成态出口（无 `cmd_sequel`、无完成态原地重开），本任务未回改。
- **diff-check 记录说明**：`spec-contract` 阶段的 `diff-check` 记录使用了“排除当时唯一已知 CRLF 文件”的命令，该命令在记录前一次运行确实 exit 0；随后主会话并发改动了另一任务（09-26）的 `task.json`，使更宽范围的命令失效。最终验收改用只覆盖本任务写入路径的 scoped 命令，并以本报告披露全局差异的来源。
- **并发工作树**：`.opencode/package.json` 与 `.trellis/tasks/09-26-*` 的改动由主会话/其他任务产生，未纳入本任务范围。