# Trellis Channel 上下文与等待优化技术设计

## 目标与架构边界

本设计优化下游模板中由主会话编排的 Trellis Channel Implement/Check 工作单元，包含两条相互独立但共同降低无效 token 消耗的路径：

1. Channel worker 的 system prompt 只保留稳定协议和角色卡，任务与 Spec/Research 正文由 worker 在收到 brief 后从共享工作区主动读取。
2. Codex 主会话启动唯一 `trellis channel wait` 后，首次短窗口只用于取得即时终态或 `session_id`；后续正常读取统一使用 `write_stdin(..., yield_time_ms=300000)` 并复用该 ID。

功能修改只落在 `templates/embedded-c-overlay/`。不修改根目录自用 Trellis、全局 `@mindfoldhq/trellis` CLI、Claude/Codex 工具实现、Channel event schema、provider adapter 或任务生命周期。

```text
主会话
  | create + spawn（不传任务正文 --file/--jsonl）
  | send brief（Active task + manifest + 本轮目标/范围/验证）
  v
Channel worker system prompt
  = Channel 协议 + Agent 角色 + 安全边界 + 上下文读取门禁
  |
  | 批量预检并读取共享工作区当前文件
  | 成功时静默进入实施、审查或自修复
  | 失败时发送 error（路径 + 原因），不开始工作
  v
done/error

Codex 主会话
  exec_command(wait, short yield)
       |-- 即时退出 --> 处理终态
       `-- session_id --> write_stdin(same id, 300000) ... 直到退出/中断
