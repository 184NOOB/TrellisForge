# 覆盖层内容

本目录设计为覆盖已经执行过 `trellis init` 的项目，且不包含运行时任务资料。

| 路径 | 安装策略 | 说明 |
| --- | --- | --- |
| `.trellis/workflow.md` | `-Force` 覆盖前备份 | 规划、实施、审查路由（Claude Code / Codex / OpenCode 三平台）、Channel 派发与唯一等待、子代理效率规则 |
| `.trellis/config.yaml` | `-Force` 覆盖前备份，随后填写 | 禁用会话自动提交、包和上下文注入配置 |
| `.trellis/scripts/` | `-Force` 覆盖同名前备份 | 会话隔离、规划/批准门禁、schema 3 两级执行计划状态机与审计 CLI、子代理提示规范化实现及测试 |
| `.trellis/scripts/common/subagent_prompt_policy.py` | 覆盖前备份 | 保守识别目标/范围/验收/命令/执行策略，仅批量化明确执行策略中的碎片化操作 |
| `.trellis/scripts/tests/test_trellis_channel_contract.py` | 覆盖前备份（`add`，1.1 新增） | Channel Skill 树完整性、公共镜像一致、Codex 终端术语作用域与唯一等待契约测试 |
| `.trellis/scripts/tests/test_opencode_platform_contract.py` | 覆盖后新增（1.2 新增） | OpenCode 平台闭包、JS 行为（Node harness）、会话隔离、五级审查与提示规范化跨平台合同测试 |
| `.trellis/spec/shared/` | 覆盖同名前备份，随后填写 | 嵌入式 C 的仓库、验证和硬件合同骨架 |
| `.trellis/spec/shared/trellis-maintenance.md` | 覆盖前备份 | 上游更新、受保护定制和升级后验证合同 |
| `.agents/skills/` | `-Force` 覆盖同名前备份 | Grill Me、规划 adapter、审查 profile、定制 `trellis-finish-work` 与完整 `trellis-channel` Skill |
| `.agents/skills/trellis-channel/` | 接管合并（1.0 adoption-baseline → 1.1 managed） | `SKILL.md` 与 `references/`（command-reference、forum、progress-debugging、workers、workflows）五个公共参考；1.1 新增“Standard dispatch use…”公共规则并移除历史多余尾部空行 |
| `.claude/` | `-Force` 覆盖前备份 | Claude Code Hook、执行计划提醒、代理与设置 |
| `.claude/skills/trellis-channel/` | 接管合并（1.0 adoption-baseline → 1.1 managed） | 与 `.agents/` 镜像一致的 Channel Skill 公共文件 |
| `.claude/commands/trellis/` | `-Force` 覆盖前备份 | Claude `/trellis:finish-work` 与 `/trellis:continue` 路由命令 |
| `.codex/` | `-Force` 覆盖前备份 | Codex Hook、代理与设置 |
| `.opencode/` | 新增目录（1.2 起默认交付，`add`） | OpenCode 第三默认平台的完整闭包：`package.json`（`@opencode-ai/plugin` 依赖）、`lib/`（会话键/任务解析/上下文材料化/Shell 桥/计划展示桥）、`plugins/`（session-start、逐轮 workflow-state、subagent 上下文与 Shell 身份桥，各文件仅一个 default export）、`agents/`（`trellis-research|implement|check` 原生子代理）、`commands/trellis/`（start/continue/finish-work 路由命令）、`skills/`（上游通用 Skill 全引用树 + 模板定制 grill-me、`__PROJECT_PREFIX__-trellis-grill-adapter`、`__PROJECT_PREFIX__-trellis-review`、`trellis-finish-work` 与定制 `trellis-channel` 覆盖同名上游）。OpenCode 主工作流使用原生 Task 子代理；Channel worker provider 仍仅 `claude|codex`。安装冲突预检、备份、回滚、canonical 对象与 1.2 manifest 集成已由 1.2 发布收尾完成并纳入 `tests/test_overlay_tools.py` 回归。 |
| `AGENTS.md.template` | 人工合并 | 目标项目事实与硬约束，不自动覆盖根 AGENTS.md |

## 安装收据与升级交付物

- 首次安装成功后会写入目标仓库的 `.trellis/trellisforge.json` 安装收据，
  记录 schema 版本、TrellisForge 版本（当前 `VERSION`，即 `1.2`）、覆盖层类型、
  项目名称/前缀和受管文件摘要；每个文件记录三类哈希：`canonical_sha256`
  （渲染前 canonical 对象哈希）、`baseline_sha256`（按项目参数渲染后的基线）和
  `installed_sha256`（实际安装结果）。收据由安装器脚本在事务最后一步生成，
  不是本目录的静态模板；本目录不复制该文件。
- 覆盖层的电梯模型升级交付物位于仓库级 `history/embedded-c-overlay/`
  （canonical 对象库 + `versions/1.0`、`versions/1.1`、`versions/1.2` 版本
  manifest）与 `migrations/embedded-c-overlay/structural/`（相邻结构迁移步骤
  `1.0-to-1.1.json`、`1.1-to-1.2.json`），配合
  `tests/test_overlay_tools.py`（临时 Git 仓库自动化测试）；这些都不属于
  发布模板本身，不会安装到目标仓库。
- 升级成功后同样写入 `.trellis/trellisforge.json` 1.2 三类哈希收据；来源可以是
  1.0（无收据入场，须显式项目参数）或带有效 1.1 收据的项目，文件正文一律从
  来源 canonical 一步三方合并到 1.2 模板，仅结构迁移按相邻步骤组合；已有
  1.2 收据时，重复升级识别为 `already-current` 并安全退出。

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