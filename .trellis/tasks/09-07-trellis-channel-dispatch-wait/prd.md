# 规范 Trellis Channel worker 派发与等待流程

## Workflow Settings

- Review level: standard
- Review scope: 提交前进行一次独立 affected-scope 审查，不进行 full-scope（全盘）审查。

## Goal

在 TrellisForge 面向下游工程发布的模板中，为 Codex 主会话建立统一、低噪声的 Trellis Channel worker 派发与等待流程。实施或审查 worker 运行时，Codex 主会话只维护一个等待进程并持续复用其终端 session；收到终止事件后再继续处理结果，避免重复等待、进度轮询和完整对话注入造成 token 浪费。

## Confirmed Facts

- 本任务的发布源是 `templates/embedded-c-overlay/`。仓库根目录的 `.trellis/`、`.agents/`、`.claude/` 和 `.codex/` 是 TrellisForge 自身正在使用的工作流实例，不是本任务的产品修改目标。
- 发布模板已有 `.trellis/workflow.md`、`.trellis/agents/implement.md`、`.trellis/agents/check.md` 和相关契约测试，但尚未包含完整的 `.agents/skills/trellis-channel/` 与 `.claude/skills/trellis-channel/`。
- 缺少完整 Skill 是现有职责分离的结果：基础 `trellis-channel` 由上游 Trellis 在 `trellis init` 时提供。TrellisForge 若要为该 Skill 发布自己的 channel 规则，就需要把完整、可维护的覆盖层版本加入模板，而不能只发布脱离上下文的局部片段。
- `tools/install-embedded-c-overlay.ps1` 当前递归收集模板文件；新增模板 Skill 会进入其文件集合，但针对既有 1.0 安装的版本识别、差异迁移和冲突处理尚无专门升级流程。
- Trellis Channel 的 dispatcher 正常流程是启动 worker 后，用一个 `trellis channel wait` 等待目标 worker 的 `done` 或 `error` 终止事件。`progress` 是过程信息，不是完成信号。
- Codex 的 `exec_command` 可在短暂首次等待后返回仍在运行的 `session_id`；后续通过 `write_stdin` 连接同一 session。当前工具 schema 对空轮询的 `yield_time_ms` 标注范围上界为 300000 ms。该值只约束单次读取窗口，不是 worker 或 Channel CLI 的总 timeout，也不是公开文档承诺的永久上限。

## Requirements

### R1. 发布模板边界

- 所有产品修改必须位于 `templates/embedded-c-overlay/`，只处理 Trellis Channel 规则及其模板契约测试。
- 不修改仓库根目录现用的 `.trellis/workflow.md`、`.agents/skills/trellis-channel/`、`.claude/skills/trellis-channel/`、`.codex/`、Hook 或代理配置。
- 不修改 `docs/接入指南.md`、`tools/install-embedded-c-overlay.ps1`、README、`TEMPLATE-CONTENTS.md`，也不实现版本识别、1.0 迁移、升级补丁或发布版本变更。这些安装、升级和接入交付全部属于子任务 2。

### R2. 完整 Skill 覆盖层与平台分层

- 模板补齐完整的 `.agents/skills/trellis-channel/` 与 `.claude/skills/trellis-channel/` 文件树，保留命令参考、worker、workflow、forum 和故障诊断等现有基础能力，不能只复制本次新增段落。
- 两套 Skill 中跨平台、跨 provider 的 Channel 命令、事件和 worker 生命周期规则保持同路径正文一致，便于后续统一升级。
- Codex 主会话专属的 `exec_command`、`write_stdin`、`yield_time_ms` 和终端 `session_id` 编排放在模板 `.trellis/workflow.md` 的 Codex 范围内，不得写成 Claude Code 主会话的必需流程。
- Claude 或 Codex 均可作为被派发的 worker provider；本任务不定义 Claude Code 作为 dispatcher 时如何管理终端等待。

### R3. 派发与唯一等待流程

- 对实施和审查分别给出可执行示例：每个 worker 工作单元创建一个用途明确的 channel，执行一次 `spawn`，随后只执行一次 `trellis channel wait`。
- `spawn` 使用明确的 `--agent implement|check`、`--provider`、`--as` 和按预计耗时设置的 `--timeout`；示例中的 30 分钟只是可调整值。
- `wait` 使用 `--as main`、`--from <worker>` 和 `--kind done,error` 等终止事件过滤。正常等待不得依赖自定义 tag、progress 或完整消息流。

