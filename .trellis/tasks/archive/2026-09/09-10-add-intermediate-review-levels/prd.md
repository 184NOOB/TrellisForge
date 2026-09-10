# 新增 reinforced 与 comprehensive 审查等级

## Workflow Settings

- Review level: standard

## Goal

在现有 `light`、`standard`、`strict` 审查等级之间加入 `reinforced` 和 `comprehensive`，把审查范围、阻塞项独立复审闭环和提交前 fresh 终审拆成清晰、可执行且可验证的五档策略。

新增等级应让中高风险任务能够选择“阻塞项修复后必须由独立审查 Agent 再确认”，而不必一律承担 `strict` 的 commit-ready fresh 终审成本。

## Confirmed Facts

- 当前审查等级只接受 `light`、`standard`、`strict`，默认值为 `standard`。
- 当前 `standard` 在实施后执行一次独立 affected-scope 审查；发现问题并修复后由主会话重跑受影响检查，除非任务范围发生实质变化，否则不重复完整独立审查。
- 当前 `strict` 使用 full-scope 独立审查，修复后重复相关审查直至阻塞项清零，并要求提交前完成最终审查。
- 当前等级允许值和路由规则在本仓库自用 Trellis 与下游发布模板中都有对应实现，但本任务只更新 `templates/embedded-c-overlay/` 内面向下游项目的工作流、规划门禁、审查 Skill、审查 Agent 和测试。本仓库根目录自用 Trellis 仅作为现状参考，不属于本任务交付范围。
- affected-scope 和 full-scope 都以任务影响证据为边界；full-scope 不是扫描与任务无关的整个仓库。

## Review Level Contract

| Level | Review scope | Independent review | Blocking-fix verification | Extra commit-ready review |
|---|---|---|---|---|
| `light` | changed-scope | 无，由主会话审查 | 主会话重跑失败或直接受影响的检查 | 无 |
| `standard` | affected-scope | 实施后一次 | 主会话验证；任务范围未实质变化时不重复独立审查 | 无 |
| `reinforced` | affected-scope | 实施后独立审查 | 每轮阻塞项修复后重新派发独立审查，直至阻塞项为零 | 无 |
| `comprehensive` | full-scope | 实施后独立审查 | 每轮阻塞项修复后重新派发独立审查，直至阻塞项为零 | 不强制额外 commit-ready 终审 |
| `strict` | full-scope | 可在重要实施批次后审查 | 每轮阻塞项修复后重新派发独立审查，直至阻塞项为零 | 必须对稳定的 commit-ready 快照执行 fresh 独立终审 |

## Scope Definitions

- `changed-scope`：实际任务 diff、列明的未跟踪任务文件、修改文件、公共接口、直接调用点及直接适用的快速检查。
- `affected-scope`：完整任务变更集、受影响模块、公共接口、直接调用点、一层依赖、所有验收条件及有影响证据的 Spec 和测试；不得无证据扩展到无关模块。
- `full-scope`：完整任务变更集、所有受影响包或工具层、适用 Spec、跨层契约、测试、安装器检查及发布模板变更所需的下游验证记录；仍排除与任务无影响关系的仓库区域。

## Requirements

- 审查等级的合法值和固定强度顺序必须变为：`light`、`standard`、`reinforced`、`comprehensive`、`strict`。
- 未填写或填写无效的等级仍默认使用 `standard`；用户最新一次明确选择仍具有最高优先级。
- `light` 和 `standard` 的既有行为不得因新增等级而发生隐式增强或削弱。
- 所有功能实现必须限定在 `templates/embedded-c-overlay/` 的下游发布模板内。可以读取根目录自用 Trellis 作为行为基线，但不得修改或把模板改动反向同步到根目录 `.trellis/workflow.md`、`.trellis/agents/`、`.trellis/scripts/common/planning_gate.py`、`.agents/skills/`、`.claude/` 或 `.codex/`。
- `reinforced` 必须执行 affected-scope 独立审查。若本轮发现阻塞项，则先按现有职责边界完成修复，再重新派发独立审查 Agent 执行下一轮 affected-scope 审查，直到最新独立报告中的阻塞项为零。
- `comprehensive` 必须执行 full-scope 独立审查，并采用与 `reinforced` 相同的阻塞项修复和独立复审闭环；达到零阻塞后，不因进入提交准备而强制增加一轮 full-scope 审查。
- `strict` 必须包含 `comprehensive` 的 full-scope 闭环，并在代码、测试、Spec 和任务交付物全部稳定后，对 commit-ready 快照额外派发一次 fresh 独立 full-scope 终审。终审发现阻塞项时，修复后继续独立终审闭环，直至阻塞项为零。
- 每轮审查发现的阻塞项应批量分流和修复，再派发下一轮审查；不得为每个拼写或单个低风险发现分别启动完整审查。
- 清晰、局部且任务范围内的机械问题可由审查 Agent 直接修复；较大的实现问题返回实施环节；PRD、设计或验收缺陷返回规划环节；超出任务范围的问题只报告并交由主会话决定。
- 非阻塞发现可在报告中保留为剩余风险，不要求仅为其启动独立复审；正确性、安全性和验收阻塞项在所有等级下都不得豁免。
- 每次独立复审仍按所选 profile 的完整范围执行，而不是只确认上一轮发现；`reinforced` 使用 affected-scope，`comprehensive` 和 `strict` 使用 full-scope。
- 任一等级完成审查后，如果任务变更集、公共契约、验收条件或适用 Spec 发生实质变化，已有审查证据失效，必须按当前等级重新审查。`comprehensive` 因证据失效触发的重审不等同于额外 commit-ready 门禁；`strict` 即使没有此类变化也必须执行 fresh 终审。
- 在支持独立 Agent 的 Claude Code 和 Codex 路径上必须实际派发相应审查 Agent；平台无法派发时，沿用现有降级规则并明确记录等价的主会话审查及独立性缺失。
- `templates/embedded-c-overlay/` 内的工作流提示、规划门禁、项目审查 Skill、Claude/Codex 审查 Agent 和模板测试必须对五档名称及行为保持一致，不能出现模板内某一层接受新等级而另一层回退为 `standard` 的情况。
- 审查报告必须记录等级、范围、轮次、阻塞项、修复归属、验证结果、未运行检查和剩余风险，使主会话能够判断是否继续复审或进入提交准备。
- 本子任务不更新 `VERSION`、历史 canonical 对象、版本 manifest、结构迁移链、README 或接入指南；这些发布收尾内容由父任务固定最后一项 `09-10-readme-integration-guide-upgrade-patch` 依据全部 1.2 子任务的最终结果统一处理。

