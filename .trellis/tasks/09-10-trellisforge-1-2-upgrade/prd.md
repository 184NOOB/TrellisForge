# TrellisForge 1.2 Upgrade

## Workflow Settings

- Review level: standard

## Goal

作为 TrellisForge 1.2 版本更新的父任务，集中管理后续逐步加入的独立子任务，并在所有功能子任务完成后统一完成 README、接入指南和升级补丁更新。

## Task Map

- 功能子任务：`09-10-add-intermediate-review-levels`，负责新增 `reinforced` 和 `comprehensive` 审查等级。
- 规划子任务：`09-10-optimize-channel-context-loading`，负责将下游模板的 Channel 上下文调整为稳定规则注入、任务与 Spec 主动读取，并增加读取失败门禁与审计证据。
- 固定收尾子任务：`09-10-readme-integration-guide-upgrade-patch`。
- 后续子任务由用户逐步补充，均排列在固定收尾子任务之前。

## Requirements

- 父任务用于维护 TrellisForge 1.2 更新的任务树和最终集成边界，不直接作为当前实施目标。
- `09-10-readme-integration-guide-upgrade-patch` 永远是父任务 `children` 列表的最后一项。
- 后续新增的功能、工具、模板或工作流子任务必须插入固定收尾子任务之前。
- 固定收尾子任务必须在此前所有 1.2 子任务完成后，依据最终工程状态更新文档与升级补丁。

## Acceptance Criteria

- [x] 父任务已创建，并关联固定收尾子任务。
- [x] 新增审查等级子任务已挂载到父任务。
- [x] Channel 上下文加载优化子任务已挂载到父任务。
- [x] 当前 `children` 列表以 `09-10-readme-integration-guide-upgrade-patch` 结尾。
- [ ] 后续每次新增子任务后，固定收尾子任务仍保持为最后一项。
- [ ] 所有子任务完成后执行父任务级最终集成检查。

## Out Of Scope For Current Planning Turn

- 预先定义尚未由用户提出的 1.2 子任务。
- 展开固定收尾子任务的详细 PRD、技术设计或执行计划。
- 启动任务实施，或修改产品、模板、工具和正式文档。

## Planning Convergence

- Status: pending
- Blocking user decisions: deferred until subsequent child tasks are supplied
- Blocking technical decisions: deferred until child-task planning
- Final summary ready: no
