# 审查模板增加主会话严重度复核规则

## Workflow Settings

- Review level: reinforced

## Spec References

- `.trellis/spec/main/tooling/templates-and-docs.md` — 下游缺陷只改 `templates/embedded-c-overlay/`；根目录自用 Trellis 只读；版本号/history/README 属发布收尾。
- `.trellis/spec/main/tooling/index.md` — 开发前检查与质量命令（模板 unittest / py_compile / `git diff --check`）。
- `.trellis/spec/guides/index.md` — Pre-Modification Rule：改退出条件文本前必须搜全模板消费者。
- `.trellis/spec/shared/validation.md` — 验证结果按 pass/fail/not run/not applicable 报告。
- `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_profile_contract.py` — 五级 profile、镜像逐字节、报告字段、既有断言子串。
- `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_fix_ownership_contract.py` — Ownership 节禁写派发/加轮次短语。

## Goal

修复 `templates/embedded-c-overlay/` 审查契约的结构性缺口：主会话把独立审查
Agent 报告中的 blocking/major/minor 标签当作最终事实，循环退出只读报告的
`Blocking findings count` / “newest independent report”。当 Agent 把触碰安全、
正确性或验收标准的问题错标为非 blocking 时，主会话不会升级，审查循环带着
实质上的 blocking 缺陷退出。

目标：在模板层确立“审查 Agent 的严重度只是信号，主会话必须按绝对门槛独立
复核定级；退出主语是复核后的 adjudicated count”，并把该规则锁进契约测试。

## Background / Confirmed Facts（仓库证据）

- 缺口三要素（模板内文件）：
  - 退出条件只看报告的 blocking 数：Skill Profile Matrix :50-52、Reinforced
    :110-113、Comprehensive :129-132、Strict :145-155；
    `.opencode/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` 为逐字节镜像。
  - “Verify before routing”（SKILL.md:167-169）只核实真实性与任务归属，不复核
    严重度。
  - Common Baseline（SKILL.md:268-269）与 Strict（156-157）已声明绝对门槛，但
    没有任何流程步骤纠正 Agent 的错误标签。
- `Finding count and severity are signals only`（SKILL.md:213-214）目前只用于
  修复归属路由，不覆盖退出判定。
- 严重度标签生产方（均在模板内）：
  `templates/embedded-c-overlay/.trellis/agents/check.md`、
  `templates/embedded-c-overlay/.claude/agents/trellis-check.md`、
  `templates/embedded-c-overlay/.codex/agents/trellis-check.toml`、
  `templates/embedded-c-overlay/.opencode/agents/trellis-check.md`。
- 主会话退出消费方（`templates/embedded-c-overlay/.trellis/workflow.md`）：
  - 逐轮注入主路径：`[workflow-state:in_progress]` :244、
    `[workflow-state:in_progress-inline]` :272。
  - Claude / OpenCode / Codex 子代理权威 profile 区：:756-772
    （“newest independent report shows zero blocking findings”）。
  - Codex inline 副本：:825-827。
  - Final pass / Phase 3.4 preamble：:835、:871。
- 既有契约测试：
  `test_review_profile_contract.py` 锁定镜像一致（220-226）、报告字段
  （245-253）、五级枚举、以及 `zero blocking` /
  `` `reinforced`: dispatch an independent affected-scope `` 等子串；
  **不**钉死 `newest independent report`。
  `test_review_fix_ownership_contract.py:227-232` 禁止 Ownership 节出现
  `dispatch a fresh Check Agent` / `an extra review round`。
- Spec 归属：`.trellis/spec/main/tooling/templates-and-docs.md:12-22`。用户
  明确：“只修改模板，禁止动根目录 trellis”。

## Explicit User Decisions

1. 本会话不处理原下游任务的 Major-1/2/3，只修模板防复发。
2. 为本问题创建 Trellis 任务（已存在：`09-27-review-severity-readjudication`）。
3. 修改范围仅限 `templates/embedded-c-overlay/`；禁止改根目录 Trellis。
4. 主会话应独立判断哪些 finding 属于 blocking、哪些属于小问题，不得全盘接受
   审查 Agent 的标签。
5. 本轮只修正规划产物，不实施；不另开新任务。

## Requirements

- R1 主会话严重度复核：在审查 Skill 新增 `## Severity Adjudication`（置于
  `## Evidence Invalidation` 前）。主会话在 “Verify before routing” 确认真实
  性与归属后，对每条仍开放的 finding 按绝对门槛独立重定级：
  - 命中（触碰安全、正确性或验收标准）→ 无论 Agent 标 major/minor/high/medium/low
    均升级为 blocking，计入本轮 adjudicated blocking count。
  - 未命中 → 主会话可把 Agent 错标的 blocking 降为非 blocking，记 residual
    risk 与理由；不得把命中门槛的 finding 降级或记为 residual risk。
  - Ownership 节只引用该规则，不在该节写入派发/加轮次语句。
