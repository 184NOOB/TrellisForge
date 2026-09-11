# 支持 OpenCode 平台

## Workflow Settings

- Review level: standard

## Goal

在 TrellisForge 1.2 面向下游嵌入式 C 项目的发布模板中，将 OpenCode 增加为与 Claude Code、Codex 并列的默认支持平台，使 OpenCode 主会话和原生子代理执行当前模板已经定义的同一套规划、上下文、执行计划、五级审查、问题修复责任和收尾合同。

本任务不是把上游 Trellis 的默认 OpenCode 文件原样复制进仓库，而是以 `templates/embedded-c-overlay/` 的现行 TrellisForge 定制为行为事实源，用 OpenCode 原生文件格式承载等价语义。

## Confirmed Facts

- TrellisForge 是叠加在 `trellis init` 结果之上的项目级工作流覆盖层；当前完整交付范例是 `templates/embedded-c-overlay/`，服务于下游嵌入式 C 项目，而不是本仓库自身的产品运行时。
- 面向下游的新功能默认只修改 `templates/embedded-c-overlay/`。根目录 `.trellis/`、`.agents/skills/`、`.claude/` 和 `.codex/` 是 TrellisForge 仓库自用实例，只能作为只读证据，不能因模板新增 OpenCode 而反向同步修改。
- 当前模板已包含此前 1.2 子任务落地的最新合同；OpenCode 必须对齐当前模板，而不是回退到上游 Trellis `0.6.10` 的通用默认行为。
- 模板合法审查等级共有五个，固定顺序为 `light < standard < reinforced < comprehensive < strict`。其中 `reinforced` 与 `comprehensive` 已由父任务下的既有子任务加入，不能遗漏或降级。
- `templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` 是五级审查、证据失效和阻塞问题责任路由的权威合同；工作流、规划门禁和各平台 Check Agent 是其消费者。
- 当前模板还包含规划收敛与后续批准门禁、schema 3 执行计划与追加式审计、子代理提示规范化、会话级任务隔离、Channel 上下文读取规则、嵌入式 C 验证分类和定制收尾流程。
- 上游 Trellis `0.6.10` 的 `trellis init --opencode` 已提供 OpenCode 原生的 agents、commands、skills、plugins、lib 和 package 结构，可作为平台格式与事件 API 的起点；它不取代 TrellisForge 模板语义。
- OpenCode 使用 `chat.message`、`session.compacted` 和 `tool.execute.before` 等插件事件，并支持原生 `trellis-research`、`trellis-implement`、`trellis-check` 子代理。
- Trellis `0.6.10` 的 Channel 受管 worker provider 只有 Claude 和 Codex。用户已决定 OpenCode 使用原生子代理完成主工作流，`trellis channel spawn --provider opencode` 不属于本任务。
- 父任务固定收尾子任务 `09-10-readme-integration-guide-upgrade-patch` 负责在全部 1.2 功能子任务结束后统一更新版本、README、接入指南、canonical 对象、版本 manifest、结构迁移链和升级补丁。

## Requirements

### R1. 下游模板是唯一功能交付目标

- OpenCode 功能实现必须位于 `templates/embedded-c-overlay/`，并以该目录当前内容为需求和行为基线。
- 不得修改根目录自用 `.trellis/`、`.agents/skills/`、`.claude/` 或 `.codex/` 来实现本功能，也不得要求根目录与新增模板文件双向镜像。
- OpenCode 平台文件可以采用不同语言和配置格式，但对外工作流结果不得弱于或偏离模板中 Claude Code、Codex 的现行合同。

### R2. 默认交付完整的 OpenCode 平台入口

