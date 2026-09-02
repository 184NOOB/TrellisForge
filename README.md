# TrellisForge

TrellisForge 是一套可复用的 Trellis 项目级工作流覆盖模板集合，以嵌入式 C
项目作为完整范例。它不替代 `trellis init`，而是在初始化后的仓库中补齐以下能力：

- 规划阶段的 Grill Me 与显式审批门禁；
- Claude Code 与 Codex 的子代理上下文注入；
- implement/check/research 代理定义；
- `execution-plan.json` 状态机、追加式审计日志和验证等级；
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
- 用任务目录内的 schema 3 `execution-plan.json` 和追加式 `execution-events.jsonl` 管理 Phase 2：计划必须先通过 `plan.py validate`，每个阶段再以 `start`、`record`、`done` 推进；`minimal` 阶段记录 `required_checks`，末端 `report` 阶段登记 `final-report.md`；计划错误或阶段失败时通过 `block`、`revise` 留下可复核的修订轨迹。
- 审查代理以变更为中心进行定向检查，并仅执行项目真实存在的构建、静态检查和测试；收尾时将代码提交、归档和 journal 分开审批。

执行计划是实施阶段的状态门禁，不是构建或测试执行器。实现代理必须在首次编辑业务源码前，读取任务的 PRD、Spec 和代码，生成并校验计划；工作流要求计划获批后才按各阶段的 `scope.write` 修改产品源码或配置。`plan.py` 强制计划状态、验证结果和审计日志的一致性，但不会拦截任意文件编辑；`scope.write` 和编辑次数提醒属于 Claude `plan-pretool-reminder.py` 等辅助层，Codex 没有 `PreToolUse` 等价提醒。实际检查仍由代理或项目命令执行，再用 `record` 记录 `required_checks` 结果和任务目录内的最终报告；这些机制不能替代独立的 2.2 质量检查。审计日志损坏时必须先修复日志，不能绕过 `plan.py` 继续推进。