```

## 混合上下文加载契约

### System prompt 保留内容

`.trellis/agents/implement.md` 和 `.trellis/agents/check.md` 的 Markdown 正文仍由 `--agent` 加载到 worker system prompt，其中保留：

- Channel worker 身份与通信方式；
- Agent 职责、禁止操作和写入边界；
- manifest 与任务文档的必读顺序；
- 上下文预检、批量读取和失败报告契约；
- 实施执行计划或审查 profile 契约；
- `done/error` 终止报告规则。

这些内容稳定且应具有最高指令优先级。任务正文不进入该层。

### Brief 定位内容

标准 Implement/Check 派发从 `spawn` 命令删除任务相关的 `--file` 和 `--jsonl` 参数。首次定向 brief 必须以 `Active task: <task-path>` 开头，并包含：

- `Context manifest: implement.jsonl|check.jsonl`；
- 本轮角色、目标、范围和明确非目标；
- 任务或工程已经规定的验证命令；
- “先完成上下文预检，失败则报告 error，成功后才可写入/审查”的提醒。

brief 不复制 PRD、design、implement、Spec、Research 或 diff 正文。消息发送和 worker 存活判定沿用现有 Channel 生命周期，本任务不改变 delivery mode 或投递协议。

### Worker 主动读取顺序

Implement worker：

1. 解析并规范化活动任务目录，确认其位于当前工作区 `.trellis/tasks/` 内。
2. 批量检查 `implement.jsonl`、`prd.md` 及可选 `design.md`、`implement.md`。
3. 逐行解析 `implement.jsonl`；无 `file` 字段的 seed/comment 行跳过，有效条目的相对路径必须保持在工作区内。
4. 批量读取 manifest 中的全部 Spec/Research 文件和全部存在的任务文档。
5. 全部读取成功后才进入 execution-plan 和交付写入流程；成功时不发送单独的读取回执。

Check worker 使用相同流程，但 manifest 为 `check.jsonl`；加载完成后才可查看任务 diff、开始审查或执行自修复。

任务文档的必需性遵循现有任务模型：`prd.md` 与对应 manifest 必需，`design.md` 和 `implement.md` 在存在时必读。规划 readiness gate 仍负责保证复杂任务在启动前具备完整规划产物和真实 manifest 条目，Channel 侧不重新定义该策略。

### 预检与信任边界

本任务不新增 Python 上下文加载脚本。worker 使用自身的文件读取/结构化解析能力完成预检，并遵循 Agent 卡中的 fail-closed 契约：

- 活动任务目录必须解析到 `<workspace>/.trellis/tasks/**`；
- manifest 的每个有效 `file` 路径必须解析在当前工作区内；
- `type=file` 必须是可读文件；`type=directory` 必须是可读目录，并读取该目录中任务所需的材料；
- JSON 无效、类型非法、路径越界、文件缺失、读取失败或任何有效条目未加载，均在交付文件写入前结束为 `error`；
- 不允许把失败条目降级为警告后继续。

现有 `task.py validate` 和 readiness gate 保持规划期门禁角色，但不是 worker 已经实际读取文件的证明。Agent 卡的运行时预检补足 spawn 后的执行时保证，同时避免把本任务扩展到非 Channel 原生子代理的 hook。

## 读取成功与失败报告

加载成功后，worker 不发送单独的 Channel 消息或文件列表，直接进入角色对应的实施或审查流程。成功回执由 worker 自报，无法独立证明文件确实被读取或内容得到理解，因此不把它包装成审计证据，也不为它增加消息和 token 开销。

加载失败时沿用现有 `error` 终态，至少报告角色、活动任务、manifest、失败文件相对路径、失败类型和原因。失败类型为 `missing|unreadable|invalid|outside-workspace`；不得附带文件正文、摘要、大小、时间或哈希，也不得在发送错误前开始实施、查看任务 diff 或自修复。

该设计保留的是 Agent 层的 fail-closed 执行契约，而不是确定性运行时证明。静态合约测试只能确认 Agent 卡明确要求读取和失败阻塞；如果未来需要机器可验证的读取证明，应另设确定性加载器或修改 provider adapter，不应依赖 worker 自报消息。

## Codex 唯一等待会话契约

该契约只写入 `.trellis/workflow.md` 的 `[Codex]` 编排块，公共 `trellis-channel` Skill 和 Channel worker Agent 卡不得出现 `exec_command`、`write_stdin`、`yield_time_ms` 或 `session_id`。

正常流程：

1. 主会话用一次 `exec_command` 启动唯一 `trellis channel wait ... --kind done,error`，使用短 `yield_time_ms` 获取即时终态或运行中的 `session_id`。
2. 若得到 `session_id`，后续只调用 `write_stdin`，每次固定 `yield_time_ms=300000`，不发送输入字符并复用同一 ID。
3. 工具在 wait 进程提前退出时立即返回；五分钟是单次读取上界，不要求强制等待满五分钟。
4. 五分钟窗口结束且进程仍运行时，继续对同一 ID 使用相同窗口；不得创建新 channel、worker 或 wait。
5. `done/error`、wait 退出码 124、明确进程失败或用户新指令中断时退出正常等待路径。用户中断后按最新请求处理，不自动创建第二个 wait。

`30000` 等短 `write_stdin` 只用于明确说明原因的诊断或交互场景。正常等待期间不为了周期性状态播报缩短窗口，也不运行 Channel list/progress 等旁路轮询。

## 模板修改面

| 文件 | 设计改动 |
|---|---|
| `templates/embedded-c-overlay/.trellis/agents/implement.md` | 增加运行时预检、批量主动读取、失败报告和首次写入门禁 |
| `templates/embedded-c-overlay/.trellis/agents/check.md` | 对称增加 Check 上下文加载门禁，并禁止加载完成前查看 diff、自修复 |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/workflows.md` | 标准 Implement/Check 及并行审查示例改为无全文注入的 brief 定位模式 |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/workers.md` | 区分共享工作区主动读取与显式快照注入，更新审计语义和示例 |
| `templates/embedded-c-overlay/.claude/skills/trellis-channel/**` | 与 `.agents` 公共 Skill 镜像保持逐字节一致 |
| `templates/embedded-c-overlay/.trellis/workflow.md` | 更新 Channel 派发边界，并把 Codex 后续读取窗口固定为 `300000` |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_trellis_channel_contract.py` | 锁定无默认全文注入、主动读取要求、失败门禁、无成功回执、公共镜像和五分钟等待契约 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_subagent_prompt_contract.py` | 如现有 Agent 卡合约测试职责适合，补充 Channel Agent 加载门禁断言；否则集中在 Channel 合约测试 |

`command-reference.md` 继续准确描述 CLI 的 `--file` / `--jsonl` 能力，不因默认工作流改变而删除参数。brainstorm、forum 和 one-shot 的显式上下文示例不属于 Implement/Check 标准派发，可继续使用快照注入。

## 测试设计

`test_trellis_channel_contract.py` 扩展为静态模板契约测试，不启动外部 provider：

1. 两份公共 Skill 树仍逐字节一致。
2. Standard Implement/Check 和 Parallel Reviewers 的 spawn 示例不含 `--file` / `--jsonl`，brief 含活动任务与对应 manifest 定位。
3. Workers 文档仍定义 `--file` / `--jsonl` 通用显式快照能力，同时将共享工作区 Implement/Check 标为主动读取默认值。
4. 两个 Channel Agent 卡包含 manifest、任务文档、工作区边界、失败 `error` 契约和首次工作门禁；成功路径不得要求单独回执或文件列表。
5. workflow `[Codex]` 块包含确切的 `yield_time_ms=300000`、同一 `session_id` 复用和读取窗口/总超时区分；公共 Skill 与 worker 卡仍不得泄漏 Codex 工具术语。
6. 标准示例继续满足一个 work unit 一次 spawn、一次 wait，且不加入 progress 轮询。

全量验证继续运行模板 Python 单测、根目录回归测试、模板 Python 语法检查和 `git diff --check`。本仓库无构建、部署或硬件目标，对应类别为 `not applicable`。

## 兼容性、发布与回滚

- 这是模板默认编排行为变化，不移除 CLI 参数；依赖 `--file` / `--jsonl` 的用户手工命令继续有效。
- Channel worker 与工作区共享是主动读取的前提；无法访问源文件或需要不可变快照时继续显式注入。
- 不迁移既有任务或 manifest，不新增任务字段和持久化审计文件。
- Agent 主动读取契约不能提供机器可验证的读取或理解证明；验收映射与独立审查继续承担正确性保证。
- 若主动读取契约回归，可只回退 Agent 卡和标准派发示例；若等待规则回归，可独立回退 workflow 的 Codex 块。两条改动不互相绑定，也不得整体重置用户工作树。
- 版本、历史对象、迁移链、README 和接入指南由父任务固定收尾子任务统一处理。
