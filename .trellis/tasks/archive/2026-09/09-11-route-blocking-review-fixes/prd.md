# 明确审查阻塞问题修复责任

## Workflow Settings

- Review level: strict
- Task-specific review override: keep strict full-scope independent implementation-loop reviews and fresh re-review after each blocking-fix batch until zero blocking findings, but omit the additional commit-ready final review for this task only.

## Goal

统一 TrellisForge 1.2 下游发布模板中各运行路径的 Check Agent 修复边界，并明确阻塞问题返回主会话后的责任分流。审查代理只直接修复机械、小且确定的问题；需要设计或实现判断的问题由主会话协调合适的实施责任方，避免审查代理越权改写，也避免在原 Implement Agent 可以低成本续接时无条件重新派发。

## Confirmed Facts

- 发布模板的权威审查契约 `templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md:159` 已有 `Blocking-Finding Ownership`，但其较大实现缺陷分支目前只允许主会话修复或派发 fresh Implement Agent，并在 `:166` 禁止续接已退出代理。
- Channel Check Agent `templates/embedded-c-overlay/.trellis/agents/check.md:107` 已区分机械问题、较大实现缺陷、设计/判断问题和越界问题，但 `:109` 同样写明不得续接已退出代理。
- Claude Check Agent `templates/embedded-c-overlay/.claude/agents/trellis-check.md:49`、`:54`、`:104` 当前要求无条件自行修复，未明确机械问题与设计/判断问题的边界。
- Codex Check Agent `templates/embedded-c-overlay/.codex/agents/trellis-check.toml:31` 只要求直接修复 clear in-scope findings，边界仍不足以表达完整责任分流。
- Claude 与 Codex 的上下文注入 Hook 分别在 `templates/embedded-c-overlay/.claude/hooks/inject-subagent-context.py:696`、`:701` 和 `templates/embedded-c-overlay/.codex/hooks/inject-subagent-context.py:699`、`:704` 保留了直接修复问题的宽泛表述，可能覆盖或稀释代理文件中的细分政策。
- 审查等级契约已经独立定义 `light`、`standard`、`reinforced`、`comprehensive`、`strict` 的审查范围、独立性和重复审查规则；问题修复责任不应成为另一套重复审查触发器。
- `09-10-optimize-channel-context-loading` 已完成并归档，其模板修改是本任务规划与后续实施所基于的当前基线，不再构成未满足的并发写入依赖。

## Requirements

### R1. Check Agent 的直接修复边界

- Check Agent 仅可直接修复同时满足以下条件的问题：位于当前任务范围内、局部、机械、小、修复方式确定且不需要产品、设计或架构判断。
- 典型机械问题包括 lint 小问题、缺失类型、错误导入、明确的死分支及同等级的确定性修正；示例不应被解释为允许扩大修复范围。
- Check Agent 必须在审查报告中记录其直接修复的问题和验证结果。
- 设计、需求、架构或其他需要判断的问题只能记录和报告，不得由 Check Agent 静默改写。

### R2. 阻塞实现问题的责任分流

- 对不属于 R1 的实现类阻塞问题，Check Agent 负责提供证据并返回主会话，不自行派发 Implement Agent，也不自行扩大修改。
- 主会话首先判断报告的问题是否真实存在以及是否属于当前任务范围，再选择实施责任方。
- 原 Implement Agent 在宿主支持可靠续接、其任务上下文仍可用且续接不会破坏隔离边界时，主会话优先让其续接修复。
- 原 Implement Agent 无法可靠续接时，若修复小且边界明确，由主会话直接修复。
- 原 Implement Agent 无法可靠续接且属于复杂实现修复时，由主会话派发新的 Implement Agent。复杂实现修复包括一个或多个相互耦合的阻塞问题，且涉及跨模块、接口或契约调整，改动面或回归风险较大，需要重新建立较完整的实现上下文并执行成组验证。
- 问题数量和严重级别只作为复杂度判断信号，不单独决定是否派发新 Implement Agent；单个高风险问题也可能构成复杂实现修复，多个同根因的局部问题也可能仍适合主会话直接修复。若风险源自 PRD、设计或验收标准缺陷，仍按 R3 返回 Phase 1。
- 在 Codex inline 模式中，主会话本身就是实施者，不虚构或强制派发原本不存在的 Implement Agent。
- “优先续接”是有能力条件的路由策略，不要求所有宿主新增会话续接能力，也不得恢复已不可寻址或上下文不可信的执行实例。

### R3. 非实现类问题的路由

