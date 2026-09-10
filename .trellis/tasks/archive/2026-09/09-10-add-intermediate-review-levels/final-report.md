# 五档审查等级实施最终报告

任务: `09-10-add-intermediate-review-levels` · 执行计划 revision 1 ·
日期 2026-09-10 · 分支 v1.2-development(未提交,按策略禁止 commit/push/merge)

## 目标达成

下游发布模板 `templates/embedded-c-overlay/` 的审查等级由
`light|standard|strict` 扩展为固定强度顺序
`light < standard < reinforced < comprehensive < strict`;
审查范围(changed/affected/full-scope)、阻塞项修复后的独立复审闭环、
提交前 fresh 终审成为三个独立、可验证的维度。仅 `strict` 保留无条件
commit-ready fresh full-scope 终审;`comprehensive` 零阻塞后不追加轮次;
缺失/无效值仍回退 `standard`;`light`/`standard` 既有语义未变。

## 改动文件(全部位于模板内,10 改 + 1 新增)

| 文件 | 改动 |
|---|---|
| `.trellis/scripts/common/planning_gate.py` | 新增 `VALID_REVIEW_LEVELS` 五档常量,fail-closed 校验与错误消息引用五档集合 |
| `.trellis/scripts/tests/test_planning_gate.py` | 参数化五档全通过(subTest)、非法值错误消息含五档名、缺失 Workflow Settings 阻断;7 测试通过 |
| `.trellis/workflow.md` | Phase 1 两处面包屑与 planning-inline 派发句、in_progress/inline 面包屑、Claude/Codex Active Task Routing、Guardrails、Phase 2.2 两平台五档路由(新增 reinforced/comprehensive 条目、strict 闭环+终审引用、分批修复与证据失效规则)、Final pass、Phase 3.4 preamble(仅 strict 无条件 fresh commit-ready 终审);light/standard 文案保持原语义 |
| `.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` | 重写为五档权威契约:Scope Definitions、Profile Matrix、Reinforced/Comprehensive/Strict 新章节、Blocking-Finding Ownership、Evidence Invalidation、Independence And Degradation、Report Contract |
| `.agents/skills/__PROJECT_PREFIX__-trellis-review/agents/openai.yaml` | short_description 五档 |
| `.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` | 允许集合五档、默认 `standard`、不因 AI 风险判断升档 |
| `.trellis/agents/check.md` | Channel Check Agent:权威 Skill 引用五档、第 4 步五档路由+每轮完整重审、第 5 步四类修复所有权、报告增加 round/stage/blocking count |
| `.claude/agents/trellis-check.md` | Context 增加 prd `Review level` 与 review Skill 契约;新增 "Review Profile" 节(每档一轮语义、round/stage、旧轮"已修复"不作当前零阻塞证据);报告格式增加五字段 Profile 块;递归/生命周期边界未动 |
| `.codex/agents/trellis-check.toml` | description 五档;context 协议四档派发;profile contract 新增 reinforced/comprehensive、strict 改写为闭环+commit-ready 终审、full-scope 影响证据边界;输出格式增加 round/stage/blocking count |
| `.codex/hooks/inject-workflow-state.py` | 仅 auto/inline 两处提示文案三档→五档,无路由逻辑(Hook 边界由合约测试锁定) |
| `.trellis/scripts/tests/test_review_profile_contract.py`(新增) | 13 项静态合约断言:五名齐备于全部 9 个消费者、规范五值序列与强度顺序、reinforced↔affected-scope 循环、comprehensive↔full-scope 且无 commit-ready 轮、strict 闭环+fresh 终审且 preamble 中终审仅出现一次、默认回退 standard、三 Check Agent 报告五字段与 stage 取值、受管文件无旧三档枚举残留、Evidence Invalidation 契约、Hook 不含门禁/路由符号 |

共 10 files changed, 298 insertions(+), 52 deletions(-)(不含新增测试文件)。

## 阶段与检查证据(plan.py 审计日志)

| 阶段 | 检查 | 结果 |
|---|---|---|
| gate-extension | gate-unittest(模板 planning gate 7 测试) | pass |
| skills-workflow | five-level-scan-skills-workflow(4 文件五名批量 rg 断言) | pass |
| skills-workflow | diff-check(`git diff --check -- templates/embedded-c-overlay`) | pass |
| agents-hook | five-level-scan-agents(3 Agent + Hook 五名断言) | pass |
| agents-hook | hook-compile(临时 PYTHONPYCACHEPREFIX 下 py_compile,树内 0 个 __pycache__) | pass |
| contract-test | template-tests-full(模板全量 114 测试 OK) | pass |
| full-verify | root-regression(根目录自用 99 测试 OK,机制未受影响) | pass |
| full-verify | py-compile-sweep(模板 45 个 .py 全编译通过,无字节码残留) | pass |
| full-verify | residual-three-level-scan(rg 命中仅合约测试自身检测字面量,受管文案零残留) | pass |
| full-verify | forbidden-dirs-clean(根 `.trellis/workflow.md`、`.trellis/agents`、根 `planning_gate.py`、`.agents/skills`、`.claude`、`.codex` git status 为空) | pass |
| full-verify | diff-check-final | pass |

## 验收对照

- 五档合法值通过规划门禁、缺失/无效回退 standard、用户选择最高优先级 → gate-unittest + skills-workflow 扫描 + 合约测试。
- reinforced/comprehensive/strict 三档路由差异与复审循环 → workflow/Skill/三 Agent 文本 + contract 测试 13 项。
- 每层不回退、跨层一致 → `test_no_stale_three_level_enumerations`、`test_five_level_names_present_in_every_consumer`。
- 实现仅落模板、根目录未改 → forbidden-dirs-clean + `git status --short` 审计。

## 未运行 / 不适用项

- 构建、部署、硬件验证: `not applicable` — 本仓库为工作流模板仓库,不产出固件、可执行产品或硬件目标。
- 全仓库 `git diff --check`: 仅报派发前主会话已修改的 `.trellis/tasks/*/task.json` 等 CRLF 行尾(非本任务写入范围,未触碰);任务范围内检查为 pass。
- 真实多轮复审循环由下游项目运行时执行,本任务以文本合约 + 静态测试锁定语义(设计既定方案,不新增运行时状态机)。

## 剩余风险与后续

- 合约测试为精确字面量/子串匹配,未来改写受管文案时可能需要同步更新测试 needle(失败信息会指出漂移文件与缺失契约,属预期防护)。
- `comprehensive` 与 `strict` 的唯一固定差异(commit-ready 终审有无)已由 preamble 单发断言与 Skill 矩阵双重锁定。
- 发布收尾(`VERSION`、历史对象、manifest、迁移链、README、接入指南)按 PRD 归父任务最后一项 `09-10-readme-integration-guide-upgrade-patch`,本任务未触碰。
- 未执行 `git add`/`commit`/`push`/`merge`;等待主会话按 Phase 3 流程处理。
- 本任务 Review level: standard 的 affected-scope 独立审查已完成(round 1, stage implementation-loop):阻塞项 0;审查补齐「证据失效」测试覆盖(`test_evidence_invalidation_contract`),最终模板单测 114 OK,根目录回归 99 OK;无实质范围变化,可进入提交准备。
