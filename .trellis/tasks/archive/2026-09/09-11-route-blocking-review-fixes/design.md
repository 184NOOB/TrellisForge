# 审查阻塞问题修复责任技术设计

## 目标与边界

本设计统一 TrellisForge 1.2 下游发布模板中 Check Agent 的直接修复边界，并建立阻塞问题返回主会话后的实施责任路由。功能修改只落在 `templates/embedded-c-overlay/`；根目录自用 `.trellis/`、`.agents/skills/`、`.claude/` 和 `.codex/` 仅用于读取现状，不同步修改。

本任务只调整工作流、Skill、Agent 和 Hook 的提示契约及其合约测试，不新增 CLI、任务 schema、会话数据库、Hook 状态或平台续接能力。任务目录中的 PRD、execution plan 和审计事件仍是可恢复执行状态的事实源；宿主原生代理句柄只用于节省同一主会话内的上下文重载成本，不成为任务恢复的必要条件。

## 责任模型

问题处理分成“问题分类与修复责任”和“修复后是否审查”两个正交阶段：

```text
Check Agent finding
        |
        v
主会话确认问题存在、任务归属和问题类别
        |
        +-- 局部、机械、小、确定、范围内 --> Check Agent 已直接修复
        +-- PRD/设计/验收缺陷 -----------> 返回 Phase 1
        +-- 越界或环境/权限阻塞 ----------> 只报告，由主会话决定后续任务
        `-- 非机械性实现阻塞 -------------> 实施责任路由
                                                |
                                                +-- Codex inline --> 主会话修复
                                                +-- 原 Agent 能可靠续接 --> 原 Agent
                                                +-- 不可续接且小、边界明确 --> 主会话
                                                `-- 不可续接且复杂 --> 新 Implement Agent

完成修复
   |
   `-- 仅依据 Review level 和证据失效规则决定后续审查
```

Check Agent 不负责启动或续接 Implement Agent。它只直接修复满足全部机械条件的问题，并对其余问题提供位置、严重度、证据、未修复原因和建议类别。主会话对报告做最小必要核实并执行路由；这一核实是所有权判断，不计为新的独立审查轮次。

## 问题分类顺序

主会话按以下顺序判断，避免“高风险”覆盖规划边界：

1. 确认 finding 真实存在、证据仍适用于当前快照，并属于当前任务。
2. 若根因是 PRD、设计或验收标准缺陷，返回 Phase 1，不进入 Implement Agent 路由。
3. 若问题越界，或受权限、环境、外部依赖限制，只报告并由主会话决定后续任务。
4. 若问题同时满足局部、机械、小、确定且范围内，由当前 Check Agent 直接修复并记录验证。
5. 其余实现类阻塞问题返回主会话，进入实施责任路由。

这里的“小且边界明确”允许主会话处理需要少量实现判断但无需重建完整实现上下文的修复；它与 Check Agent 可直接处理的“机械、小且确定”不是同一集合。

复杂实现修复由实现耦合和验证成本共同判定，典型信号包括：

- 一个或多个相互耦合的阻塞问题；
- 跨模块、公共接口、数据流或契约调整；
- 改动面或回归风险较大；
- 需要重新建立较完整的实现上下文并执行成组验证。

问题数量和严重级别只作为信号。单个高风险问题可能足够复杂，多个同根因的局部问题也可能仍适合主会话直接修复。

## 可靠续接契约

只有同时满足以下条件时，主会话才把原 Implement Agent 视为可可靠续接：

- 当前主会话持有宿主返回的原代理句柄、session id 或 thread id，且能确认它对应当前任务与当前工作区；
- 宿主明确提供 follow-up 或 resume 能力，句柄仍可寻址，续接调用被宿主接受；
- 任务目录中的 execution plan、审计事件和当前代码快照仍有效，代理可以先重读这些事实源再修复；
- finding 不要求返回 Phase 1，续接不会破坏任务范围、权限或隔离边界。

不同运行路径按能力降级：

- Channel 路径可在精确 session/thread id 可用时使用现有 `trellis channel spawn --resume <id>` 能力。
- Claude/Codex 直接子代理路径只使用宿主原生返回并由当前主会话持有的代理句柄；不扫描或猜测其他会话标识。
- Codex inline 路径没有独立 Implement Agent，主会话直接作为实施者。
- 句柄缺失、归属不明、上下文不可信、宿主不支持或续接调用失败，均按“无法可靠续接”处理。

不新增会话标识持久化。跨会话、崩溃恢复或主会话失去句柄时，仍从任务目录状态恢复，再按修复复杂度选择主会话或新 Implement Agent。

“Implement Agent 优先续接”只适用于实施者。独立 Check Agent 的 fresh reviewer 要求保持不变，不恢复上一轮审查者会话。

## 审查等级正交性

修复责任段只回答谁执行修复，不定义审查范围、轮次或独立性。修复完成后：

- `light`、`standard`、`reinforced`、`comprehensive`、`strict` 继续完全按现有 review profile 契约决定后续动作；
- `standard` 不因发生实施责任路由而自动进入独立循环审查；
- `reinforced`、`comprehensive` 和 `strict` 不因原 Implement Agent 被续接而跳过下一轮 fresh Check Agent；
- 任务变更集、公共契约、验收条件或适用 Spec 实质变化时，仍由现有证据失效规则触发当前 profile 的审查；
- 发布模板中 `strict` 的 commit-ready fresh 终审规则不变；本开发任务自身的审查例外见下一节，不进入产品模板契约。

## 本任务审查执行配置

本任务使用 `Review level: strict`，但采用用户明确指定的任务级例外：

- 实施完成后执行独立 full-scope 审查；
- 每批阻塞问题修复后，新派 fresh Check Agent 完整重审，直到最新报告为零阻塞；
- 任务 diff、公共契约、验收条件或适用 Spec 实质变化时，现有证据失效并重新执行 full-scope 审查；
- 不在进入提交准备时额外执行 commit-ready final review。

该例外只控制当前任务的审查调度，不修改 `templates/embedded-c-overlay/` 中任何 review profile 定义，也不允许把产品模板的 `strict` 改写成相同行为。每次审查派发都必须在 prompt 中明确标注本任务例外，最终报告也要记录未执行额外 commit-ready final review 的依据。

## 权威来源与同步面

`templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` 继续作为审查等级和阻塞 finding 所有权的权威契约。其他入口保留平台特有格式，但不得弱化该契约。

| 文件 | 设计改动 |
| --- | --- |
| `templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` | 重写 `Blocking-Finding Ownership`，加入主会话核实、可靠续接、主会话修复、新 Implement Agent 和复杂度判定；保留 reviewer fresh 规则 |
| `templates/embedded-c-overlay/.trellis/workflow.md` | 将“fresh implementation pass”改为明确的所有权路由，并声明后续审查只由 profile 与证据失效决定 |
| `templates/embedded-c-overlay/.trellis/agents/check.md` | 保留机械问题直接修复；较大实现、规划缺陷与越界问题只报告，不再禁止主会话续接原 Implement Agent |
| `templates/embedded-c-overlay/.claude/agents/trellis-check.md` | 移除无条件 self-fix，增加与 Channel 一致的 finding 分类、写入边界和未修复报告 |
| `templates/embedded-c-overlay/.codex/agents/trellis-check.toml` | 将宽泛 clear in-scope self-fix 收紧为机械、小且确定，并增加相同的只报告分支 |
| `templates/embedded-c-overlay/.claude/hooks/inject-subagent-context.py` | `build_check_prompt` 注入同一 finding handling 契约，不再要求无条件自行修复 |
| `templates/embedded-c-overlay/.codex/hooks/inject-subagent-context.py` | 与 Claude Hook 保持相同语义，同时保留 Codex 生命周期和安全边界 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_fix_ownership_contract.py` | 新增跨 workflow、Skill、Agent、Hook 的专用防漂移合约测试 |