- PRD、设计或验收标准缺陷返回 Phase 1，更新规划产物并重新经过所需批准，不作为普通实现修复处理。
- 越出当前任务范围的问题只报告，由主会话决定是否创建后续任务。
- 无法在权限、环境或任务边界内修复的问题必须报告原因和建议路由，不得伪装为已修复。

### R4. 与审查等级保持正交

- 修复责任只回答“谁来修复”，不得规定“是否再次审查、审查几轮、是否使用 fresh reviewer”。
- 是否重复审查、每轮范围、独立性以及 fresh Check Agent 要求，只由任务选择的 `light|standard|reinforced|comprehensive|strict` 审查等级契约及其证据失效规则决定。
- 修复责任分流本身不得让 `standard` 自动进入循环审查，也不得让 `reinforced`、`comprehensive` 或 `strict` 跳过其等级要求的后续审查。

### R5. 发布模板跨路径一致性

- 统一发布模板中的权威 review Skill、Channel Check Agent、Claude Check Agent、Codex Check Agent，以及 Claude/Codex Check Agent Hook 注入提示的语义。
- 各平台可以保留自身格式、工具名和上下文加载方式，但不得保留与 R1-R4 冲突的无条件 self-fix、无条件 fresh Implement Agent 或禁止一切续接的表述。
- Hook 注入提示只能强化同一政策，不得通过更宽泛的 `Fix issues yourself` 重新引入策略漂移。

## Acceptance Criteria

- [ ] AC1: 发布模板的权威 review Skill 明确写出 R1-R4 的责任边界，并把 Implement Agent 的选择顺序定义为“能够可靠续接则优先续接；否则由主会话按修复规模直接处理或派发新 Implement Agent”。
- [ ] AC2: Channel、Claude 和 Codex 的 Check Agent 定义对机械问题、设计/判断问题、较大实现阻塞、规划缺陷和越界问题给出语义一致的处理方式。
- [ ] AC3: Claude/Codex Hook 生成的 Check Agent 提示不再要求无条件 self-fix，且不会覆盖代理定义或 review Skill 的分级与路由政策。
- [ ] AC4: Codex inline 模式明确由主会话承担实现修复；不支持可靠续接的宿主明确降级到主会话修复或新 Implement Agent，而不是假定续接能力存在。
- [ ] AC5: 修复责任条款不新增重复审查标准；五级审查配置原有的范围、轮次、独立性和 fresh reviewer 语义保持由审查等级契约控制。
- [ ] AC6: 相关模板契约测试覆盖至少以下失败情形：Claude 无条件 self-fix 文案回归、Hook 绕过分级、禁止所有 Implement Agent 续接、修复责任触发额外审查轮次，以及平台间语义不一致。
- [ ] AC7: 对模板正文、代理和 Hook 的后续实现通过仓库规定的对应 Python 单测、Python 语法解析与 `git diff --check`；未适用的构建或硬件验证明确报告为 `not applicable`。
- [ ] AC8: 功能变更仅落在 `templates/embedded-c-overlay/`；本工程自用的根目录 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 只作为证据读取，不被当作本功能的同步修改目标。

## Dependency And Ordering

- 本任务依赖的 `09-10-optimize-channel-context-loading` 已完成并归档；后续设计和实施必须以其已提交模板状态为基线。
- 本任务作为 1.2 功能子任务，必须排列在固定收尾子任务 `09-10-readme-integration-guide-upgrade-patch` 之前。
- README、接入指南、升级补丁、版本号、模板历史对象和发布清单的统一更新由固定收尾子任务处理，本任务不提前修改。

## Out Of Scope

- 在最新完整规划获得后续用户批准前创建执行计划、启动 Phase 2 或修改发布模板实现。
- 修改本工程自用的根目录 `.trellis/agents/`、`.agents/skills/`、`.claude/` 或 `.codex/` 工作流实现。
- 为不支持续接的宿主开发新的续接基础设施，或保证任何已退出进程都可以恢复。
- 改变发布模板中五个审查等级各自的范围、轮次、独立审查或提交前审查强度；本任务自身的显式审查例外不写入发布模板政策。
- 更新 `VERSION`、README、接入指南、升级补丁、manifest 或迁移链。

## Risks And Deferred Items

- 各宿主的续接能力与句柄形态不统一；技术设计将“当前主会话持有且宿主确认可用的原代理句柄”作为可靠续接前提，实施不得把任何平台能力当作通用事实。
- 同一政策存在于 review Skill、workflow、Channel 角色卡、平台代理和 Hook 提示多个入口；技术设计已确定同步文件集，后续必须用专用合约测试防止再次漂移。
- 现有文案同时使用 issue、finding、blocking defect 等术语；技术设计已确定先判断规划/越界/机械/实现类别的顺序，实施不得改变本 PRD 的责任边界。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
