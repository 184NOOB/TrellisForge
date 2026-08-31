# TrellisForge

TrellisForge 是一套可复用的 Trellis 项目级工作流覆盖模板集合，以嵌入式 C
项目作为完整范例。它不替代 `trellis init`，而是在初始化后的仓库中补齐以下能力：

- 规划阶段的 Grill Me 与显式审批门禁；
- Claude Code 与 Codex 的子代理上下文注入；
- implement/check/research 代理定义；
- 子代理批量读取、合并编辑、分阶段验证、最小复验与停止条件；
- 项目级 `light`、`standard`、`strict` 审查合同；
- 面向嵌入式 C 的构建、硬件验证和硬件合同边界。

从 [docs/接入指南.md](docs/接入指南.md) 开始。最短接入命令为：

```powershell
# 在目标项目根目录执行
trellis init
# 在 TrellisForge 根目录执行
& .\tools\install-embedded-c-overlay.ps1 -TargetRoot C:\path\to\project -ProjectPrefix example -ProjectName "Example Firmware" -Force
```

安装后必须按指南填写 `AGENTS.md` 和 `.trellis/spec/` 中的项目事实，再提交。
本仓库以嵌入式 C 项目作为完整示例模板，但定位是可复用的 Trellis 项目级
工作流覆盖层：规划门禁、上下文注入、子代理效率规则、审查流程和收尾边界
可以迁移到其他语言项目；接入其他语言时，必须按指南替换 C 特化的规则、检查
命令、Spec 和领域术语，不能把嵌入式 C 模板原样当作通用项目配置。

本仓库提供可复用的工作流模板和嵌入式 C 示例，但不含任何特定产品的源码、任务记录、Flash 布局或硬件协议。

## TrellisForge 对 Trellis 的改造说明

以下说明 TrellisForge 对 Trellis 的项目级覆盖改造。这些改造作用于项目仓库的
Trellis 覆盖层，不修改 Trellis 的全局安装目录，也不包含任何特定产品的项目事实。

### 本工作流的解决方法

本工作流采用“项目级覆盖层 + 状态门禁 + 证据驱动”的方法。先由 `trellis init`
提供上游基线，再用本仓库的模板补齐项目级规则、脚本和代理配置；通过明确的状态转换和验收证据控制每个阶段的进入与退出。这不是靠限制 prompt 长度来强行压缩模型思考，而是减少无必要的重复工作。

具体解决方案包括：

- 用 `planning_ready` 和 `plan_approved` 门禁把需求、技术决策、实施计划和实施启动分开，防止未收敛就进入编码。
- 用会话隔离和 fail-closed 回退防止子代理继承错误任务，用户未明确选择时停止而不猜测。
- 要求子代理先批量读取和检索，再集中编辑，按阶段执行必要验证，满足验收条件后停止，以减少重复思考和工具轮次。
- 让 Hook 提供可用上下文，让代理根据 diff、调用关系、验收条件和项目规则决定是否补读，避免无证据地重复阅读整个仓库。
- 审查代理以变更为中心进行定向检查，并仅执行项目真实存在的构建、静态检查和测试；收尾时将代码提交、归档和 journal 分开审批。

