# Python 工作流脚本

## 适用范围

Python 代码主要位于 `.trellis/scripts/`、`.claude/hooks/` 和 `.codex/hooks/`，用于任务生命周期、执行计划、上下文注入和回归测试。脚本使用 UTF-8，兼容 Windows PowerShell 调用方式。

## 实际模式

- 共享逻辑放在 `.trellis/scripts/common/`，入口脚本负责参数解析和调用；例如 `task.py` 使用任务存储层，执行计划由 `plan.py` 调用 `common/execution_plan.py`。
- 任务状态、执行计划和审计日志通过已有 CLI 推进，不直接手工改写状态字段。活动任务隔离由 `common/active_task.py` 和 `common/task_store.py` 维护。
- Hook 读取标准输入 JSON，输出可注入上下文；不要在 Hook 中执行产品构建或隐式修改工作树。
- 文本文件显式使用 UTF-8 读写并保留简体中文内容；命令示例必须能在 Windows PowerShell 中解释。

## 测试与示例

- 执行计划状态机的行为测试在 `.trellis/scripts/tests/test_execution_plan.py`。
- 规划门禁和会话隔离分别由 `.trellis/scripts/tests/test_planning_gate.py`、`.trellis/scripts/tests/test_active_task_session_isolation.py` 覆盖。
- 代理提示与 Hook 合同由 `.trellis/scripts/tests/test_subagent_prompt_contract.py` 覆盖。

## 禁止事项

- 不用字符串拼接替代 JSON/结构化解析。
- 不吞掉异常或把不可执行的检查伪造为通过；应报告 `not applicable`，必要时用 `plan.py block/revise`。
- 不提交 `__pycache__`、`.pyc` 或 `.pyo`；模板安装器会主动拒绝这些缓存。