- R2 退出主语：所有循环 IF/until 与 “zero blocking” 退出判定的主语改为
  “主会话按 Severity Adjudication 复核后的 adjudicated blocking count”。
  Agent 报告的 `Blocking findings count` 与 “newest independent report” 是信号，
  不是最终事实。必须改写真正驱动循环的句子（见 AC2 清单），不得只在远处加声明。
- R3 再审调度保持五级语义，不因升级另造一轮规则：
  - `light`：主会话重跑失败/直接受影响的检查。
  - `standard`：主会话验证修复；**不**因升级自动再派独立 Check Agent，除非
    Evidence Invalidation 触发。
  - `reinforced` / `comprehensive` / `strict`：升级后的 blocking 进入该
    profile 既有 blocking-fix 循环，修完后派发新一轮独立审查，直到
    adjudicated count 为零（`strict` 的 commit-ready final 同样以复核后计数为准）。
- R4 契约测试：新增
  `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_severity_adjudication_contract.py`，
  锁定 Skill 新节、镜像一致、循环退出主语、workflow 主路径句、4 个 Agent 定级规则。
- R5 范围：只写 `templates/embedded-c-overlay/`；不更新版本号、history/、
  migrations/、README、接入指南。本任务挂到
  `09-17-trellisforge-1-3-upgrade`，收尾子任务仍最后。
- R6 Agent 侧定级门槛：模板内 4 个 Check Agent 定义在分类/定级步骤中要求：
  触碰安全/正确性/验收标准的失败必须标 blocking 并计入
  `Blocking findings count`，不得降级为 high/medium/low 或 major/minor；并注明
  主会话仍会独立复核。Agent 定义中的 “until blocking findings are zero”
  描述的是主会话调度，须改为指向 adjudicated count，避免生产端继续暗示
  “报告数为零即退出”。

## Resolved Decisions

- Q1（范围 = 双侧）：Skill 双镜像 + `workflow.md` + 模板内 4 个 Check Agent。
- Q2（再审，工程默认，保留五级矩阵）：升级后走该 profile **既有** blocking-fix
  路径；`standard` 不因本次规则新增第二轮独立审查。
- Q3（降级，落实用户决策 4）：复核双向。绝对门槛命中必须升级且不可豁免；
  未命中允许把 Agent 的 blocking 降为非 blocking 并记录理由。
- Q4（改写深度，纠正原稿“少改两句声明”）：循环 IF/until 原句必须改主语；
  远处声明不能替代 244/272/756-772 与 Skill 循环正文。既有断言子串
  `zero blocking` 等在改写后仍须保留。

## Acceptance Criteria

- [ ] AC1 审查 Skill（`.agents` 权威副本与 `.opencode` 镜像逐字节一致）含
      `## Severity Adjudication`；signals-only 扩展到退出判定；Verify before
      routing 引用该节且 Ownership 节不含 `dispatch a fresh Check Agent` /
      `an extra review round`。
- [ ] AC2 下列退出/循环句的主语是 adjudicated count，不再把
      “newest independent report” / 报告 blocking 数当作最终事实：
      - Skill Profile Matrix :50-52；
      - Skill `## Reinforced` :110-113、`## Comprehensive` :129-132、
        `## Strict` :145-155；
      - Skill :220-222（non-blocking 不触发再审：以复核后标签为准）；
      - workflow :244、:272（逐轮注入）；
      - workflow :756-772（子代理权威 profile 区，含 :758 “If the report has
        blocking findings”）；
      - workflow :825-827、:835、:871（inline / final pass / preamble）。
- [ ] AC3 模板契约测试通过：
      `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`，
      含新测试文件；新测试至少锁定 244/272/756-761 退出主语与 Skill 循环 IF/until。
- [ ] AC4 `git status` 证实本任务改动全部位于 `templates/embedded-c-overlay/`
      （任务目录除外）；根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、
      `.opencode/` 无本任务改动；`git diff --check` 通过。
- [ ] AC5 模板内 4 个 Check Agent 均含“安全/正确性/验收失败必须标 blocking、
      不得降级”，且其“until zero”表述指向主会话复核后的计数；报告字段测试不回归。
- [ ] AC6 `test_review_profile_contract.py`、`test_review_fix_ownership_contract.py`
      全绿；`standard` 的“exactly one independent review / no repeat unless
      evidence is invalidated”语义不被改写。
- [ ] AC7 本任务已作为 `09-17-trellisforge-1-3-upgrade` 的非收尾子任务挂上，
      `09-17-readme-integration-guide-upgrade-patch` 仍在 children 末位。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes

## Out of Scope

- 原下游任务中 Major-1/2/3 的实际修复与重审。
- 根目录自用 Trellis 工作流同步。
- 版本号、history 对象库、结构迁移链、README/接入指南。
- 改变五级 profile 的审查范围、独立派发次数或 commit-ready 门（除退出主语）。
- 运行时脚本 / `plan.py` / Hook 逻辑（纯散文与静态测试）。