### R4. Codex 终端 session 复用

- Codex 主会话通过 `exec_command` 在 PowerShell 启动唯一的 `trellis channel wait`，首次使用短 `yield_time_ms` 以取得即时结果或运行中的 `session_id`。
- 若返回 `session_id`，后续工具动作只对该 ID 调用 `write_stdin`。单次等待窗口以当前运行时工具 schema 为准，可在预计 worker 耗时较长时使用其允许的最大值；若仍在运行，继续复用同一 ID。
- 在该 wait session 结束前，不为同一 worker 重建 channel 或 wait 进程，不运行 `trellis channel list --all`、`messages --kind progress`、`messages --include-progress`、`plan.py status` 等观察命令，也不继续其他任务处理。用户中断、wait 超时或明确失败属于异常处理入口。
- worker 发布 `done` 或 `error` 后，wait 进程退出；Codex 主会话此时恢复处理，并只读取判断下一步所需的最终结果。

### R5. 兼容性与验证

- 不改变 Trellis Channel CLI、事件格式、provider adapter、任务状态机或 worker runtime 实现。
- 模板契约测试必须覆盖完整 Skill 文件树、两套公共内容同步、Codex 专属范围、唯一 wait、同一 session 复用和禁止进度轮询等规则。
- 本任务实施后执行项目规定的相关 Python 单测、Python 语法检查和 `git diff --check`；构建、部署和硬件验证按仓库事实报告为 `not applicable`。
- 审查制度采用 `standard`：实施完成后进行一次独立 affected-scope 审查，覆盖本任务完整 diff、直接受影响的模板/平台契约、相关测试与全部验收项，不执行 full-scope（全盘）审查，也不扩展到无影响证据的仓库区域。阻塞问题必须修复；修复后由主会话重跑受影响检查，只有任务范围发生实质变化时才重新派发完整独立审查。

## Acceptance Criteria

- [ ] 所有实际变更均位于 `templates/embedded-c-overlay/`；根目录现用 Trellis 工作流、接入指南、安装脚本和升级逻辑没有变化。
- [ ] 模板包含完整的 `.agents/skills/trellis-channel/` 与 `.claude/skills/trellis-channel/` 文件树，而不是仅包含本次规则片段。
- [ ] 两套 Skill 的公共文件逐字节一致，并清楚描述一次 spawn、一次 wait、终止事件和 progress 的诊断边界。
- [ ] 模板 `.trellis/workflow.md` 将 `exec_command`、`write_stdin`、`yield_time_ms`、同一 `session_id` 复用及暂停其他工具动作明确限定为 Codex 主会话流程。
- [ ] 实施和审查各有一条 PowerShell 可解释的标准示例，timeout 可调整，且区分 Channel CLI 总 timeout 与 Codex 单次读取窗口。
- [ ] 正常等待流程明确禁止重复 wait、额外同类 channel、progress/完整聊天轮询和执行计划状态查询；异常诊断与正常等待分开。
- [ ] 契约测试可检测 Skill 文件缺失、公共镜像漂移、Codex 规则越界或错误的轮询示例。
- [ ] standard 审查在实施完成后执行一次独立 affected-scope 检查，覆盖本任务完整 diff、直接受影响的平台分层与模板契约、相关测试和所有验收项；提交前不执行 full-scope（全盘）审查。

## Out Of Scope

- `docs/接入指南.md`、README 和模板目录清单的更新。
- `tools/install-embedded-c-overlay.ps1` 的修改，以及任何首次安装或既有 1.0 项目的升级、备份、冲突和回滚机制。
- TrellisForge 1.1 版本发布与子任务 2 的详细 PRD。
- Claude Code 主会话的派发、等待和终端 session 管理流程。
- 修改上游 Trellis 包或本仓库自身运行中的 Trellis 工作流。

## Deferred To Child Task 2

子任务 2 在子任务 1 完成后再规划，负责接入指南、安装脚本、模板目录说明、TrellisForge 1.1 版本升级，以及为已安装 1.0 的下游项目提供版本识别、差异检测、用户定制保护、Git 元数据备份、冲突提示、逐项迁移、回滚和升级后验证方案。子任务 1 的实施 agent 不得提前处理这些文件或能力。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
