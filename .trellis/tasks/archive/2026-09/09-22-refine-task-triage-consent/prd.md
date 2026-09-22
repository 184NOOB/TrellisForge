# 细化任务创建询问的触发条件（仅示例模板）

## Workflow Settings

- Review level: standard

## Parent Task

- 父任务：`09-17-trellisforge-1-3-upgrade`（TrellisForge 1.3 Upgrade）。
- 本任务已作为功能子任务挂载，并插入在固定收尾子任务
  `09-17-readme-integration-guide-upgrade-patch` 之前，满足父任务
  `child_order_policy: terminal-child-last` 不变量（children 顺序已核验）。
- 与同级子任务相互独立，无前后依赖。

## Goal

仅修改发布模板 `templates/embedded-c-overlay/`，使其下游项目在「用户明确要写代码」
且「实施复杂」时才询问是否创建 Trellis 任务；对代码分析、问答、单文件小改直接开展工作，
不再每轮先打断询问。**不修改本项目根目录自用的工作流文件。**

## Background

模板的 `no_task` 文案、`/trellis:start` 命令与三平台 session 启动脚本当前都要求
"先分类本轮、再询问是否建任务"，下游用户做分析或小改动时被反复打断。作为 1.3 升级的
一项功能子任务，收紧模板侧触发条件。

## Confirmed Facts (repository evidence)

### 旧策略在模板内的分布（5 个文件）

- `templates/embedded-c-overlay/.trellis/workflow.md`：Phase Index、`### Request Triage`、
  `[workflow-state:no_task]` 块、自定义不变量行。
- `templates/embedded-c-overlay/.claude/hooks/session-start.py`：`_get_task_status` 的 NO ACTIVE TASK 分支。
- `templates/embedded-c-overlay/.codex/hooks/session-start.py`：同分支（Codex 版）。
- `templates/embedded-c-overlay/.opencode/lib/session-utils.js`：`getTaskStatus` 的 `base` 常量。
- `templates/embedded-c-overlay/.opencode/commands/trellis/start.md`："No active task" 款项。

模板**不发布** `trellis-start` skill（全仓仅项目根 `.agents/skills/trellis-start/SKILL.md` 一份），
故模板侧无 skill 改动。

### Spec 边界（`.trellis/spec/main/tooling/templates-and-docs.md`）

- L14/L15/L22：面向下游的新功能/行为调整**只改 `templates/embedded-c-overlay/`**；根目录
  `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 仅作只读参考，**不得反向修改**。
- L16：「改根目录须同步模板」是**单向**约束；规划必须分列"模板写入范围"与"根目录禁改范围"。
- L18：VERSION、历史对象、版本 manifest、结构迁移链、README、接入指南**只由发布收尾子任务更新**，
  普通模板功能子任务不得提前扩展。

### 发布资产现状与既定中间态（关键）

- `VERSION` = 1.2；`history/embedded-c-overlay/versions/` 仅有 1.0/1.1/1.2 manifest。
- 根级 `tests/test_overlay_tools.py::test_live_template_matches_12_manifest` **当前已 FAIL**：
  live 模板正文已偏离 1.2 canonical 对象（已实测复现，如 `.claude/agents/trellis-check.md`）。
  这是已完成的同级 1.3 功能子任务（`09-17-small-patch-and-sequel-plans`、
  `09-21-codex-native-wait-quiet`）改模板正文、按 spec 把 manifest 重生成留给收尾任务所形成的
  **预期中间态**。
- 同级 `09-21-codex-native-wait-quiet/final-report.md` 印证功能子任务的标准验证口径：
  模板全量套件 + 根 `.trellis/scripts/tests` 回归 + `py_compile` + `git diff --check`，
  且功能改动只落在 `templates/embedded-c-overlay/` 与任务目录，不碰 VERSION/manifest。
- 无任何测试断言被改的 triage 文案字符串（grep 确认）；模板 parity 测试仅校验同根内 skill 镜像
  字节一致，不涉及本次文件。

## Explicit User Decisions

- 只改示例模板，不改本项目根目录自用工作流文件。
- 本任务挂在 `09-17-trellisforge-1-3-upgrade` 父任务下。
- 复杂度判定：满足任一即"复杂"才询问——跨多文件 / 触及 workflow·Hook·契约机制 /
  需设计权衡或分步实施 / 影响发布模板；单文件局部小改、纯分析、问答一律直接做、不打断。
- 触发条件为 AND：明确要写代码 AND 复杂。

## Requirements

- R1：改写模板 `workflow.md` 的 Phase Index、`### Request Triage`、`[workflow-state:no_task]`
  块与不变量行，使"询问"仅在「明确写代码 + 复杂」时触发。
