# 去掉执行计划完成后冻结，允许补加或修改步骤

## Workflow Settings

- Review level: reinforced

## Goal

下游模板中，同一份 live 执行计划在全部阶段（含终态 `report`）完成后，仍可补加或修改步骤并继续实施、重跑终态验收。完成后大修默认原地 `revise`，不再必须先 `sequel` 封存旧本。

用户价值：计划跑完后发现漏步骤或步骤不对时，不必封旧本、开空白新本，也不必新开 Trellis 任务。

## Spec References

- `.trellis/spec/main/tooling/index.md`
- `.trellis/spec/main/tooling/python.md`（模板 live 指针 / `sequel` 合同；本任务要把它从「完成后必经冻结」改成「完成后默认原地 revise，sequel 仅兼容」）
- `.trellis/spec/main/tooling/templates-and-docs.md`（只改 `templates/embedded-c-overlay/`，根目录工作流只读）
- `.trellis/spec/guides/index.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`（`plan.py` 子命令、live 指针、多平台 Agent/Hook 文案）
- `.trellis/spec/guides/code-reuse-thinking-guide.md`（`cmd_revise` / `cmd_validate` / 协议块 / 契约测试同步）
- `.trellis/spec/shared/index.md`
- `.trellis/spec/shared/validation.md`
- `.trellis/spec/shared/trellis-maintenance.md`（不把根目录自用 Trellis 当交付物）

## Background

本任务是 TrellisForge 1.3 父任务 `09-17-trellisforge-1-3-upgrade` 的功能子任务。固定收尾子任务 `09-17-readme-integration-guide-upgrade-patch` 仍在 `children` 末位。

当前模板行为（只存在于 `templates/embedded-c-overlay/`，根目录没有 `cmd_sequel`）：

- `plan.py sequel` 把已完成 live plan 冻进 `plans/<n>/`，任务根变成 `{"schema": 3, "live": N}` 指针；冻结目录只读。
- 完成态出口把同一需求的新阶段/检查/报告导向 `sequel`；小修不碰计划文件。
- `cmd_revise` 可重开已完成 live plan 为 `proposed`，且不创建 `plans/`，但已完成阶段保持 `completed`。
- `cmd_validate` 拒绝已完成阶段降级和 fingerprint 变化（`execution_plan.py:981-992`），因此无法改已完成步骤正文，也无法改 `report.depends_on` 挂上新阶段。
- 形状规则：至多一个 `level=report`，且必须传递依赖所有其他阶段（`execution_plan.py:789-833`）。
- 契约测试锁住完成态必须 `sequel` 的文案：`test_small_patch_and_sequel_contract.py`、`test_execution_plan.py:1194-1210`。
- 跨层文案：`workflow.md:246,274,357,604,614-615`、implement/check 四平台 Agent、`plan_protocol_block`、Claude `plan-pretool-reminder.py`。OpenCode `STATIC_EXECUTION_CONTRACT` 不含 sequel 句子。

## Requirements

- R1. 已全完成的 live plan 可在同一份 live 文件上补加新阶段，无需 `sequel`、无需新 Trellis 任务。
- R2. 未改动的已完成步骤保持 `completed`，其 guarded 正文 fingerprint 不得变化。
- R3. 要改某个已完成步骤的正文/范围/检查，必须把它重置为 `pending` 再重跑；仍标 `completed` 时改 fingerprint 继续拒绝。
- R4. 只要发生补加或重开，终态 `report` 必须重置为 `pending`，保持 `level=report`，并更新 `depends_on` 使最终验收传递覆盖全部其他步骤；`report` 不得改成普通阶段。
- R5. 补加/修改走 `plan.py revise` → 编辑 live `execution-plan.json` → `validate` → `start/record/done`；禁止手改状态或账本。
- R6. 完成后大修的默认路径是原地 `revise`。`plan.py sequel` 与 `plans/<n>/` 指针布局保留，用于已经封过的任务解析和显式兼容，不再作为完成后必经路径，工作流/Agent/Hook 完成态出口不再引导去冻结。
- R7. 冻结目录上的 mutation 仍拒绝。损坏指针仍 fail closed。
- R8. 只改 `templates/embedded-c-overlay/` 内脚本、工作流、Agent/Hook 与模板测试；根目录 `.trellis/workflow.md` 与根目录 `execution_plan.py` 不写入。允许更新仓库 Spec `.trellis/spec/main/tooling/python.md` 中描述模板合同的条目。
- R9. README、接入指南、`VERSION`、history/migrations 仍由固定收尾子任务负责。

