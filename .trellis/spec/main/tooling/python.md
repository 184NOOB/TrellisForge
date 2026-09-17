# Python 工作流脚本

## 适用范围

Python 代码主要位于 `.trellis/scripts/`、`.claude/hooks/` 和 `.codex/hooks/`，用于任务生命周期、执行计划、上下文注入和回归测试。脚本使用 UTF-8，兼容 Windows PowerShell 调用方式。

## 实际模式

- 共享逻辑放在 `.trellis/scripts/common/`，入口脚本负责参数解析和调用；例如 `task.py` 使用任务存储层，执行计划由 `plan.py` 调用 `common/execution_plan.py`。
- 任务状态、执行计划和审计日志通过已有 CLI 推进，不直接手工改写状态字段。活动任务隔离由 `common/active_task.py` 和 `common/task_store.py` 维护。
- Hook 读取标准输入 JSON，输出可注入上下文；不要在 Hook 中执行产品构建或隐式修改工作树。
- 文本文件显式使用 UTF-8 读写并保留简体中文内容；命令示例必须能在 Windows PowerShell 中解释。

## Scenario: 模板执行计划 live 指针与 sequel

### 1. Scope / Trigger

- Trigger: 下游模板新增 `plan.py sequel` 与 live 计划解析。任务可顺序持有多份闭环计划；命令签名、指针 JSON、冻结目录和错误矩阵都是跨层合同（CLI / `execution_plan.py` / workflow / 各平台 Agent / Hook）。
- 合同目前只存在于 `templates/embedded-c-overlay/`。根目录自用 `.trellis/scripts/` 尚未同步，不得把模板行为写成根目录已经具备的事实。

### 2. Signatures

- `python .trellis/scripts/plan.py [--task <path>] sequel --reason "..."`
- 现有 `validate|status|start|record|done|block|revise` 全部只作用于 live plan。
- `common.execution_plan.resolve_live_plan(task_dir) -> tuple[int, Path]`
- `common.execution_plan.cmd_sequel(repo_root, task_dir, reason) -> str`

### 3. Contracts

- 无 sequel 时（第 1 份 / 旧布局）：任务根 `execution-plan.json` 是真实 schema-3 计划，含 `tasks`。
- 有 sequel 时：任务根 `execution-plan.json` 仅为指针 `{"schema": 3, "live": N}`，不含 `tasks`。live 文件在 `plans/<N>/execution-plan.json` 与 `plans/<N>/execution-events.jsonl`；对应 `final-report.md` 也在该目录。
- `plan_sequel` 事件写入**新** live 账本，字段 `from`、`to`、`reason`。冻结账本只读，不再追加。
- Hook / OpenCode 插件只展示 live 状态，不推进状态，也不复制路径常量。

### 4. Validation & Error Matrix

- `--reason` 为空 -> 拒绝 sequel
- live 仍有未完成 phase，或缺少 terminal report / `plan_completed` -> 拒绝 sequel
- 指针缺 `live`、`live < 1`、混入 `tasks`、指向缺失目录、或 `plans/<n>` 自身又是指针 -> 全部变更命令 fail closed
- 冻结目录上的 `start|record|done|block|revise|validate` -> 拒绝
- 把已完成 report 改成普通阶段 -> `validate` 仍拒绝（防伪史，不是 sequel 通道）
- `revise` -> 只重开当前 live，不创建 sequel

### 5. Good/Base/Bad Cases

- Good: 旧单文件任务无需迁移即可 `validate` / `status` / 推进。
- Base: 完成后 `sequel` 把第 1 份冻进 `plans/1/`，live 指针变为 2；第三次 `sequel` 得到 live 3。
- Bad: 计划未完成就 `sequel`；手改已完成 report 冒充下一轮；损坏指针后继续 `start`。

### 6. Tests Required

- 模板 `test_execution_plan.py`：旧单文件兼容、完成后 sequel 冻结、未完成拒绝、第三次 sequel、损坏指针 fail closed、`status` 只详列 live、`revise` 不创建 sequel、已完成 report 仍不可改写、sequel 回滚清掉空的 `plans/1/`。
- 模板 `test_small_patch_and_sequel_contract.py`：workflow / implement 协议含用户声明优先的小修门槛、阻塞修复默认小修、以及 `sequel` 完成态出口。

### 7. Wrong vs Correct

#### Wrong

完成后把 `report` 改成普通阶段再 `revise`，或让 `plan.py` 自动判断一次编辑算不算小修。

#### Correct

小修（用户明确说小修/不走 `plan.py`，或满足四条客观门槛；阻塞修复默认如此）不碰已完成计划文件。同一需求的大修或过多冗杂复杂的阻塞修复才 `plan.py sequel --reason "..."`。

## 测试与示例

- 执行计划状态机的行为测试在 `.trellis/scripts/tests/test_execution_plan.py`。
- 规划门禁和会话隔离分别由 `.trellis/scripts/tests/test_planning_gate.py`、`.trellis/scripts/tests/test_active_task_session_isolation.py` 覆盖。
- 代理提示与 Hook 合同由 `.trellis/scripts/tests/test_subagent_prompt_contract.py` 覆盖。

## 禁止事项

- 不用字符串拼接替代 JSON/结构化解析。
- 不吞掉异常或把不可执行的检查伪造为通过；应报告 `not applicable`，必要时用 `plan.py block/revise`。
- 不提交 `__pycache__`、`.pyc` 或 `.pyo`；模板安装器会主动拒绝这些缓存。

## 常见错误

- **Windows 下 `task.json` 变 CRLF 触发 `git diff --check` 尾随空白**：`common/io.py` 的 `write_json` 用 `os.fdopen(fd, "w", encoding="utf-8")` 写文件（未传 `newline=`），Windows 文本模式把 `\n` 转成 `\r\n`，因此 `task.py`/`plan.py` 推进状态落盘的 `task.json` 等 JSON 会成为 CRLF。仓库 `core.autocrlf=false` 且 `.gitattributes` 无 JSON 换行规则，`git diff --check` 会把 CRLF 判为 `trailing whitespace` 报错。提交前若在 `task.json` 上遇到该报错，先将文件规范化为 LF（`git add --renormalize` 或脚本转 LF）；根治需给 `write_json` 传 `newline="\n"`，属根级工具修复、需单独任务授权。