- R2：同步改写模板三平台 session 启动文案（claude / codex / opencode）的 NO ACTIVE TASK 分支。
- R3：同步改写模板 `/trellis:start` 命令的"No active task"款项。
- R4：5 个模板文件采用统一措辞，不分叉；保留 `[workflow-state:no_task]` 标签与结构/缩进。
- R5：根目录禁改范围零改动；VERSION/manifest/canonical 对象/结构迁移链/README/接入指南零改动（spec L18）。

## Key Decisions

- 范围限定模板侧（用户显式决策 + spec L14-16 强制）。
- 统一新措辞：默认句 + 询问条件句 + 拒绝处理句（见 design.md / implement.md）。
- 不新增模板测试文件：triage 文案是 AI 指引散文、无程序化消费者，用脆弱的字符串测试锁定
  反而增加维护成本；以"模板套件无回归 + grep 旧句缺席/新句在场 + standard 评审"保障。
- manifest/VERSION 重生成是发布收尾子任务 `09-17-readme-integration-guide-upgrade-patch`
  的职责（spec L18 + overlay-upgrade L133），本任务只交付正文，收尾任务从 live 模板整体重生成时
  自然纳入本改动。

## Acceptance Criteria

- [ ] AC1：模板 `no_task` 文案与 Request Triage 改为"默认直接干活、仅复杂编码才询问"。
- [ ] AC2：模板分析/问答/单文件小改指引为"直接开展工作、无 Trellis 提示"。
- [ ] AC3：模板 claude/codex/opencode 三处 NO ACTIVE TASK 文案与模板 workflow.md 策略一致。
- [ ] AC4：模板 `/trellis:start` 命令相应款项与新策略一致。
- [ ] AC5：`[workflow-state:no_task]` 标签完整；模板全量套件无回归（与改动前同为绿）。
- [ ] AC6：根 `.trellis/scripts/tests` 回归套件仍全绿；改动的模板 `.py` 过 `py_compile`、
      模板 `.js` 过 `node --check`（如有 node）；`git diff --check` 无输出。
- [ ] AC7：`git status` 功能改动只在 `templates/embedded-c-overlay/`（5 个文件）与本任务工件；
      根目录自用工作流文件、VERSION、`history/`、manifest、README、接入指南零改动。
- [ ] AC8：模板内 grep `ask only whether|Classify the current turn|First classify` 无残留，
      且新统一措辞在 5 个文件均在场。

## Out of Scope

- 不修改本项目根目录任何自用工作流文件（`.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`）。
- 不更新 VERSION、`history/embedded-c-overlay/` canonical 对象、版本 manifest、结构迁移链、
  README、接入指南（spec L18：发布收尾子任务专属）。
- 不试图让根级 `tests/test_overlay_tools.py::test_live_template_matches_12_manifest` 转绿
  （它是发布门禁，当前已因既定中间态为红，归收尾任务在 1.3 重生成 manifest 时恢复）。
- 不改注入机制、状态机、`task.py`/`plan.py` 逻辑或其它 `[workflow-state:*]` 块；不增删文件。

## Risks / Deferred

- 分叉影响（已知并接受）：只改模板意味着本项目自身会话仍保留旧"总是询问"行为；如需本仓库
  也生效，需另起子任务把同样改动同步到根目录文件（spec L16 单向约束，本次不处理）。
- 发布门禁依赖（交接给收尾任务）：本改动叠加 live 模板对 1.2 manifest 的预期漂移；
  `09-17-readme-integration-guide-upgrade-patch` 在 1.3 发布时 bump VERSION、用 `gen_migration.py`
  重生成 manifest+对象、`verify_assets.py` 校验后，live-manifest 一致性恢复。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
