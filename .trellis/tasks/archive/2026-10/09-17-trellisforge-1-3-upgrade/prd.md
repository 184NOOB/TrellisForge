# TrellisForge 1.3 Upgrade

## Workflow Settings

- Review level: standard

## Goal

作为 TrellisForge 1.3 版本更新的父任务，集中管理后续逐步加入的独立子任务，并在所有功能子任务完成后统一完成 README、接入指南和升级补丁更新。

## Task Map

- 功能子任务：`09-17-small-patch-and-sequel-plans`，负责小修绕过执行计划，以及同一任务在计划闭环后另开后续计划。
- 功能子任务：`09-24-spec-first-planning-gate`，规划阶段 spec 前置读取与 `task.py start` 门禁加固（根目录自用工作流实例修复 + 模板同步）。
- 固定收尾子任务：`09-17-readme-integration-guide-upgrade-patch`。
- 后续功能子任务由用户逐步补充，均排列在固定收尾子任务之前。

## Requirements

- 父任务用于维护 TrellisForge 1.3 更新的任务树和最终集成边界，不直接作为当前实施目标。
- `09-17-readme-integration-guide-upgrade-patch` 永远是父任务 `children` 列表的最后一项。
- 后续新增的功能、工具、模板或工作流子任务必须插入固定收尾子任务之前。
- 固定收尾子任务必须在此前所有 1.3 子任务完成后，依据最终工程状态更新文档与升级补丁。
- 当前不预先定义 `docs/开发计划.md` 中尚未由用户点名启动的条目。

## Acceptance Criteria

- [x] 父任务已创建，并关联固定收尾子任务。
- [x] 当前 `children` 列表以 `09-17-readme-integration-guide-upgrade-patch` 结尾。
- [x] 后续每次新增子任务后，固定收尾子任务仍保持为最后一项（已挂载 `09-17-small-patch-and-sequel-plans` 并保持收尾在末位）。
- [ ] 所有子任务完成后执行父任务级最终集成检查。

## Out Of Scope For Current Planning Turn

- 预先定义尚未由用户提出的 1.3 子任务。
- 展开固定收尾子任务的详细 PRD、技术设计或执行计划。
- 启动任务实施，或修改产品、模板、工具和正式文档。
- 将根目录 `.opencode/package.json` 的本机插件版本钉死改动纳入 1.3 范围。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