| 原流程的问题 | 工作流解决方案 | TrellisForge 的修改位置 | 修改内容与原因 |
| --- | --- | --- | --- |
| 规划任务可以在需求、技术决策尚未收敛时进入实施，用户批准与 `task.py start` 的边界不够明确 | 先写完并校验规划收敛标记，再展示最终摘要；用户后续明确批准后才启动任务 | `.trellis/workflow.md`、`.trellis/scripts/common/planning_gate.py`、`.trellis/scripts/task.py`、`AGENTS.md.template` | 增加 `planning_ready`、`plan_approved` 和 `Planning Convergence` 门禁。原因是仅有“已经讨论过”不能证明 PRD、设计和实施计划已收敛。 |
| Phase 2 只能依赖 `implement.md` 或代理记忆推进，阶段范围和验证证据不易复核 | 先生成并校验执行计划，再通过唯一 CLI 逐阶段推进、记录验证和审计修订；独立质量检查仍负责复核结果 | `.trellis/workflow.md`、`.trellis/scripts/plan.py`、`.trellis/scripts/common/execution_plan.py`、Claude/Codex implement Hook、Claude `plan-pretool-reminder.py` 与测试 | 新增 schema 3 `execution-plan.json` 状态机、`execution-events.jsonl` 追加式审计日志、依赖校验、`scope.write`/编辑次数辅助提醒、`minimal`/`report` 两级验证与 `required_checks`；明确 Claude 提醒和 Codex 上下文 Hook 都不替代 CLI，`plan.py` 不执行构建或测试。 |
| Grill Me 容易被当成必须反复提问的问卷，仓库已有事实也会被重复询问 | 先检索仓库证据并分类决策所有权；仅对仍未解决的用户决策一次问一个问题，零问题也可收敛 | `.trellis/workflow.md`、`.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/` | 分开证据、工程决策和用户决策，避免制造澄清问题，同时保留真正需要用户选择的分支。 |
| 新会话或 Codex fallback 可能继承上一会话的活动任务，导致在错误任务上规划或修改 | 每个会话只接受精确的 `session:*` 任务来源；身份不明时停止并报告，不猜测旧任务 | `.trellis/scripts/common/active_task.py`、`.trellis/scripts/common/task_store.py`、`.trellis/scripts/tests/test_active_task_session_isolation.py` | 实现 fail-closed 会话隔离；只为明确识别的 pull-based 子代理启用 fallback，并用回归测试锁定边界。 |
| 多任务树常把所有节点都用 `--no-start` 创建，再用 `task.py start` 绕过规划阶段选择任务 | 父任务和延后兄弟任务可延后启动，下一步唯一子任务必须绑定当前会话；`task.py start` 只用于已批准规划进入实施 | `.trellis/workflow.md`、任务创建与上下文脚本 | 将任务选择、规划批准和实施启动拆成可审计的状态转换，避免用启动命令绕过规划门禁。 |
| 子代理每轮只读一个文件、改一处、立刻验证，导致大量重复思考和无效工具轮次 | 一次批量读取和检索，集中完成相关编辑；按阶段验证，修复后只复验受影响检查，满足范围和验收证据后立即停止 | `.trellis/workflow.md`、`.trellis/agents/implement.md`、`.trellis/agents/check.md`、`.claude/agents/`、`.codex/agents/` | 通过减少模型重新加载上下文的轮次降低总耗时，而不是依赖更快编译。 |
| 实施和审查提示词经常把完整 PRD、Spec、research、清单和 diff 再粘贴一遍，Hook 已注入的内容也被重新阅读 | 派发只携带任务路径、目标、范围、非目标、已有验收条件和验证命令；先用 Hook 上下文，只有证据显示缺失时补读 | `.trellis/workflow.md`、两套 `.claude/hooks/inject-subagent-context.py`、`.codex/hooks/inject-subagent-context.py`、implement/check agents | 降低重复 prompt、上下文回传和思考成本；保留 `original_prompt`，因此这是可审计的工作流约束，不是按长度截断。 |
| 主代理把“逐个 grep”“每项单独构建”等工具编排写进实施提示，子代理按小步操作并反复验证 | 在实施派发入口保守分区；只改写明确“执行策略”中的碎片化编排，编号步骤和常见中文变体统一改为批量扫描/按阶段验证；目标、范围、验收条件和验证命令保持原文 | `.trellis/scripts/common/subagent_prompt_policy.py`、`.trellis/scripts/tests/test_subagent_prompt_contract.py`、两套注入 Hook、三个 implement 模板、`.trellis/workflow.md` | 将“逐项”解释为报告粒度而不是一次工具调用，减少重复 Read/Grep/Edit/Bash 和无效重建；保留无法安全分区的业务要求，避免正则误改验收语义 |
| 审查代理被要求重新完整探索实现过程，或无证据地扫描整个 Spec/仓库 | 先看完整 diff、任务清单和验收条件，再按 diff、调用图、review profile 和项目规则决定补读范围 | `.agents/skills/__PROJECT_PREFIX__-trellis-review/`、`.claude/agents/trellis-check.md`、`.codex/agents/trellis-check.toml` | 用 `light/standard/strict` 对应 changed-scope、affected-scope、full-scope，避免审查重复实现探索。 |
| 通用模板要求运行并不存在的 Web `lint/typecheck`，对嵌入式 C 造成无效验证轮次 | 只运行任务或项目定义的静态检查、测试和目标构建；无适用命令就记录 `not applicable` 或 `not run` | `.trellis/agents/implement.md`、`.trellis/agents/check.md`、`.claude/agents/`、`.codex/agents/`、`.agents/skills/__PROJECT_PREFIX__-trellis-review/` | 分开报告构建、静态检查、单元测试和实体硬件验证，避免虚构命令引发重复尝试；迁移其他语言时替换为真实检查命令。 |
| 默认的收尾入口可能把代码提交、任务归档和 session journal 混成一个动作 | Phase 3.4 单独取得代码提交批准；`finish-work` 只归档和记录 journal，bookkeeping 变化再单独批准 | `.agents/skills/trellis-finish-work/`、`.claude/commands/trellis/`、`.trellis/workflow.md`、`.trellis/spec/shared/trellis-maintenance.md` | 分离代码变更与运行记录的审批对象，并提供 `/trellis:continue`、`/trellis:finish-work` 路由入口。 |

### 本次子代理提示规范化修复

本次修复针对一个具体耗时来源：主代理提示中把等价检查拆成“逐个 grep”“每项分别构建”等微步骤，实施代理就会按项目逐次调用工具并反复验证。原有的批量操作文字只是静态说明，Hook 仍把原始提示原样传递，因而没有形成运行时约束。

解决方案是增加共享的 `subagent_prompt_policy.py`。实施派发时，它按目标、范围、非目标、验收条件、验证命令和执行策略进行保守分区；只有明确位于执行策略分区的碎片化工具编排才会被改写为一次批量扫描或阶段统一验证。编号列表先剥离编号再处理，`每一个`、`逐一`、`挨个`、`每项分别`、`每处重新编译` 等中文变体有回归测试。无法安全识别的内容原样保留并标记为业务要求，避免误改真实验收条件；该机制是提示级约束，不是工具层硬拦截。

涉及文件：

- `.trellis/scripts/common/subagent_prompt_policy.py`：共享分区、去重和批量化规则；
- `.trellis/scripts/tests/test_subagent_prompt_contract.py`：15 项规范化、JSON 输出和 Claude/Codex 行为测试；
- `.claude/hooks/inject-subagent-context.py`、`.codex/hooks/inject-subagent-context.py`：普通派发和 Codex Native 实施入口接入规范化器与执行契约；
- `.claude/agents/trellis-implement.md`、`.codex/agents/trellis-implement.toml`、`.trellis/agents/implement.md`、`.trellis/workflow.md`：把批量读取、阶段验证和完成即停止写成实施规则。