- OpenCode 必须成为 TrellisForge 的第三个默认平台，不通过目标仓库探测或可选安装开关决定是否交付。
- 下游模板必须具备 OpenCode 完成主工作流所需的平台资产闭包，包括平台依赖声明、共享运行库、插件、原生子代理、命令和需要由 OpenCode 直接发现的项目级 Skills。
- 平台资产必须覆盖 SessionStart、逐轮工作流状态、Shell 会话身份桥接、子代理上下文、任务继续和任务收尾等现有模板入口；不能只添加三个 Agent 文件便宣称完成支持。
- 上游 OpenCode 资产中的通用说明必须按 TrellisForge 当前模板定制，尤其不能保留三档审查、通用 Web 检查、宽泛自修复或缺少执行计划门禁的旧语义。

### R3. 规划与启动门禁一致

- OpenCode 必须遵循模板的 Phase 1 流程：任务创建许可与实施许可分离，先读取仓库证据，再由 `trellis-brainstorm`、`grill-me` 和 `PROJECT_PREFIX-trellis-grill-adapter` 处理用户拥有的决策。
- OpenCode 必须持久化并尊重 `planning_ready`、`plan_approved` 和 `## Planning Convergence`；未收敛或未获得后续显式批准时不得进入 Phase 2。
- OpenCode 必须接受 `light`、`standard`、`reinforced`、`comprehensive`、`strict` 五个审查等级；缺失或无效值仍按模板规则回退到 `standard`。
- 复杂任务仍要求 `prd.md`、`design.md`、`implement.md`，原生子代理模式仍要求真实的 `implement.jsonl` 与 `check.jsonl` 上下文条目。

### R4. 会话状态与上下文一致

- OpenCode SessionStart 和逐轮提示必须读取下游项目的 `.trellis/workflow.md`、任务状态和 Spec 索引；工作流状态正文继续以模板 `workflow.md` 标签块为唯一事实源。
- OpenCode 主会话执行 `task.py` / `plan.py` 时必须携带当前 OpenCode 会话身份，并与 `.trellis/.runtime/sessions/` 中的会话级任务指针一致。
- 多窗口、多任务、陈旧指针和歧义会话场景不得借用其他主会话的任务；Shell 不直接暴露会话 ID 时必须使用平台插件提供的 `TRELLIS_CONTEXT_ID` 桥接。
- OpenCode 子代理上下文顺序必须与模板一致：对应 JSONL 中的 Spec/Research -> `prd.md` -> 可选 `design.md` -> 可选 `implement.md` -> 当前执行计划状态。
- 自动注入缺失或截断时，Agent 必须按模板定义的主动读取协议恢复上下文；无法确定活动任务时停止并报告，不猜测其他会话。

### R5. 原生子代理行为一致

- OpenCode 必须通过原生 Task/子代理机制提供 `trellis-research`、`trellis-implement`、`trellis-check`，并保持研究、实施、审查三种职责和写入边界分离。
- Research Agent 只在当前任务 `research/` 中持久化研究结果，不修改产品或模板实现。
- Implement Agent 必须遵守模板的递归防护、禁止提交边界、任务上下文协议、schema 3 执行计划状态机和批量化执行纪律。
- Check Agent 必须遵守模板的独立审查、五级 profile、问题修复责任和报告合同；不得退化为“发现任何问题都自行修复”的通用审查提示。
- 派发提示必须保留任务目标、范围、非目标、验收条件和验证命令，只对明确属于执行策略的碎片化工具编排做批量化规范；不得为每个字段、符号或发现分别扫描、构建或派发代理。

### R6. 五级审查合同完整一致

- `light` 使用 changed-scope 主会话审查，不派发独立 Check Agent。
- `standard` 执行恰好一次独立 affected-scope 审查；阻塞修复后由主会话验证，除非证据失效，否则不自动重复完整独立审查。
- `reinforced` 执行 affected-scope 独立审查，并在每轮阻塞问题批量修复后派发 fresh Check Agent 重新完整审查，直至最新报告阻塞数为零。
- `comprehensive` 采用与 `reinforced` 相同的 fresh 独立闭环，但每轮为 full-scope；达到零阻塞后不增加额外 commit-ready 终审。
- `strict` 在 full-scope 独立闭环之外，还必须对稳定的 commit-ready 快照执行 fresh 独立 full-scope 终审；终审发现阻塞问题时继续修复和 fresh 终审至零。
- 任务变更集、公共合同、验收条件或适用 Spec 实质变化时，已有相关审查证据失效，必须按当前 profile 重新审查。
- OpenCode 审查报告必须与模板其他路径一致地记录等级、范围、轮次、阶段、阻塞问题数、已修复/未修复发现、责任去向、验收证据、验证、未运行检查和剩余风险。

