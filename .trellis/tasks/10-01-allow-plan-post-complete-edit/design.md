# 设计：完成后原地补加/修改步骤

## 边界

- 写入：`templates/embedded-c-overlay/` 内 `execution_plan.py`、`plan.py` 文案、`workflow.md`、implement/check Agent、Claude `plan-pretool-reminder.py`、模板测试。
- 写入（合同文档）：`.trellis/spec/main/tooling/python.md` 的模板 sequel 条目，改为「默认原地 revise，sequel 兼容」。
- 不写入：根目录 `.trellis/workflow.md`、根目录 `execution_plan.py`、README、升级资产。
- 不删除：`cmd_sequel`、live 指针、`plans/<n>/` 冻结只读。

## 机制

完成后大修走现有 `revise` 通道，不新开子命令。

### 1. `cmd_revise`

现有行为保留：只重开 **live** 计划；不创建 sequel；先按审计把阶段重导为 `completed`/`pending`（未完成的 `in_progress`/`blocked` 落回 `pending` 并清 managed 字段）。

工程默认（与 R4 对齐，避免「只 bump revision」留下已完成 report）：若重导后**全部阶段均为 `completed`** 且存在唯一 `level=report`，把该 `report` 再置为 `pending` 并清 `verification_results`。其他已完成任务保持 `completed`。未全完成的 revise 不自动动 report。

`plan_revised` 可带信息字段 `reopened`（引擎这次拉回 pending 的 id，通常是 report）。**重开的权威不在这个字段**：以审计回放 + validate 时的 JSON 状态为准，避免 revise 写事件失败时与 heal 双写。

### 2. 模型在 `proposed` 上编辑

允许：

- 新增 `pending` 阶段（受 `max_tasks` 约束）。
- 把仍为 `completed` 的非 report 任务改成 `pending`，并改其 guarded 字段。
- 改已重置的 `report` 的 `depends_on` / `scope` / `required_checks`；`verification.level` 必须仍为 `report`，且仍是唯一 terminal report。

不允许：

- 删除仍被历史引用的任务 id。
- 保持 `completed` 的同时改 guarded fingerprint。
- 把 `report` 改成普通阶段，或让新阶段依赖 `report`。

### 3. `cmd_validate` 完成态规则

用「仍生效的完成集」替代「全日志任意一次 `task_completed`」。

回放规则：按事件序，`task_completed` 标完成，`task_reopened` 标未完成。proposed 期间额外规则：JSON 为 `pending` 且历史上曾 `task_completed` 的 id，视为**尚未入账的 sanctioned 重开**。

- 仍生效且 JSON 为 `completed`：fingerprint 必须等于该 id **最后一次** `task_completed` 的 fingerprint。
- sanctioned 重开（JSON `pending`）：允许改 guarded 字段；`plan_approved` 的同一原子写追加 `task_reopened`（每个重开 id 一条）。
- 历史完成 id 从 `tasks` 消失：仍拒绝。
- 无完成历史的新 id：只能是新阶段，状态必须是 proposed 允许的非 `completed`（通常 `pending`）。
- 存在新 id 或任何重开 id 时：唯一 `report` 必须为 `pending`，且 `level` 仍为 `report`、仍 terminal、传递依赖覆盖其余全部阶段。把 `report` 改成 `minimal` 走形状错误拒绝，不再依赖「rewritten after completion」（因为 revise 后 report 已不是 completed）。
- 声称 `completed` 但不在仍生效完成集：拒绝（不能靠手改 JSON 标完成）。

`replay_statuses`：`task_reopened` 把该 id 标回未完成。`_replay_start_index`：重开后的 verification 窗口从最新 `plan_approved`/`plan_revised` 边界起算，不再沿用重开前的 `task_completed` 窗口。下一次 `plan_approved` 的 `completed` 列表不含已重开 id，批准后的推进不依赖旧完成指纹。

### 4. 完成后再跑

与未完成计划相同：`validate` 批准 → `start` 新阶段与 pending 的 `report` → `record` → `done`。`report` 再次 `done` 时覆盖 live 目录的 `final-report.md` 并写新的 `plan_completed`。冻结目录里的旧报告不动。

### 5. `sequel`

命令、指针 JSON、冻结只读、错误矩阵保持。协议/工作流/Agent/Hook **不再**把完成后大修导向它。显式调用仍然合法（例如调用者就是要另开一本计划）。

## 跨层文案

同一完成态出口，四处保持同义：

1. 小修：不碰计划文件。
2. 同一需求要新阶段/改步骤/重跑验收：`plan.py revise --reason "..."`，编辑 live 计划，`validate` 后再改源码。
3. 不同需求、已归档、或需要独立审查/回滚：新 Trellis 任务。
4. `sequel`：可选兼容，不是默认。

必须改驱动句，不能只在远处加声明：

- `workflow.md:246,274,357,614-615`（604 的指针/冻结布局事实保留，但不得写成完成后大修必经）。
- `plan_protocol_block` 全完成分支（2122-2143）**以及**进行中分支里「justifies a sequel」（2166-2169）；未完成计划上的大改本应 `revise`，`sequel` 在未完成时会被拒绝。
- `plan.py` 模块说明里把 sequel 写成唯一后续手段的句子。
- implement 四平台「Same-task sequel」段。
- Claude `plan-pretool-reminder.py` 全完成警告（Codex/OpenCode 无对等 PreToolUse，靠协议块）。
- check Agent 仍描述 live 指针与冻结只读（布局还在），但不得把「小修永不改写冻结历史」理解成「live 完成后也不能 revise」。

## 取舍

- 不新开 `plan.py reopen`：`revise` 已是重开通道，再加命令会分叉。
- 不在 `revise` 时自动重开所有已完成步骤：用户要求未改动的保持 completed。
- 不删除 sequel：已封存下游任务靠指针才能读。
- 不改 schema：重开是审计事件，不是新 schema。

## 回滚

单一行为开关在 `cmd_validate` 完成态规则与完成态文案。若撤回，恢复「historical completed 不可降级」和「完成后导向 sequel」。已写入的 `task_reopened` 事件在回滚后不会被旧代码识别，因此回滚必须在未发布或可弃下游账本时进行；本任务不提供迁移器。