| 原流程的问题 | 工作流解决方案 | TrellisForge 的修改位置 | 修改内容与原因 |
| --- | --- | --- | --- |
| 规划任务可以在需求、技术决策尚未收敛时进入实施，用户批准与 `task.py start` 的边界不够明确 | 先写完并校验规划收敛标记，再展示最终摘要；用户后续明确批准后才启动任务 | `.trellis/workflow.md`、`.trellis/scripts/common/planning_gate.py`、`.trellis/scripts/task.py`、`AGENTS.md.template` | 增加 `planning_ready`、`plan_approved` 和 `Planning Convergence` 门禁。原因是仅有“已经讨论过”不能证明 PRD、设计和实施计划已收敛。 |
| Grill Me 容易被当成必须反复提问的问卷，仓库已有事实也会被重复询问 | 先检索仓库证据并分类决策所有权；仅对仍未解决的用户决策一次问一个问题，零问题也可收敛 | `.trellis/workflow.md`、`.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/` | 分开证据、工程决策和用户决策，避免制造澄清问题，同时保留真正需要用户选择的分支。 |
| 新会话或 Codex fallback 可能继承上一会话的活动任务，导致在错误任务上规划或修改 | 每个会话只接受精确的 `session:*` 任务来源；身份不明时停止并报告，不猜测旧任务 | `.trellis/scripts/common/active_task.py`、`.trellis/scripts/common/task_store.py`、`.trellis/scripts/tests/test_active_task_session_isolation.py` | 实现 fail-closed 会话隔离；只为明确识别的 pull-based 子代理启用 fallback，并用回归测试锁定边界。 |
| 多任务树常把所有节点都用 `--no-start` 创建，再用 `task.py start` 绕过规划阶段选择任务 | 父任务和延后兄弟任务可延后启动，下一步唯一子任务必须绑定当前会话；`task.py start` 只用于已批准规划进入实施 | `.trellis/workflow.md`、任务创建与上下文脚本 | 将任务选择、规划批准和实施启动拆成可审计的状态转换，避免用启动命令绕过规划门禁。 |
| 子代理每轮只读一个文件、改一处、立刻验证，导致大量重复思考和无效工具轮次 | 一次批量读取和检索，集中完成相关编辑；按阶段验证，修复后只复验受影响检查，满足范围和验收证据后立即停止 | `.trellis/workflow.md`、`.trellis/agents/implement.md`、`.trellis/agents/check.md`、`.claude/agents/`、`.codex/agents/` | 通过减少模型重新加载上下文的轮次降低总耗时，而不是依赖更快编译。 |
| 实施和审查提示词经常把完整 PRD、Spec、research、清单和 diff 再粘贴一遍，Hook 已注入的内容也被重新阅读 | 派发只携带任务路径、目标、范围、非目标、已有验收条件和验证命令；先用 Hook 上下文，只有证据显示缺失时补读 | `.trellis/workflow.md`、两套 `.claude/hooks/inject-subagent-context.py`、`.codex/hooks/inject-subagent-context.py`、implement/check agents | 降低重复 prompt、上下文回传和思考成本；保留 `original_prompt`，因此这是可审计的工作流约束，不是按长度截断。 |
| 审查代理被要求重新完整探索实现过程，或无证据地扫描整个 Spec/仓库 | 先看完整 diff、任务清单和验收条件，再按 diff、调用图、review profile 和项目规则决定补读范围 | `.agents/skills/__PROJECT_PREFIX__-trellis-review/`、`.claude/agents/trellis-check.md`、`.codex/agents/trellis-check.toml` | 用 `light/standard/strict` 对应 changed-scope、affected-scope、full-scope，避免审查重复实现探索。 |
| 通用模板要求运行并不存在的 Web `lint/typecheck`，对嵌入式 C 造成无效验证轮次 | 只运行任务或项目定义的静态检查、测试和目标构建；无适用命令就记录 `not applicable` 或 `not run` | `.trellis/agents/implement.md`、`.trellis/agents/check.md`、`.claude/agents/`、`.codex/agents/`、`.agents/skills/__PROJECT_PREFIX__-trellis-review/` | 分开报告构建、静态检查、单元测试和实体硬件验证，避免虚构命令引发重复尝试；迁移其他语言时替换为真实检查命令。 |
| 默认的收尾入口可能把代码提交、任务归档和 session journal 混成一个动作 | Phase 3.4 单独取得代码提交批准；`finish-work` 只归档和记录 journal，bookkeeping 变化再单独批准 | `.agents/skills/trellis-finish-work/`、`.claude/commands/trellis/`、`.trellis/workflow.md`、`.trellis/spec/shared/trellis-maintenance.md` | 分离代码变更与运行记录的审批对象，并提供 `/trellis:continue`、`/trellis:finish-work` 路由入口。 |