## Acceptance Criteria

- [ ] AC1. 已全完成（含 terminal report）的模板 live plan，不跑 `sequel`、不新建任务，即可补加至少一个新阶段并通过 `plan.py validate`。
- [ ] AC2. 补加后：未改动的已完成步骤仍为 `completed`；`report` 为 `pending` 且传递依赖覆盖全部其他步骤；随后能 `start/record/done` 并写出新的 live `final-report.md`。
- [ ] AC3. 把某个已完成非 report 步骤重置为 `pending` 后，允许改其正文/范围/检查并重跑；仍标 `completed` 时改 fingerprint 继续被拒绝。
- [ ] AC4. 把已完成 `report` 改成 `level=minimal`（或取消唯一 terminal report）仍被 `validate` 拒绝。
- [ ] AC5. 已存在的 sequel 指针任务仍能 `resolve_live_plan` / `status` / 推进 live 计划；冻结目录 mutation 仍拒绝。
- [ ] AC6. 模板 `workflow.md`、implement/check 协议、`plan_protocol_block`、Claude PreToolUse 完成态提示与对应契约测试，把完成后大修写成原地 `revise`，不再写成必须 `sequel`。
- [ ] AC7. 根目录 `.trellis/workflow.md` 与根目录 `.trellis/scripts/common/execution_plan.py` 无本任务写入。
- [ ] AC8. 模板单测（至少 `test_execution_plan.py` 与 `test_small_patch_and_sequel_contract.py`）、改动 Python 的 `python -m py_compile`、`git diff --check` 通过。构建/硬件：`not applicable`。

## Out Of Scope

- 根目录自用 Trellis 运行时（`.trellis/workflow.md`、根目录 `execution_plan.py`、根目录 Agent/Hook）。
- 删除 `plan.py sequel` 或废除 `plans/<n>/` 指针布局。
- 改变 schema 3、两级 verification、小修四条客观门槛、`max_tasks` 上限。
- 自动判断一次编辑算不算小修。
- README / 接入指南 / 升级补丁 / 版本号。
- OpenCode `trellis channel --provider opencode`。

## Key Decisions

- 已跑完的工作不能静默改写却仍标 `completed`。
- 补加新步骤：未改动步骤保持完成；`report` 重置为 pending 并更新等待关系。
- 改已完成步骤：先重置为 pending 再重跑。
- 只停用「完成后必须封存」；保留 sequel 命令与已有冻结布局的只读兼容。
- 审查等级：用户在实施批准时显式改为 `reinforced`。

## Risks

- `cmd_validate` 目前用全日志 `task_completed` 锁定完成态；若不引入 sanctioned 重开（`task_reopened` + proposed 中的 pending），R1–R4 无法同时满足 fail closed。
- `cmd_revise` 今天会按审计把所有历史完成阶段重新标回 `completed`（`execution_plan.py:1114-1141`）。只改 JSON、不改这条重导，report 无法保持 pending。
- 完成态文案还锁在：`workflow.md:246,274,357,614-615`、`plan_protocol_block` 全完成分支与进行中分支 `2166-2169`、`plan.py` 模块说明、implement 四平台、Claude Hook、`test_small_patch_and_sequel_contract.py`、`test_execution_plan.py:980-986,1194-1210`。漏改一处仍会导向必须 `sequel`。
- 已 sequel 过的任务必须继续按指针解析，不能把根文件当普通计划读。
- `constraints.max_tasks` 仍为 8：已满 8 阶段的完成计划不能再补加，只能重开已有步骤、显式 `sequel` 或新任务。
- 本仓库根目录自用工作流仍是旧完成态出口；只保证下游模板行为变化。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
