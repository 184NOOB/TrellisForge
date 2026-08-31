# 覆盖层内容

本目录设计为覆盖已经执行过 `trellis init` 的项目，且不包含运行时任务资料。

| 路径 | 安装策略 | 说明 |
| --- | --- | --- |
| `.trellis/workflow.md` | 覆盖 | 规划、实施、审查路由和子代理效率规则 |
| `.trellis/config.yaml` | 覆盖后填写 | 禁用会话自动提交、包和上下文注入配置 |
| `.trellis/scripts/` | 覆盖同名文件 | 会话隔离与规划/批准门禁实现及测试 |
| `.trellis/spec/shared/` | 新增/填写 | 嵌入式 C 的仓库、验证和硬件合同骨架 |
| `.agents/skills/` | 新增 | Grill Me、规划 adapter、审查 profile |
| `.claude/` | 覆盖或人工合并 | Claude Code Hook、代理与设置 |
| `.codex/` | 覆盖或人工合并 | Codex Hook、代理与设置 |
| `AGENTS.md.template` | 人工合并 | 目标项目事实与硬约束，不自动覆盖根 AGENTS.md |

安装脚本没有删除文件，也不复制 `.trellis/tasks/`、`.trellis/workspace/`、
`.trellis/.runtime/` 和 `.trellis/.template-hashes.json`。