### R7. 阻塞问题责任与恢复路径一致

- Check Agent 只直接修复同时满足局部、机械、小型、确定且位于任务范围内的问题。
- PRD、设计或验收缺陷返回 Phase 1；越界或环境/权限问题只报告；其他实现阻塞问题返回主会话，不由 Check Agent 派发或恢复 Implement Agent。
- 主会话处理非机械实现阻塞问题时，必须沿用模板顺序：宿主可靠支持时优先续接原 Implement Agent；否则小而边界明确的问题由主会话处理，复杂修复派发新的 Implement Agent。
- 问题修复责任只决定谁修复，不得改变 R6 中各 profile 的审查范围、独立性和轮次。

### R8. 执行计划、验证与收尾一致

- Phase 2 的文件修改必须受 `execution-plan.json` 与 `execution-events.jsonl` 约束，且状态只能通过 `plan.py start|record|done|block|revise` 推进；插件提示不是可替代 CLI 门禁的安全边界。
- OpenCode 必须保持模板的两级验证合同：普通阶段为 `minimal`，唯一终端报告阶段为 `report` 并登记 `final-report.md`。
- 静态检查、测试、目标构建和实体硬件验证必须分开报告为 pass/fail/not run/not applicable，且只能使用下游项目真实定义的命令，不得引入通用 Web lint/typecheck 假设。
- Spec 更新、用户确认后的提交和定制 `trellis-finish-work` 归档/会话记录顺序必须与模板现行 Phase 3 一致；任何 Agent 不得自行提交、推送、合并或改写历史。

### R9. 模板内跨平台合同测试

- 模板现有只覆盖 Claude/Codex 的平台枚举、提示生成、Agent 内容和 Hook 等价性测试必须扩展为包含 OpenCode，不能留下“只支持两个平台”的陈旧断言。
- 自动化测试必须验证 OpenCode 对 R3-R8 的关键合同，并验证引入 OpenCode 不改变 Claude Code、Codex 和 Channel runtime 的现行行为。
- OpenCode 使用 JavaScript 插件时，测试与语法检查必须覆盖其原生文件；Python 测试不得假装执行了 OpenCode 运行时。

## Acceptance Criteria

