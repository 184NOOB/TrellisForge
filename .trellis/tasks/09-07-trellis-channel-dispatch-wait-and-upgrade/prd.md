# 规范 Trellis Channel 派发与等待流程并规划 1.1 升级

## Workflow Settings

- Review level: standard

## Goal

建立一套适用于 Codex 主会话通过 Trellis Channel 启动 Claude/Codex worker 进行实施或审查的稳定流程，确保主会话在等待 worker 完成期间只维护一个等待进程，不重复创建等待命令、读取进度或注入子代理完整对话，从而降低 token 消耗并保持主会话的独立判断能力。

父任务同时登记后续的 TrellisForge 1.1 升级工作：升级子任务需要给已经安装 1.0 的 TrellisForge 提供可执行的升级方案，但本轮只记录范围，不编写该子任务 PRD。

## Background And Evidence

- 当前 TrellisForge 版本为 `1.0`，版本事实记录在 `README.md`。
- 仓库内 `trellis-channel` 文档的 dispatcher 模式要求先 `spawn` worker，再用单条 `trellis channel wait` 订阅 worker 的 `done`/`error` 等终止事件；正常等待不依赖反复读取 `list` 或 `messages --kind progress`。
- `progress` 事件用于流式过程信息，属于高噪声事件；最终结果应在等待命令结束后按需读取，而不是持续把子代理聊天记录带回主会话。
- Codex 主会话的 `exec_command` 在短暂首次等待后可能返回 `session_id`；之后应使用同一 `session_id` 调用 `write_stdin` 继续读取。当前内部工具接口对空轮询的 `yield_time_ms` 标注范围为 5000–300000 ms（范围上界约 5 分钟）；这是单次工具调用的等待窗口，不是 worker 或终端进程的总运行时长，也不是公开文档承诺的永久硬限制，实际执行应以当时工具 schema 为准。公开 OpenAI 文档未找到该内部接口的独立说明。
- TrellisForge 的升级维护规范要求升级前运行 `trellis update --dry-run`，采用逐项迁移，不使用整体 `--force` 覆盖项目定制。

## Requirements

- **父任务范围**：维护两个独立子任务及其先后关系。子任务 1 先完成 Trellis Channel 派发/等待流程改动；子任务 2 在子任务 1 完成后再规划和实施，负责将 TrellisForge 升级为 1.1，并提供从已安装 1.0 的 TrellisForge 迁移的方案。
- **子任务 1**：必须把 worker 启动、单一等待进程、同一终端 session 复用、完成后恢复主会话的行为写成可执行要求，并覆盖实施与审查两种 worker 角色。
- **子任务 1 的等待约束**：首次 `exec_command` 只做短等待；若返回 `session_id`，后续只允许对同一 ID 调用 `write_stdin`，单次等待窗口遵循运行时工具 schema（当前标注上限约 300 秒）；未完成时继续复用该 ID，不得重新执行新的 `trellis channel wait`。
- **子任务 1 的主会话约束**：等待进程运行期间，主会话暂停其他推理、规划、代码阅读和进度查询；不创建同类的额外 channel/wait 进程，不轮询 `trellis channel list`、`messages --kind progress` 或执行计划状态，也不把 worker 的完整对话持续读入主会话。只有 wait 收到终止事件后，主会话才恢复思考并读取必要的最终结果。
- **升级子任务登记**：子任务 2 只在本父 PRD 中登记目标、依赖和后续交付，不在本轮填写升级 PRD，也不在本轮设计升级文件或实施升级改动。
- **规划边界**：本轮只创建任务并编写 PRD；不写 `design.md`、`implement.md`，不运行 `task.py start`，不修改产品、模板、Hook、代理或文档代码。

## Acceptance Criteria

- [ ] 父任务 `task.json` 关联两个子任务，且依赖关系明确为“子任务 1 完成后再处理子任务 2”。
- [ ] 父 PRD 明确记录子任务 1 的流程目标、禁止行为和等待 session 复用规则。
- [ ] 父 PRD 明确记录子任务 2 的 TrellisForge 1.1 目标以及为已安装 1.0 的 TrellisForge 提供升级方案的后续范围。
- [ ] 子任务 1 存在独立 PRD，包含可观察的派发、等待、完成恢复和反例验收条件。
- [ ] 子任务 2 保持为已创建但未规划的占位任务；本轮不新增其需求、设计或实施文件内容。
- [ ] 本轮三个任务均保持 `planning` 状态；不执行 `task.py start`，不产生产品代码变更。

## Out Of Scope

- 本轮不实现任何 Trellis Channel、Hook、代理或文档修改。
- 本轮不验证具体 provider 的实际启动时延，也不承诺固定的 channel CLI timeout；timeout 由后续实施时按 worker 预计耗时设置。
- 本轮不编写或审批 TrellisForge 1.1 升级子任务 PRD，不执行 `trellis update` 或迁移。

## Planning Convergence

- Status: pending
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: no

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
