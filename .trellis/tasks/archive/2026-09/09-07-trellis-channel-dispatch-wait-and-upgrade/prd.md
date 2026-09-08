# 规范 Trellis Channel 派发等待并规划 TrellisForge 1.1 升级

## Workflow Settings

- Review level: standard

## Goal

通过两个有先后关系的子任务完成 TrellisForge 的模板规则与升级交付：先在发布模板中建立 Codex 主会话正确的 Trellis Channel 派发/等待流程，再规划并实现 TrellisForge 1.1、接入说明和面向已安装 1.0 项目的安全升级方案。

父任务及两个子任务的所有改动统一在分支 `trellis-channel-dispatch-wait-and-upgrade` 上进行。

## Confirmed Facts

- `templates/embedded-c-overlay/` 是下游工程的发布模板源；仓库根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/` 是 TrellisForge 自身工作流实例。
- 子任务 1 已完成并归档：模板已补齐完整 `trellis-channel` Skill，并加入 Codex 主会话唯一 wait/session 复用规则及契约测试。
- 当前安装器递归复制模板文件并在 `-Force` 覆盖前备份，但没有面向已安装 TrellisForge 1.0 项目的版本化升级补丁流程。
- 子任务 1 以 `standard` 完成审查并归档；子任务 2 已按用户要求进入详细规划。

## Child Task Boundaries

### 子任务 1：模板层 Channel 规则

子任务目录：`.trellis/tasks/09-07-trellis-channel-dispatch-wait/`

- 已只修改 `templates/embedded-c-overlay/` 中与 Trellis Channel 直接相关的 Skill、Codex 工作流、worker 事件契约和模板契约测试。
- 已在模板中补齐完整 `trellis-channel` Skill，并将跨平台公共规则与 Codex 主会话的 `exec_command`/`write_stdin` session 编排分层。
- 接入指南、README、模板目录说明、安装脚本、版本号和升级逻辑已按边界留给子任务 2。
- 已以 standard profile 完成受影响范围审查并归档。

### 子任务 2：1.1 接入与升级交付

子任务目录：`.trellis/tasks/09-07-trellisforge-1-1-upgrade/`

- 负责 TrellisForge 1.1 版本升级。
- 负责 `docs/接入指南.md`、README、`TEMPLATE-CONTENTS.md` 等接入和发布说明的必要更新。
- 负责 `tools/install-embedded-c-overlay.ps1` 的必要调整，以及面向已安装 1.0 项目的升级补丁能力。
- 当前规划采用电梯模型：当前模板是唯一升级目标，Forge 侧用按 SHA-256 去重的 canonical 对象和版本 manifest 保存三方合并所需历史内容，1.0 通过无收据入场适配进入该模型，结构变化走独立线性迁移链。用户已决定任一冲突都阻止整次工作树写入，由工具生成报告和候选文件，解决后重新预检。

## Requirements

- 父任务保持两个子任务的父子关系；子任务 1 已完成，当前唯一下一步是收敛并实施子任务 2。
- 两个子任务使用同一指定分支，避免模板规则与升级机制分散到不同发布线。
- 子任务 2 在当前分支完成 TrellisForge 1.1、首次接入更新、README/接入指南重构和 1.0 安全升级工具。
- 父任务不会把仅完成子任务 1 的中间状态视为 TrellisForge 1.1 的完整交付。

## Acceptance Criteria

- [ ] 父任务 `task.json` 关联两个子任务，两个子任务均指回本父任务。
- [ ] 父任务和两个子任务的任务元数据均记录分支 `trellis-channel-dispatch-wait-and-upgrade`。
- [x] 子任务 1 只修改发布模板中的 Channel 规则，并完成完整 Skill 覆盖层、平台分层、测试、standard 审查和归档。
- [ ] 子任务 2 完成 TrellisForge 1.1、接入文档、首次安装脚本和 1.0 安全升级方案。
- [ ] 父任务在子任务 2 完成并归档后达到完整交付状态。

## Out Of Scope For Current Planning Turn

- 在规划尚未收敛和获得后续明确批准前，修改模板、接入文档、安装脚本、升级工具或版本文件。
- 执行 `trellis update`、升级演练、提交、推送或合并。

## Planning Convergence

- Status: pending
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: no