- [ ] AC1: 本功能的实现改动只位于 `templates/embedded-c-overlay/` 及当前任务资料；根目录自用 Trellis 平台和运行时文件没有被反向同步修改。
- [ ] AC2: 模板包含 OpenCode 完成主工作流所需的平台依赖、lib、plugins、agents、commands 和 OpenCode 可发现 Skills；全新下游安装不依赖预先存在的 `.opencode/` 文件才能获得这些受管能力。
- [ ] AC3: OpenCode 在 `no_task`、`planning`、`in_progress`、`completed` 状态下得到与模板工作流一致的下一步，并通过 planning convergence、后续批准和执行计划门禁阻止越阶段修改。
- [ ] AC4: OpenCode 接受并正确路由全部五个审查等级；模板内不存在针对 OpenCode 的 `light|standard|strict` 三档残留或将 `reinforced` / `comprehensive` 回退为 `standard` 的路径。
- [ ] AC5: 并行 OpenCode 会话分别绑定不同任务时，主会话 Shell、逐轮状态和子代理均使用正确的会话级任务；缺失、陈旧和歧义上下文会显式失败而不串线。
- [ ] AC6: OpenCode Research、Implement、Check Agent 的职责、上下文读取、递归防护、写入/提交边界、执行计划和报告语义与模板当前 Claude/Codex 路径一致。
- [ ] AC7: 五级审查在 OpenCode 下分别满足 changed/affected/full scope、独立审查轮次、fresh reviewer、证据失效和 strict commit-ready 终审合同。
- [ ] AC8: OpenCode Check Agent 对机械问题、实现阻塞、规划缺陷、越界问题和环境阻塞执行模板规定的责任路由，且责任路由不会自行新增或跳过审查轮次。
- [ ] AC9: OpenCode 实施与审查提示保留业务要求并应用模板的批量工具纪律；不存在逐项工具调用、每处修改后全量构建或完成后无影响重复扫描等退化。
- [ ] AC10: OpenCode 路径完整执行 schema 3 计划审计、两级验证、Spec 更新、提交授权和 `trellis-finish-work` 收尾，不依赖 Hook/插件作为唯一门禁。
- [ ] AC11: 模板的跨文件合同测试将 OpenCode 纳入平台矩阵，同时证明 Claude Code、Codex、Channel Agent、五级审查、任务隔离和提示规范化没有回归。
- [ ] AC12: 运行模板相关 Python 单测、Python 语法检查、OpenCode JavaScript/JSON 语法检查和 `git diff --check` 均通过；构建、部署和硬件验证对 TrellisForge 仓库本身报告为 `not applicable`。
- [ ] AC13: 父任务固定收尾子任务能据本任务交付清单将 OpenCode 纳入 TrellisForge 1.2 默认安装、冲突预检、备份、回滚、版本 manifest、升级补丁和接入文档；这些发布集成资产不由本功能子任务提前修改。

## Out Of Scope

- 修改根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`，或为了本任务在根目录新增自用 `.opencode/`。
- 在本功能子任务中更新 `VERSION`、README、`docs/接入指南.md`、canonical 对象、1.2 版本 manifest、结构迁移链、安装/升级补丁；这些属于父任务固定收尾子任务。
- 修改上游 Trellis npm 包或 OpenCode CLI。
- 为 Trellis Channel 新增 OpenCode 受管 worker provider，或实现 `trellis channel spawn --provider opencode`。
- 修复 Trellis `0.6.10` 中处于降级状态的 OpenCode `trellis mem` 会话读取器；它不属于本次约定的主工作流与原生子代理范围。
- 改变模板现有五级审查、schema 3 执行计划、阻塞问题责任、Channel worker 生命周期、嵌入式 C 验证或提交授权合同。
- 顺带支持其他 AI 平台。

## Key Decisions

- 行为事实源是当前 `templates/embedded-c-overlay/`，不是上游 Trellis 默认 OpenCode 模板，也不是根目录自用 Trellis。
- OpenCode 作为第三个默认平台完整交付，不使用平台探测、条件清单或可选安装模式。
- OpenCode 使用原生 Task/子代理执行 Research、Implement、Check；Channel 通用协作能力可继续使用，但 OpenCode 受管 worker provider 暂不纳入。
- OpenCode 必须实现模板现有五级审查：`light`、`standard`、`reinforced`、`comprehensive`、`strict`。
- 功能子任务只交付模板能力和模板内验证；父任务固定收尾子任务统一完成 1.2 发布资产与文档集成。

## Risks And Deferred Items

- 上游 OpenCode 文件只能作为平台 API 起点；若直接复制，会丢失 TrellisForge 的五级审查、执行计划、提示规范化、嵌入式 C 验证和问题责任合同。
- OpenCode 插件与 Python Hook 的实现形态不同，不能以文本相同代替行为等价；模板测试需要验证可观察合同而非文件字节一致。
- 父任务收尾前，live 模板新增 `.opencode/` 与当前 1.1 manifest 暂时不一致是版本开发期状态；固定收尾子任务必须恢复模板、manifest、历史对象和安装器验证的一致性。
- OpenCode Channel worker 和 OpenCode 历史会话读取器均受上游 `0.6.10` 能力限制，已明确延后，不得在实施中暗中扩大范围。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
