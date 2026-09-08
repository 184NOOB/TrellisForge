# 规范 Trellis Channel worker 派发与等待流程

## Workflow Settings

- Review level: strict

## Goal

为 Codex 主会话建立统一的 Trellis Channel worker 派发与等待行为，适用于实施 worker 和审查 worker。worker 运行期间主会话保持安静，只保留一个可复用的等待进程；worker 发布完成事件后，主会话再恢复思考并读取必要的最终结果，避免多次启动等待命令和反复注入进度造成 token 浪费。

## Background And Evidence

- Trellis Channel 文档提供的 dispatcher 模式是 `spawn` 后使用 `trellis channel wait <channel> --as main --from <worker> --kind done` 等待终止事件。
- `progress` 事件是过程流，不是完成信号；正常流程不应通过 `list` 或 `messages --kind progress` 轮询 worker 状态。
- Codex 的 `exec_command` 首次可以使用短 `yield_time_ms`；若命令仍在运行会返回 `session_id`。后续应使用同一个 `session_id` 调用 `write_stdin`。当前内部工具接口对空轮询的 `yield_time_ms` 标注范围为 5000–300000 ms（范围上界约 5 分钟）；这是单次工具调用的等待窗口，不是 worker 或终端进程的总运行时长，也不是公开文档承诺的永久硬限制，实际执行应以当时工具 schema 为准。公开 OpenAI 文档未找到该内部接口的独立说明。

## Requirements

- **派发**：主会话为一次实施或审查创建一个明确用途的 channel，启动一个明确 handle 的 worker，传入对应 `--agent implement` 或 `--agent check`、provider、角色和可按预计耗时调整的 CLI `--timeout`。
- **首次等待**：worker 启动后，主会话只执行一次 `trellis channel wait`，过滤目标 worker 的 `done`（必要时同时处理 `error`）事件；通过 `exec_command` 首次仅短暂等待，例如 `yield_time_ms=1000`。
- **session 复用**：首次等待返回 `session_id` 时，主会话必须使用 `write_stdin` 连接该 ID 继续等待；单次等待窗口按当前工具 schema 设置，当前说明的范围上界约为 300 秒。若仍未完成，继续对同一 ID 调用 `write_stdin`，不得重新执行 `trellis channel wait`，不得创建新的等待进程。
- **完成恢复**：worker 发布 `done` 后，`trellis channel wait` 退出，随后 `write_stdin` 返回完成输出；主会话才恢复思考，并按需读取一次最终结果。读取不得扩展为完整聊天记录或持续 progress 监控。
- **等待期间禁止行为**：等待进程运行期间，主会话暂停其他推理、规划、代码阅读和进度查询；不为同一 worker 重复创建 channel 或 wait 进程，不反复运行 `trellis channel list --all`、`trellis channel messages ... --kind progress`、`messages --include-progress`、`plan.py status` 等进度观察命令，也不把 worker 的完整对话持续读入主会话。只有 wait 收到终止事件后，主会话才恢复思考并读取必要的最终结果。
- **流程对称性**：以上约束同时适用于实施流程和审查流程；差异仅限 worker 的 agent/角色和具体任务内容。
- **主会话范围**：本子任务只规范 Codex 主会话作为 dispatcher 时的流程；Claude Code 作为主会话的派发、等待和终端 session 管理流程不在范围内，不能根据本任务推断其行为。被派发的 worker provider 仍可为 Claude 或 Codex。
- **超时策略**：channel CLI 的 timeout 由主会话依据 worker 预计耗时设置，不固定为 30 分钟；Codex 工具层当前说明的约 300 秒只是单次 `write_stdin` 等待窗口范围上界，不应被误当作 worker 总 timeout；实际窗口以运行时工具 schema 为准。
- **文档与提示要求**：后续实现应把上述流程写入主会话可见的 Trellis 工作流、技能、代理提示或等效指导位置，并提供能阻止错误流程的清晰规则；本 PRD 不预先指定具体文件，交由设计阶段根据仓库现有分层确定。

## Acceptance Criteria

- [ ] 对实施和审查各有一条可复现的标准流程，均包含一次 `spawn`、一次 `trellis channel wait` 和同一 `session_id` 的连续 `write_stdin` 等待。
- [ ] 标准流程明确首次 `exec_command` 使用短 `yield_time_ms`，后续单次 `write_stdin` 遵循运行时工具 schema（当前说明范围上界约 300 秒），未完成时复用同一 session ID。
- [ ] 标准流程明确 worker 发布 `done` 后才恢复主会话思考，并说明最终结果读取边界。
- [ ] 标准流程明确禁止重复执行 `trellis channel wait`、创建多个同类等待进程、轮询完整 progress/聊天记录和在等待期间运行计划状态查询。
- [ ] 文档或提示中明确 timeout 可按预计耗时调整，且把工具层等待窗口与 worker 总 timeout 区分开。
- [ ] 规则按平台分层：公共 `trellis-channel` skill 只描述跨平台的 channel/事件语义；`exec_command`、`write_stdin`、`yield_time_ms` 和主会话暂停/恢复只作为 Codex 主会话定制，不得写成 Claude Code 主会话的必需流程。
- [ ] 若修改 `.agents/skills/trellis-channel` 的公共内容，必须同步 `.claude/skills/trellis-channel` 的对应公共文件并验证逐字节一致；Codex 专属内容不得因同步镜像而扩展到 Claude Code 主会话。
- [ ] 相关测试或静态验证能够证明规则文案与示例命令保持一致；不可适用的构建、部署或硬件验证类别按项目规则报告为 `not applicable`。

## Planning Convergence

- Status: pending
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: no

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