## Acceptance Criteria

- [ ] 新任务 PRD 或现有任务 PRD 可使用五个合法等级中的任意一个，规划门禁不会把 `reinforced` 或 `comprehensive` 误判为无效值。
- [ ] 缺失或无效的 `Review level` 仍回退到 `standard`，明确用户选择仍覆盖默认值。
- [ ] `reinforced` 的 affected-scope 审查发现阻塞项后，修复完成会触发新的独立 affected-scope 审查；只有最新独立报告为零阻塞时才结束审查循环。
- [ ] `comprehensive` 采用 full-scope 执行相同的独立闭环，零阻塞后不自动要求额外 commit-ready full-scope 审查。
- [ ] `strict` 在完成 full-scope 闭环之外，仍会对稳定的 commit-ready 快照执行 fresh 独立 full-scope 终审；终审阻塞项同样必须修复并复审至零。
- [ ] 非阻塞发现不会单独触发完整复审，但会作为发现、修复或剩余风险被准确记录。
- [ ] 审查后的实质性任务变化会使旧证据失效并按当前等级重新触发审查；仅 `strict` 在无实质变化时仍具有额外 fresh 终审门禁。
- [ ] affected-scope 与 full-scope 的边界按任务影响证据确定，不会将 full-scope 实现为无差别扫描整个仓库。
- [ ] 实际功能改动仅位于 `templates/embedded-c-overlay/`；本仓库根目录自用 `.trellis/`、`.agents/skills/`、`.claude/` 和 `.codex/` 没有因本任务发生功能性修改。
- [ ] `templates/embedded-c-overlay/` 内的工作流、Claude/Codex 审查角色、规划门禁、项目 Skill 和测试中的等级契约保持一致。
- [ ] 模板内自动化测试覆盖五档合法值、默认回退、各档路由、阻塞复审循环、证据失效和 strict commit-ready 终审门禁。
- [ ] 项目规定的 Python 单测、Python 语法检查和 `git diff --check` 通过；构建、部署和硬件验证报告为 `not applicable` 并说明本仓库没有对应目标。

## Out Of Scope

- 在用户批准最新规划摘要之前执行计划、运行 `task.py start` 或开始修改工作流实现。
- 修改本仓库根目录自用 Trellis 工作流、规划门禁、Agent、Skill、Hook 或平台配置；“根目录改动需同步模板”不是“模板改动需反向同步根目录”。
- 改变 `changed-scope`、`affected-scope`、`full-scope` 的基本含义，或把 full-scope 扩大为无证据的全仓库扫描。
- 新增审查 provider、模型选择策略、严重级别体系或自动提交功能。
- 修改实施 Agent 的执行计划协议、Trellis Channel worker 生命周期或提交授权规则。
- 为低风险非阻塞发现强制重复独立审查。
- 提前更新 TrellisForge 版本号、升级资产、README 或接入指南。

## Risks And Deferred Items

- 五档比三档更难选择；最终规划摘要和审查报告必须不仅显示等级名，还显示范围、复审策略与 commit-ready 门禁。
- `comprehensive` 与 `strict` 都使用 full-scope；两者通过“是否强制 fresh commit-ready 终审”保持稳定区别。
- 技术方案已确定不新增运行时状态机或任务 schema；轮次与阶段证据通过 Check Agent 报告传递，并由模板内跨文件合约测试防止五档语义漂移。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
