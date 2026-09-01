# 覆盖层内容

本目录设计为覆盖已经执行过 `trellis init` 的项目，且不包含运行时任务资料。

| 路径 | 安装策略 | 说明 |
| --- | --- | --- |
| `.trellis/workflow.md` | `-Force` 覆盖前备份 | 规划、实施、审查路由和子代理效率规则 |
| `.trellis/config.yaml` | `-Force` 覆盖前备份，随后填写 | 禁用会话自动提交、包和上下文注入配置 |
| `.trellis/scripts/` | `-Force` 覆盖同名前备份 | 会话隔离、规划/批准门禁、子代理提示规范化实现及测试 |
| `.trellis/scripts/common/subagent_prompt_policy.py` | `-Force` 覆盖前备份（首次接入时新增） | 保守识别目标/范围/验收/命令/执行策略，仅批量化明确执行策略中的碎片化操作 |
| `.trellis/scripts/tests/test_subagent_prompt_contract.py` | `-Force` 覆盖前备份（首次接入时新增） | Claude/Codex Hook、Native fallback、编号步骤和中文变体行为测试 |
| `.trellis/spec/shared/` | `-Force` 覆盖同名前备份，随后填写 | 嵌入式 C 的仓库、验证和硬件合同骨架 |
| `.trellis/spec/shared/trellis-maintenance.md` | 覆盖前备份（首次接入时新增） | 上游更新、受保护定制和升级后验证合同 |
| `.agents/skills/` | `-Force` 覆盖同名前备份 | Grill Me、规划 adapter、审查 profile、定制 `trellis-finish-work` |
| `.claude/` | `-Force` 覆盖前备份 | Claude Code Hook、代理与设置 |
| `.claude/commands/trellis/` | `-Force` 覆盖前备份 | Claude `/trellis:finish-work` 与 `/trellis:continue` 路由命令 |
| `.codex/` | `-Force` 覆盖前备份 | Codex Hook、代理与设置 |
| `AGENTS.md.template` | 人工合并 | 目标项目事实与硬约束，不自动覆盖根 AGENTS.md |

安装脚本没有删除文件，也不复制 `.trellis/tasks/`、`.trellis/workspace/`、
`.trellis/.runtime/` 和 `.trellis/.template-hashes.json`。
`-Force` 备份所有实际被覆盖的模板文件，并在备份根目录写入
`backup-manifest.json`；备份位于 Git 元数据目录下，不会成为工作树未跟踪文件；
根 `AGENTS.md` 始终不自动覆盖。`TEMPLATE-CONTENTS.md` 仅供 Forge 维护者阅读，
不会安装到目标仓库。
模板只包含源码和配置，不含 Python `__pycache__` 或 `.pyc/.pyo` 缓存；安装器
发现缓存时会拒绝继续。
