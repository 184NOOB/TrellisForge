# 五档审查等级技术设计

## 目标与架构边界

本设计把下游 Trellis 工作流的审查等级从三档扩展为五档，并让“审查范围”“阻塞项修复后的复审策略”和“提交前 fresh 终审”成为彼此独立、可验证的维度。功能实现只修改 `templates/embedded-c-overlay/`；根目录 `.trellis/`、`.agents/skills/`、`.claude/` 和 `.codex/` 仅作为现状参考，不反向同步模板改动。

本任务不引入新的运行时状态文件、CLI、任务 schema 或持久状态机。`prd.md` 中的 `Review level` 仍是等级事实源；规划门禁负责接受合法值，workflow 和 review Skill 负责路由，Check Agent 报告负责携带本轮证据，主会话负责依据报告推进修复、复审或提交准备。

```text
prd.md Review level
        |
        v
workflow + review Skill normalization
        |-- invalid/missing --> persist standard
        v
planning gate validates one of five values
        |
        +--> main-session changed-scope review (light)
        |
        +--> independent Check Agent (standard/reinforced/comprehensive/strict)
                         |
                         v
              structured review report
                         |
                         v
              main-session routing decision
```

## 五档 Profile 契约

固定强度顺序为 `light < standard < reinforced < comprehensive < strict`，但实现不依赖数值比较；每档行为在 workflow 和 review Skill 中显式定义，避免新增值落入旧的 `else` 分支。

| Level | Scope | 实施后独立审查 | 阻塞项修复后 | Commit-ready fresh 终审 |
|---|---|---|---|---|
| `light` | changed-scope | 无 | 主会话重跑失败或直接受影响检查 | 无 |
| `standard` | affected-scope | 恰好一次 | 主会话验证；证据未失效时不重复独立审查 | 无 |
| `reinforced` | affected-scope | 有 | 新派独立 Check Agent，完整重审至零阻塞 | 无 |
| `comprehensive` | full-scope | 有 | 新派独立 Check Agent，完整重审至零阻塞 | 无 |
| `strict` | full-scope | 有 | 新派独立 Check Agent，完整重审至零阻塞 | 必须；稳定快照上 fresh 重审至零阻塞 |

`affected-scope` 覆盖完整任务变更集、受影响模块、公共接口、直接调用点、一层依赖、全部验收条件以及有影响证据的 Spec 和测试。`full-scope` 在此基础上覆盖全部受影响包或工具层、跨层契约、安装器检查和发布模板所需的下游验证记录，但仍不扫描没有任务影响证据的仓库区域。

## 工作流路由

### Phase 1：规划与门禁

- `planning_gate.py` 接受 `light`、`standard`、`reinforced`、`comprehensive`、`strict`。它只校验已持久化的值，不修改 PRD；如果值仍缺失或非法，门禁按现有机制 fail closed 并报告五档合法集合。
- workflow、grill adapter 和 review Skill 使用同一五值集合；它们负责在缺失或非法时写入 `standard`，并在最终规划摘要中展示所选等级。
- 现有只写 `light`、`standard` 或 `strict` 的 PRD 无需迁移；既有任务行为保持兼容。

### Phase 2.2：实施后审查

- `light` 仍由主会话执行一次 changed-scope 审查。
- `standard` 仍只派发一次 affected-scope 独立审查；若发现阻塞项，按职责修复后由主会话验证直接受影响检查。只有任务变更集、公共契约、验收条件或适用 Spec 实质变化导致证据失效时，才重新执行所选 profile。
- `reinforced` 每轮执行完整 affected-scope 独立审查。报告存在阻塞项时，先批量完成该轮修复，再新派一个 Check Agent 开始下一轮，直到最新独立报告的阻塞项数量为零。
- `comprehensive` 使用与 `reinforced` 相同的循环，但每轮范围为 full-scope。零阻塞后不因进入提交准备而自动增加一轮审查。
- `strict` 的实施审查先执行 `comprehensive` 同等的 full-scope 闭环；其 commit-ready 终审由 Phase 3.4 单独约束。
- 平台支持独立 Agent 时，每轮复审使用新派发的 `trellis-check`，不恢复上一审查者会话，以保持独立性。平台不支持派发时，沿用现有降级规则并明确记录独立性缺失。

### Phase 3.4：提交前门禁

- `light`、`standard`、`reinforced` 和 `comprehensive` 只需确认最新审查证据仍有效，不强制新增 commit-ready 审查。
- `strict` 必须在代码、测试、Spec 和任务交付物稳定后，对 commit-ready 快照新派一次 fresh full-scope 独立终审。若终审产生阻塞项，则修复后重新建立稳定快照并再次 fresh 终审，直到零阻塞。
- 任何 profile 在审查后发生实质范围变化都使旧证据失效，需要按当前等级重新进入相应审查路径；这与 `strict` 无条件要求的额外 commit-ready 终审是两套不同触发条件。

## 阻塞项所有权与 Agent 生命周期