不修改 Implement Agent 定义。原代理和新代理都继续从现有任务文件与 execution plan 恢复工作，本任务只改变主会话选择实施责任方的顺序。

## Hook 与 Agent 协作

Claude/Codex Hook 的 `build_check_prompt` 只注入执行边界，不承担主会话路由。两个 Hook 生成的 finding handling 段采用等价内容：

- 仅机械、小、确定且范围内的问题允许 Check Agent 直接修复；
- 实现阻塞、规划缺陷和越界问题必须报告，不由 Check Agent 派发或续接实施者；
- 修复后的审查动作由所选 profile 决定。

Agent 自身仍保留同样边界，以覆盖 Hook 未运行、注入截断或 agent pull 的路径。Hook 和 Agent 重复的是安全责任边界，不复制 Implement Agent 的具体派发命令。

## 测试设计

新增 `test_review_fix_ownership_contract.py`，通过静态文本检查与 Hook builder 行为检查锁定以下契约：

1. review Skill 和 workflow 都包含机械直修、主会话核实、原 Implement Agent 可靠续接、不可续接时主会话/新代理分流以及 Phase 1/越界路由。
2. Channel、Claude、Codex Check Agent 都只允许机械、小且确定的问题直接修复，并禁止 Check Agent 自行派发或续接 Implement Agent。
3. Claude/Codex `build_check_prompt` 生成的 finding handling 段语义一致，不包含无条件 `Fix issues yourself`。
4. 受管入口不存在“Never resume an agent that already exited”或把所有较大实现问题强制路由到 fresh Implement Agent 的旧政策。
5. ownership 段不定义额外审查轮次；现有 `test_review_profile_contract.py` 继续证明五档范围、轮次、fresh reviewer 与 evidence invalidation 契约未改变。
6. 测试不启动真实 Agent、不依赖网络或硬件。

## 兼容性与回滚

- 对不支持代理续接的平台，行为自然降级为主会话修复或新 Implement Agent，现有宿主不需要新增能力。
- 对支持续接的平台，仅改变主会话优先级，不改变 task schema、execution plan 或审查报告字段。
- 各批次以专用合约测试和现有 review profile 测试为回滚边界。若某一平台入口无法表达全部路由，只保留 Check Agent 的报告职责，将派发决策放在 workflow/review Skill，不向 Agent 注入平台专用命令。
- README、接入指南、版本号、升级补丁、manifest 和迁移链由父任务固定收尾子任务统一处理。

## 已决工程决策

- 不新增运行时续接基础设施或持久状态。
- 把当前主会话持有并经宿主确认可用的原代理句柄作为可靠续接前提。
- 把 review Skill 作为权威责任契约，workflow 负责主会话路由，Check Agent/Hook 负责执行边界。
- 新增一个聚焦的所有权合约测试，不把责任规则混入现有五档 profile 测试的内部结构。
- 实施责任与重复审查保持正交。
