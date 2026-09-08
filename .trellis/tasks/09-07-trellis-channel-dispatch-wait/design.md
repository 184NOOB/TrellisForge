# Trellis Channel 派发与等待流程设计

## 设计目标

本设计只改变 TrellisForge 的下游发布模板，并只规范 Codex 主会话通过 `trellis channel` 派发 Claude/Codex 实施或审查 worker 的行为。模板把跨平台 Channel 语义与 Codex 终端编排分开维护，使公共规则可统一同步，Codex 定制也有单独、明确的修改位置。

## 发布与任务边界

子任务 1 的允许修改根为 `templates/embedded-c-overlay/`。仓库根目录现用的 `.trellis/`、`.agents/`、`.claude/` 和 `.codex/` 只作为当前行为与完整 Skill 的参考源，不接受产品修改。

以下交付明确推迟到子任务 2：

- `docs/接入指南.md`、README、`templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 等接入和发布说明；
- `tools/install-embedded-c-overlay.ps1` 及其安装/升级测试；
- 1.0 版本识别、模板差异检测、用户定制保护、备份、冲突处理、逐项迁移、回滚和 1.1 版本发布。

子任务 1 可以新增模板源文件，但不得为了让既有项目立即接收这些文件而修改安装器或编写升级补丁。父任务不会在两个子任务全部完成前把这一中间状态作为完整 1.1 升级交付。

## 模板文件设计

| 模板路径 | 责任 |
|---|---|
| `.agents/skills/trellis-channel/` | 完整的共享 Skill 覆盖层；包含索引及全部 references，承载跨平台 Channel 语义 |
| `.claude/skills/trellis-channel/` | Claude Skill 镜像；公共文件与 `.agents` 对应文件逐字节一致 |
| `.trellis/workflow.md` | Codex 主会话专属的终端 wait/session 编排，以及实施/审查路由入口 |
| `.trellis/agents/implement.md` | Channel implement worker 的完成/失败事件契约，不管理 dispatcher 终端 |
| `.trellis/agents/check.md` | Channel check worker 的完成/失败事件契约，不管理 dispatcher 终端 |
| `.trellis/scripts/tests/test_subagent_prompt_contract.py` | 扩展模板契约检查；必要时可在同目录新增职责单一的测试文件 |

不计划修改 `.trellis/config.yaml`。`channel.worker_guard` 的 idle timeout 和 worker 数量限制与本次 dispatcher 的 CLI timeout/session 复用不是同一问题，改配置会扩大范围且不能解决重复 wait。

## 分层结构

### 公共 Channel 层

模板完整复制现有 `trellis-channel` Skill 的索引、`command-reference.md`、`forum.md`、`progress-debugging.md`、`workers.md` 和 `workflows.md`，再在直接相关的公共参考中加入以下规则：

- 一个 worker 工作单元只有一次 spawn 和一个阻塞 wait；
- `done`/`error` 是正常完成或失败信号，progress 仅用于显式诊断；
- 正常路径不使用 `list`、progress messages 或完整消息流轮询；
- CLI `--timeout` 按 worker 预计耗时设置，不固定为示例值；
- 实施与审查仅在 agent、角色和任务内容上不同。

公共层不提 Codex 工具 API。`.agents` 与 `.claude` 两套对应公共文件保持相同，测试通过路径集合和文件哈希/正文比较防止漏文件与漂移。

### Codex 主会话层

模板 `.trellis/workflow.md` 中现有的 Codex 路由或 `[codex-inline]` 范围承载 Codex 专属规则：

1. 用 `exec_command` 在 PowerShell 中启动唯一的 `trellis channel wait`，首次短暂 yield。
2. 命令未完成并返回 `session_id` 后，只用 `write_stdin` 读取该 session。
3. 每次 `write_stdin` 的等待窗口遵循当时工具 schema；当前上界约 300 秒，窗口结束但进程仍在运行时继续复用同一 ID。
4. wait 进程存活期间，下一次主会话工具动作仍是对同一 session 的 `write_stdin`；不得启动其他任务操作或正常进度查询。用户中断、wait timeout 和明确错误进入异常路径。
5. wait 因 `done`/`error` 退出后，主会话恢复分析并读取最小必要的最终结果。

该规则不能放进公共 Skill 或 worker 角色卡，以免 Claude Code 主会话或 worker 被错误要求使用 Codex 的终端 API。

## 标准流程

实施和审查分别采用唯一 channel 名与 worker handle。下面的角色参数不同，生命周期相同：

```text
create channel
  -> spawn --agent implement|check --provider claude|codex --as <worker>
  -> exec_command: trellis channel wait ... --from <worker> --kind done,error
  -> returns session_id if still running
  -> write_stdin(session_id=<same id>)
  -> repeat write_stdin on <same id> while running
  -> wait exits on done/error/timeout
  -> resume main-session processing
```

示例命令使用 Windows PowerShell 的续行语法，并明确 30 分钟只是示例。`exec_command` 的初次 yield 与后续 `write_stdin` 窗口属于 Codex 工具调用参数，不拼进 shell 命令文本。

## 异常与诊断

- CLI wait timeout 后原进程已经退出，主会话先判断 worker 状态和任务风险，再决定中止、恢复或重新派发；不得把重新 wait 写成无条件循环。
- `error` 或 `killed` 作为终止状态处理，主会话在 wait 退出后分析失败。
- 只有 wait 异常退出、worker 明确失联或用户要求检查时，才进入受限诊断。诊断允许读取必要的 channel 状态，但必须限制事件类型和输出量，且不能伪装成正常等待流程。
- 用户在等待期间发来新指令时，主会话遵循最新用户指令；这是交互中断，不属于后台进度轮询。

## 兼容性与后续升级

本任务只增加模板内容和约束，不改变 Channel CLI 或事件 schema。由于下游 `trellis init` 通常已经生成上游 `trellis-channel`，完整覆盖层可能与用户现有文件冲突，也可能在未来 `trellis update` 时发生上游更新冲突。子任务 2 必须基于文件版本/哈希和用户修改状态设计迁移，不能把子任务 1 的模板文件直接静默覆盖到既有 1.0 项目。

## 验证设计

- 模板 Skill 完整性：验证两套目录包含相同的预期相对路径集合。
- 公共层同步：逐文件比较两套 Skill 的对应内容。
- 平台范围：验证 `exec_command`、`write_stdin`、`yield_time_ms` 和 `session_id` 只在 workflow 的 Codex 范围内构成主会话要求。
- 流程契约：验证实施和审查示例均包含一次 spawn、一次 wait、`done,error`、同一 session 复用，以及正常路径禁止的观察命令。
- 回归验证：运行根目录和模板中适用的 Python 单测、改动涉及的 Python 语法检查及 `git diff --check`。

## 审查策略

本任务采用 `standard` 审查等级。实施完成后派发一次独立 affected-scope 审查，范围限定为本任务完整 diff、直接受影响的模板文件与平台边界、相关测试和全部验收项；提交前不执行 full-scope（全盘）审查。发现阻塞问题后必须修复，由主会话重跑受影响检查；只有修复导致任务范围发生实质变化时，才重新派发完整独立审查。没有 diff、调用关系或验收条件支持的仓库区域不纳入审查。

## 回滚点

完整 Skill 模板、workflow Codex 规则、worker 角色卡和契约测试按独立批次实施。若 standard 范围审查发现公共 Skill 与 Codex 规则混层，回滚对应批次后修正设计；不得通过修改根目录现用工作流、CLI 或安装器绕过问题。
