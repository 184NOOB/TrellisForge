# Trellis Channel 上下文与等待优化实施计划

## 实施前条件

- [ ] 用户已审查并明确批准最新规划摘要；批准前不得运行 `task.py start` 或修改模板功能文件。
- [ ] 将本子任务绑定为本会话唯一下一步活动任务，确认来源为精确 `session:*` 指针且状态为 `planning`；启动后才进入 `in_progress`。
- [ ] 读取 `prd.md`、`design.md`、本文件、`implement.jsonl`、`check.jsonl` 及其中列出的全部 Spec。
- [ ] 用 `git status --short` 记录并保护其他任务已经产生的修改；本任务功能写入只允许位于 `templates/embedded-c-overlay/`。

## 实施批次

### 1. 建立 Channel 上下文合约测试

- [ ] 扩展模板 `test_trellis_channel_contract.py`，先锁定标准 Implement/Check/Parallel Reviewers 示例不得包含任务正文 `--file` / `--jsonl`。
- [ ] 断言 brief 包含 `Active task`、角色对应 manifest 和上下文预检指令。
- [ ] 断言 Implement/Check Agent 卡具备批量读取、工作区边界、失败 `error` 报告和首次工作前门禁，且成功路径不发送单独回执或文件列表。
- [ ] 保留公共 Skill 镜像、一次 spawn/一次 wait 和禁止正常 progress 轮询的现有断言。
- [ ] 运行该测试文件，确认新断言在实现前按预期失败，且失败点对应本任务契约。

### 2. 更新 Implement/Check Channel Agent 卡

- [ ] 在模板 `.trellis/agents/implement.md` 中定义活动任务解析、`implement.jsonl` 解析、任务文档/Spec/Research 批量读取和 fail-closed 预检顺序。
- [ ] 明确正常加载成功后静默进入工作，不发送单独 Channel 回执、文件列表或内容指纹。
- [ ] 失败时使用现有 `error` 终态报告活动任务、manifest、失败路径、`missing|unreadable|invalid|outside-workspace` 类型和阻塞原因，并在首次交付写入前终止。
- [ ] 在模板 `.trellis/agents/check.md` 对称实现 `check.jsonl` 门禁，并把首次工作边界定义为查看任务 diff、正式审查或自修复之前。
- [ ] 保留两个 Agent 的执行计划/审查 profile、禁止提交和 Channel 终止契约，不引入 Codex 主会话工具术语。

### 3. 更新标准派发与显式快照文档

- [ ] 修改 `.agents/skills/trellis-channel/references/workflows.md` 的 Standard Implement/Check 示例：spawn 只保留 Agent/provider/as/cwd/timeout，brief 负责活动任务和 manifest 定位。
- [ ] 对 Parallel Reviewers 的任务型 Check 示例应用相同主动读取默认值；brainstorm、forum、one-shot 等非标准任务场景按需保留显式注入。
- [ ] 保持现有 Channel 消息投递语义，不借本任务修改 delivery mode 或 worker 生命周期。
- [ ] 修改 `references/workers.md`，将 `--file` / `--jsonl` 定义为保留的显式 system-prompt 快照能力，并清楚说明共享工作区 Implement/Check 默认由 Agent pull。
- [ ] 同步 `.claude/skills/trellis-channel/` 镜像，确保全部公共文件逐字节一致；不修改 CLI 命令参考中真实存在的参数签名。

### 4. 固化 Codex 五分钟等待窗口

- [ ] 更新模板 `.trellis/workflow.md` 的 `[Codex]` 唯一等待块：首次 `exec_command` 使用短窗口，取得 `session_id` 后每次 `write_stdin` 明确固定 `yield_time_ms=300000`。
- [ ] 明确五分钟只是单次读取上界，进程提前退出应立即返回；窗口到期但 wait 仍运行时继续复用同一 ID。
- [ ] 明确正常路径禁用 `30000` 等短周期读取，只有诊断/交互且当轮说明原因时例外。
- [ ] 保持 `done/error`、CLI 总超时 124、进程失败和用户中断边界，以及等待期间不并行处理其他任务的既有规则。
- [ ] 扩展合约测试，断言确切值 `yield_time_ms=300000`，并拒绝正常规则中的短 `write_stdin` 窗口。

### 5. 跨文件契约与回归检查

- [ ] 扫描模板所有 `trellis channel spawn` 示例，确认只有任务型 Implement/Check 默认派发移除全文注入，显式快照场景仍有准确说明。
- [ ] 检查公共 Skill 不含 `exec_command`、`write_stdin`、`yield_time_ms`、`session_id`，这些术语只存在于 workflow `[Codex]` 块。
- [ ] 检查 Agent 卡、workflow、Skill 示例和测试对 manifest 文件名、读取顺序、失败报告和写入前门禁保持一致。
- [ ] 确认根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 没有因本任务发生功能性修改；其他任务已有改动按基线保留。

### 6. 全量验证

- [ ] 运行模板单元测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 运行仓库自用 Trellis 回归测试：

  ```powershell
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 检查模板 Python 语法：

  ```powershell
  Get-ChildItem templates/embedded-c-overlay/.trellis/scripts,templates/embedded-c-overlay/.claude/hooks,templates/embedded-c-overlay/.codex/hooks -Recurse -Filter *.py -File |
    ForEach-Object { python -m py_compile $_.FullName }
  ```

- [ ] 运行 `git diff --check`，并核对任务范围内模板文件换行与两份公共 Skill 镜像一致。
- [ ] 报告构建、部署和硬件验证为 `not applicable`：本仓库不产出固件、可执行产品或硬件目标。

### 7. 审查与交付

- [ ] 按 PRD 的 `Review level: standard` 对完整任务 diff 执行一次独立 affected-scope 审查，覆盖 Agent 卡、公共 Skill 镜像、workflow Codex 块、合约测试和所有验收条件。
- [ ] 批量处理审查发现并重跑直接受影响检查；若任务范围、公共契约、验收条件或适用 Spec 实质变化，则旧证据失效并重新审查。
- [ ] 汇总修改文件、上下文加载与等待契约、测试结果、未运行项和剩余风险；不提前更新版本、升级资产、README 或接入指南。
- [ ] 未经用户另行授权不执行 `git add`、`git commit`、推送、合并或历史重写。

## 风险点与回滚点

- 删除标准 spawn 的 `--file` / `--jsonl` 后，brief 的活动任务路径与 manifest 名称成为定位入口；消息投递和 worker 存活判定继续沿用现有 Channel 生命周期。
- Agent 提示只能强制流程契约，不能从机制上证明模型已读取或理解内容；若未来需要强证明，应另行设计确定性加载器或 provider adapter 校验。
- 公共 Skill 有 `.agents` 与 `.claude` 两份镜像，任一处漏改都会触发字节一致性测试。
- 五分钟读取窗口只减少无终态轮询次数，不改变 wait 总超时；不得把 `300000` 写进 Channel CLI `--timeout` 或 worker idle timeout。
- 回滚时分别回退“主动上下文读取”和“Codex 等待窗口”两组模板改动，不覆盖其他任务正在修改的审查等级文件。