Check Agent 每轮结束后即退出，不要求实施 Agent 或审查 Agent 常驻。报告中的问题由主会话批量分流：

| 问题类型 | 修复所有者与后续动作 |
|---|---|
| 清晰、局部、机械且在任务范围内 | 当前 Check Agent 可直接修复，并在报告中记录 |
| 较大的实现缺陷 | 返回实施环节；主会话自行修复或重新派发新的实施 Agent，不恢复已经结束的旧 Agent |
| PRD、设计或验收缺陷 | 返回 Phase 1 更新规划并重新获得必要批准 |
| 超出任务范围 | Check Agent 只报告，由主会话决定是否另开任务 |

每轮先修复同批阻塞项，再根据 profile 决定主会话验证或新派独立复审。非阻塞项可记录为已修复项或剩余风险，不单独触发完整复审；正确性、安全性和验收阻塞项不可豁免。

## 审查报告契约

Channel、Claude 和 Codex Check Agent 使用语义一致的报告字段：

- `Review level`：五档之一；
- `Review scope`：`changed-scope`、`affected-scope` 或 `full-scope`；
- `Review round`：同一 stage 内从 1 开始的轮次；
- `Review stage`：`implementation-loop` 或 `commit-ready-final`；
- `Blocking findings count`：本轮仍未清零的阻塞项数量；
- findings：区分 fixed 与 not fixed，并标明 severity、位置和原因；
- fixes/ownership：已修复内容以及未修复项应返回实施、规划还是另行处理；
- acceptance evidence、verification、checks not run 和 residual risks。

主会话以最新一轮报告为准，不把前一轮“已修复”视为当前轮零阻塞证据。每次独立复审重新覆盖该 profile 的完整 scope，而不是只回看上一轮发现。

## 模板修改面

| 文件 | 设计改动 |
|---|---|
| `templates/embedded-c-overlay/.trellis/scripts/common/planning_gate.py` | 扩展合法等级集合，默认仍为 `standard` |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_planning_gate.py` | 覆盖五档合法值和无效值拒绝/默认契约 |
| `templates/embedded-c-overlay/.trellis/workflow.md` | 更新 Phase 1、Phase 2.2、final pass 与 Phase 3.4 路由和门禁 |
| `templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` | 作为五档语义权威契约，定义范围、循环、证据失效和报告要求 |
| `templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review/agents/openai.yaml` | 更新五档能力描述 |
| `templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` | 规划时接受五档并保持 `standard` 默认 |
| `templates/embedded-c-overlay/.trellis/agents/check.md` | Channel Check Agent 的五档执行与报告协议 |
| `templates/embedded-c-overlay/.claude/agents/trellis-check.md` | Claude Check Agent 的 profile 加载、轮次和报告协议 |
| `templates/embedded-c-overlay/.codex/agents/trellis-check.toml` | Codex Check Agent 的五档执行与报告协议 |
| `templates/embedded-c-overlay/.codex/hooks/inject-workflow-state.py` | 更新仍硬编码三档的提示文案，不在 Hook 内实现路由 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_profile_contract.py` | 静态解析跨文件契约，锁定五档集合、路由差异和报告字段 |

Claude Agent 当前主要依赖项目 review Skill 获取 profile 语义；本次会在保留该单一权威来源的同时，把执行入口和报告字段补充到 Agent 提示中。各平台文本无法共享导入一个 Python 常量，因此不引入伪统一模块，而用模板内合约测试检测漂移。

## 测试设计

1. `test_planning_gate.py` 参数化验证五个合法值均通过规划门禁，缺失或非法值仍按现有规则失败并提示五档合法集合。
2. 新增 `test_review_profile_contract.py`，读取模板 workflow、review Skill、grill adapter、三个 Check Agent 定义和 Codex Hook，断言：
   - 五档名称在所有合法值消费者中齐全；
   - `reinforced` 固定为 affected-scope 循环；
   - `comprehensive` 固定为 full-scope 循环且没有额外 commit-ready 门禁；
   - `strict` 同时具备 full-scope 循环和 fresh commit-ready 终审；
   - 报告契约包含 level、scope、round、stage 和 blocking count；
   - 旧的三档枚举文案不再残留在受管模板文件中。
3. 运行模板测试、根目录既有回归测试、模板 Python 语法检查和 `git diff --check`。
4. 构建、部署和硬件验证为 `not applicable`：本仓库没有可构建产品或硬件目标。

## 兼容性、发布与回滚

- 新增值是向后兼容扩展；`standard` 默认值和既有 `light`、`standard` 行为保持不变。
- 不迁移既有 PRD，不新增持久化字段；旧任务继续按原值运行。
- 本子任务不更新 `VERSION`、历史 canonical 对象、版本 manifest、结构迁移链、README 或接入指南。这些内容由父任务固定最后一项统一生成 1.2 升级补丁。
- 实施按“门禁与测试”“Skill/workflow”“Agent/Hook”“合约测试”分批；若某批验证失败，只回退该批任务内改动，不覆盖用户已有工作树改动。
