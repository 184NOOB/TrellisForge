# 更新 README、接入指南与升级补丁

## Workflow Settings

- Review level: standard

## Goal

作为 TrellisForge 1.2 父任务的固定收尾子任务，更新 README、接入指南和升级补丁；升级补丁沿用当前工程更新逻辑。

## Confirmed Facts

- 本子任务是父任务 `09-10-trellisforge-1-2-upgrade` 的固定最后一项。
- 当前工程的升级逻辑采用版本 manifest、canonical 对象、结构迁移链、安装收据、默认预检和失败回滚等现有机制。
- 后续详细规划可参考已归档任务 `09-07-trellisforge-1-1-upgrade`，但不得在本轮提前扩展 1.2 升级范围。

## Requirements

- 在其他 TrellisForge 1.2 子任务完成后更新根目录 README。
- 同步更新中文接入指南，使其反映最终 1.2 接入与升级方式。
- 提供或更新面向 1.2 的升级补丁，并与当前工程既有更新逻辑保持一致。
- 在父任务中始终排在所有其他子任务之后。
- 实施前再依据最终 1.2 变更补齐详细需求、技术设计、执行计划和验证范围。

## Acceptance Criteria

- [ ] 父任务的 `children` 列表中，本子任务位于最后一项。
- [ ] README 与接入指南准确描述最终 TrellisForge 1.2 状态。
- [ ] 升级补丁沿用当前工程更新逻辑，并覆盖从受支持旧版本进入 1.2 的路径。
- [ ] 进入实施前完成详细规划和独立的实施批准。

## Dependency And Ordering

- 本子任务依赖父任务中排在它之前的所有 1.2 子任务完成，以最终交付状态作为文档和升级补丁输入。

## Out Of Scope For Current Planning Turn

- 确定 1.2 的完整变更清单、受支持来源版本和逐文件迁移内容。
- 编写 `design.md`、`implement.md` 或开始修改 README、接入指南和升级工具。

## Planning Convergence

- Status: pending
- Blocking user decisions: deferred until the 1.2 child-task set is complete
- Blocking technical decisions: deferred until final upgrade planning
- Final summary ready: no
