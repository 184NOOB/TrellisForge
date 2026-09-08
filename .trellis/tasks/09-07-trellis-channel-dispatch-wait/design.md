# Trellis Channel 派发与等待流程设计

## 目标与边界

本设计仅针对 Codex 主会话通过 `trellis channel` 派发 Claude/Codex 实施或审查 worker 的场景。这里的 Claude/Codex 指被派发的 worker provider，不代表 Claude Code 主会话也采用本设计。Claude Code 作为 dispatcher 的派发、终端等待和 session 管理流程不在本任务范围内，不能根据本设计推断其行为。

Codex 主会话的核心契约是：一次 worker 工作只启动一个 channel 和一个 wait 进程；wait 进程交给终端后，主会话复用同一个 `session_id` 读取直到终止事件；终止前不执行其他推理、规划、代码阅读或进度查询；收到 `done`/`error` 后才恢复主会话并读取必要结果。

本任务只修改工作流指导、channel 技能参考和必要的文档契约测试。worker 的业务实现、Trellis CLI 的事件存储和 provider 适配器不在范围内。

## 规则分层

### 1. Channel 命令语义层

`trellis-channel` 技能参考文档负责说明跨 provider 可复用的命令和事件语义；其中涉及终端 session 的条目必须显式标注为 Codex 主会话专属：

- 用 `spawn` 启动一个明确 handle 的 `implement` 或 `check` worker；`--timeout` 按预计工作时长设置。
- 只执行一次 `trellis channel wait`，使用 `--from <worker>` 和 `--kind done,error`（必要时可根据任务选择 `turn_finished`），不使用自定义 tag 作为完成信号。
- wait 的 `--timeout` 是 worker 等待总时长；Codex 工具的 `write_stdin` 只是读取同一终端进程的单次等待窗口，两者分开说明。
- Codex 主会话首次 `exec_command` 使用短 `yield_time_ms` 获取结果；若返回 `session_id`，后续只能对该 ID 调用 `write_stdin`。每次窗口遵循运行时工具 schema 当前给出的范围上界，未完成时继续复用 ID。该条不适用于 Claude Code 主会话。
- 只有终止事件到达后，才按需用一次受限的 `messages --from <worker> --last 1 --raw`（或等效最终结果读取）获取结论；不得把完整 progress/聊天流注入主会话。

跨 provider 的 spawn/wait/终止事件规则放入 `.agents/skills/trellis-channel/references/workflows.md` 和 `workers.md`，并同步到 `.claude/skills/trellis-channel/references/`。Codex 专属的 `exec_command`/`write_stdin` 编排只放在 Codex 主会话可见的工作流提示中；Claude 镜像不得把它描述成 Claude Code 主会话的必需流程。命令参考中的 `wait`、事件 kind 和 timeout 说明只补充与上述契约直接相关的边界，避免重复写多套 host-specific 流程。

### 2. 主会话状态层

`.trellis/workflow.md` 的 Codex 路由和 Codex inline 状态提示负责约束 Codex 主会话行为：

- 派发后立即进入唯一 wait 进程的等待阶段。
- wait 进程运行期间暂停主会话的其他推理、规划、代码阅读、`channel list/messages` 进度观察和 `plan.py status` 查询。
- 首次 `exec_command` 返回 session 后，循环调用同一 `write_stdin`，直到 wait 退出；不重新执行 wait，不新建同类 channel。
- wait 收到终止事件并退出后恢复思考，读取最小必要最终结果，再依据结果进入修复、复审或下一阶段。

该层是主会话生命周期规则，不把等待责任交给 worker，也不要求 hook 维护终端 session 状态。

### 3. 平台同步层

`.agents/skills/trellis-channel/` 作为共享技能内容的编辑基准；`.claude/skills/trellis-channel/` 保持同路径同正文镜像。两套目录只同步 provider-neutral 的 channel 语义和明确的范围声明；Codex 专属终端编排不得因镜像而被解释为 Claude Code 主会话契约。两套目录的对应文件仍需在实现后逐文件比较，确保镜像没有意外漂移。

`.trellis/agents/check.md` 和 `implement.md` 继续只描述 worker 角色与执行协议；不把主会话的 wait 调度规则复制到 worker role card，避免 worker 被错误要求管理自己的 dispatcher session。

## 行为状态与异常

正常状态序列为：

```text
spawned worker
    -> one channel wait process
    -> exec_command returns session_id (or wait completes immediately)
    -> repeated write_stdin on the same session_id
    -> done/error/killed/timeout
    -> wait process exits
    -> main session resumes and reads bounded final result
```

- wait 返回 timeout（CLI 退出码 124）时，主会话不得另起第二个 wait 观察同一工作；应按后续设计的超时/恢复处理决定是否终止 worker、重派或回到任务规划。
- worker 出现 `error` 或 `killed` 时，仍由同一个 wait 进程收集终止事件；主会话在进程退出后再处理失败。
- 只有确有故障证据时才进入 `trellis channel` 的诊断路径；诊断命令不属于正常等待循环，且应限制输出范围。
- 运行时工具 schema 变化时，以当前 schema 为准；文档不得把某个 `write_stdin` 窗口写成永久硬限制。

## 数据与兼容性

不改变 Trellis Channel 事件格式、CLI 参数、worker agent card、任务状态或执行计划状态机。变更只增加 Codex 主会话可读的流程约束与 provider-neutral 示例，因此兼容已有 channel、任务和下游安装结果。旧文档中允许重复 wait 或 progress 轮询的示例必须被替换或明确标为诊断用途，防止规则冲突。

## 验证策略

- 文档契约测试批量检查共享技能与 Claude 镜像存在 provider-neutral 关键规则、示例包含终止事件等待、正常路径没有 `include-progress`/重复 wait 指导，并确认两套公共文件正文一致；另行检查 Codex 专属 `exec_command`/`write_stdin` 规则只出现在 Codex 主会话工作流范围，未被定义为 Claude Code 主会话要求。
- 运行项目既定 Python 单测、Python 语法检查和 `git diff --check`。
- 不运行虚构的构建、typecheck、固件或硬件命令；这些类别按项目规则报告为 `not applicable`。

## 回滚

若文档契约测试或 strict 审查发现规则与现有 Trellis CLI 语义不符，回滚对应文档批次并保留任务 PRD；不得通过修改 CLI 或 hook 绕过问题。平台镜像出现差异时，恢复到编辑基准文件的同一版本后重新批量同步。
