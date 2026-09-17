# 小修绕过与同一任务后续计划技术设计

## 目标与边界

本设计解开“已完成 report 后的小修只能伪造 `revise`”的死结。功能只修改 `templates/embedded-c-overlay/`。根目录 `.trellis/` 及平台目录只读，不反向同步。

两件事必须分开：

1. 小修：workflow / Agent 协议退出 `plan.py`。`plan.py` 不分类编辑。
2. 大修：当前 live plan 全部完成后冻结，另开下一份 live plan。`revise` 继续只重开当前 live plan。

```text
active task
  |
  +-- live plan incomplete
  |     +-- in-scope small patch / blocking-fix --> stay in current phase
  |     +-- plan defect -----------> revise current live plan
  |
  +-- live plan complete (all phases done, including report)
        +-- small patch / ordinary blocking-fix --> edit code, do not touch plan files
        +-- too many, messy, complex blocking-fixes or same-requirement major patch --> plan.py sequel
        +-- new requirement / archived task --> new Trellis task
```

## 小修硬规则

用户明确说“这是小修”或“不走 plan.py”时，直接按小修处理，不再叠加其余门槛。

否则以下四条必须同时满足：

- 不改验收，或只删除用户已确认过时的限制
- 范围小、同一模块、不换架构
- 不需要新的 phase 拆分
- 文档默认不同步 PRD/design；只有以后还会踩的约定才写 spec

满足时：直接改代码 → 跑该跑的检查 → 必要时补 spec。禁止 `revise`、新 phase、新任务。

修复审查或实施中的阻塞问题默认走小修，不因此开 sequel。只有阻塞项过多、冗杂且复杂，需要新的拆步、检查和 report 时，才 `plan.py sequel`。

未完成的当前 phase 内小修仍走该 phase 的 `record`/`done`。已完成 live plan 后的小修不读写执行计划文件。验收已变则不是小修：先改 PRD，再 `sequel`。

`plan.py` 不新增“这是不是小修”的检测。Hook 提醒可以在 live plan 已完成且编辑业务源码时提示“若属小修则不要 revise”，但仍是 advisory。

## Sequel 文件布局

兼容旧任务：第 1 份 live plan 继续使用任务根目录那一组文件。出现第 2 份时，把第 1 份冻结进 `plans/1/`，任务根目录改为 live 指针。

第 1 份（无 sequel 时，旧布局）：

```text
<task>/execution-plan.json
<task>/execution-events.jsonl
<task>/final-report.md
```

第 2 份及以后：

```text
<task>/execution-plan.json          # live 指针：{"schema":3,"live":2}
<task>/plans/1/execution-plan.json  # 冻结只读
<task>/plans/1/execution-events.jsonl
<task>/plans/1/final-report.md
<task>/plans/2/execution-plan.json  # 当前 live
<task>/plans/2/execution-events.jsonl
<task>/plans/2/final-report.md
```

规则：

- 同时只有一份 live。`plan_path()` / `events_path()` / report 路径全部解析到 live 目录。
- 冻结计划禁止 `start` / `record` / `done` / `block` / `revise` / `validate` 改写。`status` 可列出冻结摘要，默认仍只详列 live。
- 不设上限。`live: N` 合法。
- 每份 plan 独立 schema 3 账本；`revise` 只作用于 live。
- 旧单文件任务无需迁移即可继续 `validate`/`status`/推进。只有 `sequel` 成功后才出现 `plans/`。

指针文件必须能和真实 plan JSON 区分：真实 plan 含 `tasks`；指针含 `live` 且不含 `tasks`。损坏指针 fail closed。

## CLI 与状态机

现有子命令语义不变，全部针对 live plan。新增：

```text
python .trellis/scripts/plan.py --task "<task-path>" sequel --reason "..."
```

`sequel` 前置：

- 当前 live 已 approved
- 全部 phase `completed`，含唯一 terminal report
- 审计完整，无 drift
- `--reason` 非空

成功后：

1. 将当前 live 文件移入 `plans/<old>/`（第 1 次 sequel 时 `old=1`）
2. 在 `plans/<old+1>/` 写入新的 proposed 空骨架（或仅创建目录，由实施者写入后 `validate`）
3. 任务根 `execution-plan.json` 写成 live 指针
4. 追加 sequel 事件到**新**账本：`plan_sequel`（from、to、reason）。旧账本保持只读，不追加。

失败时工作树不变。不允许用 `revise` 把已完成 report 改成普通阶段来模拟 sequel。

新 live plan 仍须 `validate` 后才能改业务源码。验收变化必须先反映在 `prd.md`。

## 协议注入与平台文件

模板内这些消费者必须改成 live 解析，而不是写死任务根文件名：

- `execution_plan.py` 的 `plan_path` / `events_path` / `plan_exists` / breadcrumb / protocol
- `plan.py` 帮助与 `sequel` 子命令
- workflow Phase 2 门禁与小修出口
- Channel/Claude/Codex/OpenCode 的 implement / check Agent
- Claude `plan-pretool-reminder.py` 对 live 计划文件的提醒
- OpenCode `session-utils.js` 只桥接 Python，不复制路径常量

Hook 仍非门禁。Hook 关闭时，CLI 必须单独正确。

protocol 在 live plan 已全部完成且无 in_progress/runnable 时，必须提示两条出路：小修不碰计划文件；同一需求大修用 `sequel`。禁止再提示把 report 改成普通阶段。

## 兼容与回滚

- 旧单文件任务：行为与现在一致。
- 指针损坏、`plans/<n>` 缺失、多个目录同时像 live：所有变更命令拒绝。
- 回滚：未 `sequel` 则无新目录；已 `sequel` 但新 plan 未批准，可删除新目录并把指针改回上一份，但实施时默认不提供自动 rollback 命令，避免静默改历史。需要人工按任务目录恢复。
- 根目录自用 Trellis 本轮不改，因此本仓库当前会话不会获得该能力，直到安装/同步下游模板或另开根目录任务。

## 验证

模板 `test_execution_plan.py` 增加：

- 旧单文件 round-trip 不变
- 完成后 `sequel` 冻结旧文件、创建 live=2
- 未完成时 `sequel` 拒绝
- `revise` 仍不能改写已完成 report
- `status` 默认只展示 live
- 第三次 `sequel` 得到 live=3
- 损坏指针 fail closed

合约测试断言 workflow / implement Agent / protocol 含用户声明优先的小修门槛、阻塞修复默认小修，以及 `sequel`；且不再写死“任何源码编辑都必须先有 approved execution-plan.json”而不给完成态出口。
