# 规范 Trellis Channel 派发等待并规划 TrellisForge 1.1 升级

## Workflow Settings

- Review level: standard

## Goal

通过两个有先后关系的子任务完成 TrellisForge 的模板规则与升级交付：先在发布模板中建立 Codex 主会话正确的 Trellis Channel 派发/等待流程，再规划并实现 TrellisForge 1.1、接入说明和面向已安装 1.0 项目的安全升级方案。

父任务及两个子任务的所有改动统一在分支 `trellis-channel-dispatch-wait-and-upgrade` 上进行。

## Confirmed Facts

- `templates/embedded-c-overlay/` 是下游工程的发布模板源；仓库根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/` 是 TrellisForge 自身工作流实例。
- 模板目前没有完整复制上游提供的 `trellis-channel` Skill。若 TrellisForge 要发布自己的 Channel 规则，需要在模板中提供完整覆盖层，并处理它与下游已有上游 Skill 的关系。
- 当前安装器递归复制模板文件并在 `-Force` 覆盖前备份，但没有面向已安装 TrellisForge 1.0 项目的版本化升级补丁流程。
- 子任务 1 的 review level 已由用户改回 `standard`，提交前进行一次独立 affected-scope 审查，不进行 full-scope（全盘）审查；子任务 2 暂不编写详细 PRD。

## Child Task Boundaries

### 子任务 1：模板层 Channel 规则

子任务目录：`.trellis/tasks/09-07-trellis-channel-dispatch-wait/`

- 只修改 `templates/embedded-c-overlay/` 中与 Trellis Channel 直接相关的 Skill、Codex 工作流、worker 事件契约和模板契约测试。
- 在模板中补齐完整 `trellis-channel` Skill，并将跨平台公共规则与 Codex 主会话的 `exec_command`/`write_stdin` session 编排分层。
- 不修改根目录现用 Trellis 工作流，不修改接入指南、README、模板目录说明、安装脚本、版本号或升级逻辑。
- 以 standard profile 实施和审查，实施完成后进行一次独立 affected-scope 审查，范围限定为本任务完整 diff、直接受影响契约和全部验收项，不进行 full-scope（全盘）审查；完成后才能进入子任务 2 的详细规划。

### 子任务 2：1.1 接入与升级交付

子任务目录：`.trellis/tasks/09-07-trellisforge-1-1-upgrade/`

- 负责 TrellisForge 1.1 版本升级。
- 负责 `docs/接入指南.md`、README、`TEMPLATE-CONTENTS.md` 等接入和发布说明的必要更新。
- 负责 `tools/install-embedded-c-overlay.ps1` 的必要调整，以及面向已安装 1.0 项目的升级补丁能力。
- 后续 PRD 必须覆盖版本识别、模板文件差异、用户定制保护、冲突提示、Git 元数据备份、逐项迁移或覆盖策略、异常回滚和升级后验证。
- 本轮只登记上述目标和依赖，不编写子任务 2 的详细 PRD、design 或 implement。

## Requirements

- 父任务保持两个子任务的父子关系，并明确执行顺序为子任务 1 完成后再规划和实施子任务 2。
- 两个子任务使用同一指定分支，避免模板规则与升级机制分散到不同发布线。
- 子任务 1 的实施 agent 必须遵守禁止修改清单，不得以“发布完整性”为由提前编辑接入指南或安装脚本。
- 子任务 1 的审查 agent 必须遵守 standard 范围：实施完成后只进行一次独立 affected-scope 审查，阻塞问题修复后由主会话重跑受影响检查，不在提交前扩展为全盘审查。
- 子任务 2 的占位 PRD保持未收敛状态，直到用户在子任务 1 完成后明确要求开始规划。
- 父任务不会把仅完成子任务 1 的中间状态视为 TrellisForge 1.1 的完整交付。

## Acceptance Criteria

- [ ] 父任务 `task.json` 关联两个子任务，两个子任务均指回本父任务。
- [ ] 父任务和两个子任务的任务元数据均记录分支 `trellis-channel-dispatch-wait-and-upgrade`。
- [ ] 子任务 1 的 PRD、design 和 implement 只以发布模板为产品修改对象，并逐项禁止接入指南、安装脚本、升级逻辑和根目录现用工作流改动。
- [ ] 子任务 1 明确补齐完整 Channel Skill 覆盖层，并把公共 Channel 语义与 Codex 主会话终端编排分层。
- [ ] 子任务 1 采用 standard 审查制度，实施完成后进行一次独立 affected-scope 审查；提交前不做 full-scope（全盘）审查，审查范围限定为任务 diff、直接受影响契约、相关测试和全部验收项。
- [ ] 子任务 2 保持占位状态；父 PRD只登记其 1.1、接入文档、安装脚本和 1.0 升级方案责任。
- [ ] 三个任务保持 `planning`，未运行 `task.py start`，未产生产品实现变更。

## Out Of Scope For Current Planning Turn

- 编写或审批子任务 2 的详细升级 PRD、design 或 implement。
- 修改任何模板、Skill、工作流、Hook、代理、接入文档、安装脚本或版本文件。
- 执行 `trellis update`、升级演练、提交、推送或合并。

## Planning Convergence

- Status: pending
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: no
