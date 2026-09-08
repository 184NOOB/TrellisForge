# 覆盖层内容

本目录设计为覆盖已经执行过 `trellis init` 的项目，且不包含运行时任务资料。

| 路径 | 安装策略 | 说明 |
| --- | --- | --- |
| `.trellis/workflow.md` | `-Force` 覆盖前备份 | 规划、实施、审查路由、Channel 派发与唯一等待、子代理效率规则 |
| `.trellis/config.yaml` | `-Force` 覆盖前备份，随后填写 | 禁用会话自动提交、包和上下文注入配置 |
| `.trellis/scripts/` | `-Force` 覆盖同名前备份 | 会话隔离、规划/批准门禁、schema 3 两级执行计划状态机与审计 CLI、子代理提示规范化实现及测试 |
| `.trellis/scripts/common/subagent_prompt_policy.py` | 覆盖前备份 | 保守识别目标/范围/验收/命令/执行策略，仅批量化明确执行策略中的碎片化操作 |
| `.trellis/scripts/tests/test_trellis_channel_contract.py` | 覆盖前备份（`add`，1.1 新增） | Channel Skill 树完整性、公共镜像一致、Codex 终端术语作用域与唯一等待契约测试 |
| `.trellis/spec/shared/` | 覆盖同名前备份，随后填写 | 嵌入式 C 的仓库、验证和硬件合同骨架 |
| `.trellis/spec/shared/trellis-maintenance.md` | 覆盖前备份 | 上游更新、受保护定制和升级后验证合同 |
| `.agents/skills/` | `-Force` 覆盖同名前备份 | Grill Me、规划 adapter、审查 profile、定制 `trellis-finish-work` 与完整 `trellis-channel` Skill |
| `.agents/skills/trellis-channel/` | 三方合并（1.0→1.1 `adopt`） | `SKILL.md` 与 `references/`（command-reference、forum、progress-debugging、workers、workflows）五个公共参考；1.1 新增“Standard dispatch use…”公共规则并移除历史多余尾部空行 |
| `.claude/` | `-Force` 覆盖前备份 | Claude Code Hook、执行计划提醒、代理与设置 |
| `.claude/skills/trellis-channel/` | 三方合并（1.0→1.1 `adopt`） | 与 `.agents/` 镜像一致的 Channel Skill 公共文件 |
| `.claude/commands/trellis/` | `-Force` 覆盖前备份 | Claude `/trellis:finish-work` 与 `/trellis:continue` 路由命令 |
| `.codex/` | `-Force` 覆盖前备份 | Codex Hook、代理与设置 |
| `AGENTS.md.template` | 人工合并 | 目标项目事实与硬约束，不自动覆盖根 AGENTS.md |

## 安装收据与升级交付物

- 首次安装成功后会写入目标仓库的 `.trellis/trellisforge.json` 安装收据，
  记录 schema 版本、TrellisForge 版本（`1.1`）、覆盖层类型、项目名称/前缀和
  受管文件摘要。收据由安装器脚本在事务最后一步生成，不是本目录的静态模板；
  本目录不复制该文件。
- 覆盖层的版本化 1.0→1.1 升级交付物位于仓库级
  `migrations/embedded-c-overlay/1.0-to-1.1/`（迁移清单 + 1.0 旧基线 + 1.1 目标快照）与
  `tests/test_overlay_tools.py`（临时 Git 仓库自动化测试），不属于发布模板
  本身，不会安装到目标仓库。
- 升级成功后同样写入 `.trellis/trellisforge.json` 1.1 收据；已有 1.1 收据时，
  重复升级识别为 `already-current` 并安全退出。

## 边界与安全检查

安装脚本没有删除文件，也不复制 `.trellis/tasks/`、`.trellis/workspace/`、
`.trellis/.runtime/` 和 `.trellis/.template-hashes.json`。
`-Force` 备份所有实际被覆盖的模板文件，并在备份根目录写入
`backup-manifest.json`；备份位于 Git 元数据目录下，不会成为工作树未跟踪文件；
根 `AGENTS.md` 始终不自动覆盖。升级器对用户定制的受管文件执行三方文本合并，
任一冲突都不会修改工作树，并在 `.git/trellisforge-upgrade/` 生成报告与候选
文件。`TEMPLATE-CONTENTS.md` 仅供 Forge 维护者阅读，不会安装到目标仓库。
模板只包含源码和配置，不含 Python `__pycache__` 或 `.pyc/.pyo` 缓存；安装器
发现缓存时会拒绝继续。