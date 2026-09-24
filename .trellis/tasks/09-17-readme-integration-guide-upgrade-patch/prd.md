# TrellisForge 1.3 发布收尾：README、接入指南与升级补丁

## Workflow Settings

- Review level: reinforced

## Goal

作为 TrellisForge 1.3 父任务的固定最后一个子任务，在全部功能子任务完成后，依据最终工程状态更新 README、接入指南和升级补丁。

## Background And Confirmed Facts

- 本任务是父任务 `09-17-trellisforge-1-3-upgrade` 的固定最后一个子任务。
- 父任务当前已挂载子任务：`09-17-small-patch-and-sequel-plans`（已完成，归档于 `archive/2026-09`）与 `09-21-codex-native-wait-quiet`（planning 中）；后续功能子任务仍可继续加入。详细发布范围、版本资产、升级路径和文档清单要等全部功能子任务完成后再规划。
- 1.2 的发布收尾合同是参考基线，不作为本轮已冻结的 1.3 验收。

## Requirements

- 在此前所有 1.3 功能子任务完成前，不展开本任务的详细设计或实施。
- 本任务必须始终保持为父任务 `children` 列表的最后一项。
- 详细 PRD、design 与 implement 将在功能子任务全部完成后，按当时工程状态重写。

## Acceptance Criteria

- [ ] 父任务所有前置功能子任务均已完成。
- [ ] 本任务仍是父任务 `children` 的最后一项。
- [ ] 详细发布收尾规划已按最终工程状态补齐，并获得实施批准。

## Out Of Scope For Current Planning Turn

- 现在更新 `VERSION`、manifest、canonical 对象、结构迁移链、README、接入指南或升级补丁。
- 现在实施任何 1.3 功能。

## Planning Convergence

- Status: pending
- Blocking user decisions: 1
- Blocking technical decisions: 0
- Final summary ready: no

当前阻塞项：功能子任务尚未全部完成（`09-21-codex-native-wait-quiet` 仍在 planning），无法冻结 1.3 发布收尾的具体验收。
