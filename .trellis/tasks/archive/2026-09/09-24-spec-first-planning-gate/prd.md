# 模板规划门禁加固：spec 前置读取与 start 机械校验（仅模板）

## Workflow Settings

- Review level: reinforced

## Spec References

- `.trellis/spec/main/tooling/templates-and-docs.md` — :14 面向下游的缺陷修复默认只改 `templates/embedded-c-overlay/`（用户决定按此默认执行）；:16 单向约束"改模板不反向同步根目录"；:17 契约测试优先落在模板内；:18 manifest/版本号/README/接入指南只归发布收尾任务 → 本任务排除。
- `.trellis/spec/main/tooling/python.md` — :9-12 脚本分层（共享逻辑在 common/）；:74 cwd 必须是模板根否则误读 workflow.md；:105 教训"只做文本层断言不走真实 CLI"；:111-112 测试写法约定；:139 根级工具修复需单独任务授权（本任务不碰根目录，符合）。
- `.trellis/spec/main/tooling/overlay-upgrade.md` — :124 live 模板与 manifest 漂移 → 安装/升级 fail closed；:133-135 模板正文变化须由发布收尾任务提升 VERSION 并重生成 manifest → 本任务不触碰。
- `.trellis/spec/shared/trellis-maintenance.md` — :17 planning_gate.py 是受保护项目定制（模板侧同样受保护，有意修改允许）；:28-36 复核命令思路适用于模板侧等价物。
- `.trellis/spec/shared/validation.md` — 验证命令全集与 pass/fail/not run/not applicable 报告格式。
- `.trellis/spec/guides/index.md` — Pre-Modification Rule（改前必搜）；Code Reuse 触发器（复用既有 helper 而非新写）。

## Goal

把"规划不读 spec 也能收敛并通过 start 门禁"的缺陷在**发布模板**中修复，使下游项目获得：
1. spec 发现程序前置为 Phase 1.1 证据路径的强制第一步（文本层）；
2. `task.py start` 规划门禁新增两项机械校验：prd.md `## Spec References` 存在性 + implement/check jsonl 真实条目（硬层）。

**根目录零改动（用户明确决定）**：本仓库自身工作流实例的同源缺陷不在本任务修复。

## Background / Confirmed Facts

- **事故（修复动机）**：本仓库 09-22-task-dir-time-prefix 规划全程未读 spec——把 AGENTS.md:15 单向同步误读为双向、把 `templates-and-docs.md:14-17` 已回答的问题抛给用户、implement/check jsonl 只有种子行仍到 planning_ready=true。该缺陷源自模板与根目录共用的工作流设计，模板中同样存在。
- **门禁缺口（模板侧，与根目录当前逐字节相同）**：`planning_gate.py:58-110` 只校验 meta 标记、Review level、Planning Convergence 四字段；brainstorm SKILL.md:170 声称的"jsonl 须有真实条目才能 start"是纯散文，`cmd_start`（模板 task.py:99）未实现。
- **spec 发现程序错位**：完整发现流程只存在于 `trellis-before-dev`（Phase 2 触发）；模板 workflow.md 1.1、brainstorm/adapter SKILL 只有 "existing specs"/"relevant Specs" 软引用，无发现程序、无工件要求。
- **模板侧改动面（已逐一核实）**：
  - brainstorm SKILL 模板仅 1 份发布副本：`.opencode/skills/trellis-brainstorm/SKILL.md`（模板 `.agents/.claude` 不发布该上游 Skill，由下游 `trellis init` 提供；新增受管路径归发布收尾，见 Out of Scope）。
  - adapter SKILL 模板 2 份：`.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` == `.opencode/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md`（实测零差异，改后保持）。
  - workflow.md（模板）：1.1 节（:407 起）、Guardrails、`[workflow-state:planning]` / `[workflow-state:planning-inline]` 块；逐轮注入的 planning 提示从这两个块逐字渲染，hooks/plugins 仅提取（grep 证实无测试钉住块文本）。
  - hook 提示文本 3 处：`.codex/hooks/session-start.py:~284`、`.claude/hooks/session-start.py:~396`、`.opencode/lib/session-utils.js:~256`；`test_review_profile_contract.py:285` 断言 hook 文本不得含 `validate_planning_gate`。
  - 可复用件（模板侧均有）：`task_store.py:150 _has_subagent_platform`（codex inline 不算）；`task_context.py:176` 种子行语义（真实条目 = 含 `file` 字段）；模板 task_store 不 import planning_gate（grep 核实，无循环依赖）。
  - `task.py:449-474` 的 jsonl 提示文本属 `init-context` 弃用守卫，与 cmd_start 无交互（已核实）。
- **模板内既存禁触区**：`[workflow-state:no_task]` 块、Guardrails "Phase 2 source edits" 条目、session-utils.js no-task 分诊段、Step detail 提示串（`.claude/hooks/session-start.py:725`、`session-utils.js:625`）、`task.py:466-469` 求助命令——前四处不属本任务；后三处是同胞任务 `09-24-template-platform-hint-and-step-text` 的目标。
- **同胞任务共享面**：与该同胞任务共享模板 3 文件（`.claude/hooks/session-start.py`、`.opencode/lib/session-utils.js`、`.trellis/scripts/task.py`）但**不同区域**；双方均未 start，无硬依赖，后实施者以内容 grep 重锚行号，互不触碰对方目标文本。
- **门禁行为描述文案分布（自查二/三轮核实）**：模板 workflow.md 1.4 :560-562 与 1.5 完成标准表（:570-584）、adapter SKILL intro 段（"only verifies…"）、brainstorm SKILL :170、**`.opencode/commands/trellis/start.md:55-60`（穷举式列出 prd.md 须含 Review level + Planning Convergence + planning_ready + 用户批准——三轮自查推翻二轮"commands 无需改动"结论：continue.md:12 措辞非穷举可不改，start.md 此处必须补两项新校验）**都在描述 start 门禁校验集——新校验上线后必须同步更新，否则文本与行为矛盾；grep 证实无测试钉住这些文案。
- **种子 prd 骨架缺节（三轮自查新发现）**：模板 `task_store.py:197-231 _default_prd_content` 为新任务预置 `## Workflow Settings`、`## Planning Convergence`（pending 值）等被门禁检查的节，但无 `## Spec References`——门禁上线后每个新建任务的种子 prd 天然缺节。按既有"被门禁检查的节都预置骨架 + pending 值"模式，种子须补该节头 + 填写指引注释（**不含列表项**：占位列表项会让校验 A 形式化通过，失去强制力）；grep 证实无测试钉住种子骨架文本。
- **hook planning 分支结构（三轮自查修正精度）**：两侧 session-start hook 与 session-utils.js 的 planning 状态各有**两个** return 分支（无 prd 分支 + 有 prd 分支），非单句；追加句须覆盖两个分支。
- **测试基线（自查二轮实测，2026-09-24）**：根套件 154 tests OK；模板套件 201 tests OK。实施后模板套件应为 201+新增用例，根套件保持 154 OK（根零改动证明）。
- **任务树**：本任务挂载于父任务 `09-17-trellisforge-1-3-upgrade`，固定收尾子任务保持 children 末位（已重排 + Task Map 已登记）。

## Requirements

- **R1 门禁（硬层，仅模板）**：
  - `templates/embedded-c-overlay/.trellis/scripts/common/planning_gate.py`：签名扩为 `validate_planning_gate(task_dir, repo_root=None)`；新增校验 A——prd.md 须含 `## Spec References` 节且节内至少一条 `^[ \t]*-[ \t]+` 列表项；新增校验 B——仅当 `repo_root is not None` 且 `_has_subagent_platform(repo_root)`（直接 import 该私有 helper，不改 task_store，避免新增分叉）为真时，`implement.jsonl` 与 `check.jsonl` 各须至少一条含非空 `file` 字段的 JSON 行；文件缺失或非空行解析失败 → 错误（fail closed）。未传 repo_root → 跳过校验 B（向后兼容既有调用）。
  - `templates/embedded-c-overlay/.trellis/scripts/task.py` cmd_start：门禁调用传入已有的 `repo_root`（:76）。
  - `templates/embedded-c-overlay/.trellis/scripts/common/task_store.py` `_default_prd_content`（:197-231）：种子骨架补 `## Spec References` 节头 + 填写指引注释（HTML 注释或说明行，**不含 `- ` 列表项**，保证未填写的种子被校验 A 如实拦截；与 Planning Convergence 种子 pending 值同模式）。
- **R2 spec 发现前置（文本层，仅模板 workflow.md）**：
  - 1.1 节：决策清点前插入 "Spec discovery (mandatory first evidence step)" 段（`--mode packages` → 相关 index → guideline 文件 → guides/index.md → 记入 prd.md `## Spec References`，无适用 spec 也必须写节显式声明）；Guardrails 加对应一条（锚在 "Planning must be persisted…" 条目后）。
  - `[workflow-state:planning]` 与 `[workflow-state:planning-inline]` 块：各加一句 spec 发现 + Spec References 持久化要求；"blocks unless convergence and subsequent approval markers are present" 句补 Spec References 与（子代理模式）策展后 jsonl，与新门禁行为一致。
  - **1.4 节（自查二轮新增）**：:562 的门禁拒绝条件枚举（"rejects planning tasks unless…"）补 Spec References 节与策展后 jsonl 两项，:560 尾句 "that tolerance is not a planning-ready state" 补"start 门禁拒绝种子-only"表述——否则门禁行为与文本失真；1.5 完成标准表加一行 `prd.md contains a ## Spec References section`。
  - **`.opencode/commands/trellis/start.md`（自查三轮新增）**：:55-60 planning 分支的穷举句（"must carry a Review level … and a ready ## Planning Convergence block … also requires planning_ready and …"）补 Spec References 与策展后 jsonl；不碰 --platform 示例行与 no-task triage 段（test_opencode_platform_contract 钉住前者、既存分叉属后者）。`continue.md:12` 非穷举措辞不改。
- **R3 SKILL 文本（仅模板）**：brainstorm `.opencode` 副本——Evidence Rule 与 Planning Flow step 2 的 "existing specs" 具体化为显式发现程序，Artifact Rules 的 prd.md 清单加 `## Spec References`，Quality Bar 加一条，:170 的 jsonl 句补 "(enforced by the start gate)"；adapter 2 份（正文同改、frontmatter 不动、两份保持零差异）——step 1 "relevant Specs" 具体化，step 7 收敛前置补 Spec References，**intro 段 "that gate only verifies the persisted convergence and approval markers" 的 "only" 表述更新为新校验集（自查二轮新增：否则 Skill 文本与门禁行为矛盾）**。
- **R4 Hook 提示文本（仅模板，3 文件 × 2 个 planning 分支）**：`.codex/.claude session-start.py` 与 `session-utils.js` 的 planning 状态**两个 return 分支**（无 prd / 有 prd）各追加一句"先读相关 `.trellis/spec/` 索引与指南并记入 prd.md `## Spec References`"；仅文本，不含门禁逻辑，不出现 `validate_planning_gate` 字样，不动 Step detail 提示串、no-task 段与其他状态分支。
- **R5 测试（仅模板）**：`templates/.../tests/test_planning_gate.py`：`READY_PRD` fixture 补 `## Spec References` 节（既有 7 用例断言不变；不补则校验 A 击穿 3 个期望通过用例——自查已证实）；新增：缺节/空节 → 拒绝；≥1 条 → 通过；种子-only + 有平台目录 → 拒绝；无平台目录 → 不因 jsonl 拒绝；真实条目 → 通过；未传 repo_root → 跳过 B；损坏 JSON 行 → 拒绝；**`_default_prd_content` 输出含 `## Spec References` 节头且不含占位列表项**（三轮新增，锁定种子骨架合同）。
- **R6 根目录零改动纪律**：根 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/`、`AGENTS.md` 全程只读；`git status` 中根侧唯一允许的变更是本任务目录与父任务挂载工件（已在规划期完成）。不把模板改动反向同步到根（templates-and-docs.md:16）。

## Out of Scope

- **根目录自身工作流实例的同源缺陷修复**（用户明确决定不改根目录）：根 planning_gate 仍无校验 A/B、根 skills/workflow/hooks 仍是软引用、根 AGENTS.md:15 歧义句保留。将来若要修，按 python.md:139 模式另开根级任务授权。
- `VERSION`、`history/`、manifest、`migrations/`、README、接入指南（overlay-upgrade.md:133、templates-and-docs.md:18 → v1.3 发布收尾任务）。
- 把 brainstorm 新增进模板 `.agents/.claude` 发布面（新增受管路径需 manifest + adoption-baseline，归发布收尾；下游 Claude/Codex 主会话经模板 workflow.md 1.1/state 块 + hook 文本获得同等约束，不留空洞）。
- 模板内既存禁触区（no_task 块、Guardrails Phase-2 条目、session-utils no-task 段、同胞任务目标行）。
- `planning-inline` 的门禁豁免现状变更（gate 仍只对 `status == "planning"` 生效；inline 任务受文本层要求但不被机械拦截——有意的文本/门禁不对称，不扩大授权面）。
- 09-22 任务工件：根目录门禁未变，它不受本任务影响。

## Acceptance Criteria

- [ ] 模板单测证明：planning 任务缺 `## Spec References` 或列表为空 → start 拒绝并报可读错误；含 ≥1 条 → 通过；既有 7 用例（fixture 补节后）全绿。
- [ ] 模板单测证明：子代理平台下 jsonl 仅种子行 → 拒绝；两文件各 ≥1 条真实条目 → 通过；无平台目录 → 不因 jsonl 拒绝；未传 repo_root → 跳过校验 B；损坏 JSON 行 → 拒绝。
- [ ] 以 workdir=`templates/embedded-c-overlay` 运行模板自己的 `python ./.trellis/scripts/get_context.py --mode phase --step 1.1`，输出含 spec 发现步与 Spec References 要求（真实 CLI，不做纯文本断言——python.md:74,105）。
- [ ] adapter 2 份副本改后正文零差异（frontmatter 除外）；3 处 hook 文件的两个 planning 分支语义一致；`[workflow-state:planning]`/`[workflow-state:planning-inline]` 块、workflow.md 1.4 :560-562、1.5 完成标准表、adapter intro、brainstorm :170、`.opencode/commands/trellis/start.md:55-60` 的门禁行为描述与新校验集一致（无 "only verifies" 类失真残留）。
- [ ] 种子骨架单测：`_default_prd_content` 输出含 `## Spec References` 节头且不含占位列表项（新建任务未填写时被校验 A 如实拦截）。
- [ ] 禁触区零改动：模板 diff 中不出现 no_task 块、Guardrails "Phase 2 source edits" 条目、session-utils no-task 段、Step detail 提示串、task.py:466-469。
- [ ] 模板套件 `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` 全绿（201 基线 + 新增用例，零既有用例破坏）；根套件 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` 只读回归 154 OK（与实测基线一致，证明根零改动无副作用）；`python -m py_compile` 覆盖模板改动的 .py；`node --check` 覆盖模板 session-utils.js；`git diff --check` 干净。
- [ ] `git status`：改动仅位于 `templates/embedded-c-overlay/` 所列文件 + 本任务目录；根 `.trellis/scripts/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/`、`AGENTS.md`、`history/`、`VERSION`、manifest、migrations 零改动。

## Decisions Log

- 用户：创建本任务修复"规划不看 spec"问题；规划时必须读取本仓库 spec（本 PRD Spec References 节即执行记录）。
- 用户：本任务挂载于父任务 `09-17-trellisforge-1-3-upgrade`（1.3 功能子任务，排在固定收尾之前）。
- **用户（本轮范围决定，覆盖此前"根+模板"方案）**：只改模板、根目录零改动。已知悉并接受其后果：本仓库自身规划缺陷保持原样（同类事故可能在根目录重演）、AGENTS.md 消歧取消、根↔模板新增分叉（见 Risks）。
- 用户（前序对话）：双机械门禁 + spec 前置的修复机制经两轮解释无异议。
- **用户（最新明确选择）**：Review level 由默认 standard 升级为 **reinforced**（affected-scope 独立审查；有阻塞发现则批修后派发全新 trellis-check 全范围复审，循环至零阻塞；无额外 commit-ready 审查）。
- 用户（Phase 3.3，实施+审查完成后）：批准一次**限定性根目录 spec 更新**（仅 `.trellis/spec/main/tooling/python.md` 新增"模板规划门禁 Spec 前置校验"Scenario + `index.md` 描述行；纯文档，不碰根目录任何脚本/Skill/hook/AGENTS.md）——R6"根目录只读"就此文档范围经用户授权豁免。
- 工程：门禁只做结构校验（节存在 + 非空列表 + jsonl 含 file 字段），内容真实性由 review 兜底（与 adapter"门禁不能证明判断正确"哲学一致）。
- 工程：planning_gate 直接 import 私有 `_has_subagent_platform`（同包内引用），不改 task_store——比"公开化更名"少一处模板改动面；repo_root 可选参数保证向后兼容。
- 工程：模板-only 后无跨侧镜像义务，但新增根↔模板分叉（planning_gate.py、test_planning_gate.py、workflow.md 1.1/Guardrails/state 块、brainstorm/adapter SKILL、3 处 hook 文本）——与分支既有"模板领先、根滞后"模式一致（journal Session 8、python.md:19,70,139），根侧回移留给将来单独授权的根级任务。
- 工程（批准前自查二轮修正 3 项）：① workflow.md 1.4 :562 门禁枚举与 1.5 完成标准表未列新校验 → 纳入 R2（否则文本与门禁行为失真）；② adapter SKILL intro "only verifies the persisted convergence and approval markers" 将变假 → 纳入 R3；③ brainstorm :170 jsonl 句补 "(enforced by the start gate)"。另实测两侧测试基线（根 154 OK / 模板 201 OK）写入验收；核实 commands/trellis/*.md 措辞非穷举、无需改动。
- 工程（批准前自查三轮修正 3 项）：① **推翻二轮"commands 无需改动"结论**——`.opencode/commands/trellis/start.md:55-60` 是穷举式门禁描述，纳入 R2（continue.md 仍不改）；② 种子 prd 骨架（`task_store._default_prd_content`）缺 `## Spec References` 节 → 补节头 + 指引注释、**不含占位列表项**（占位项会让校验 A 形式化通过），纳入 R1/R5；③ hook planning 提示实为每文件两个 return 分支（无 prd / 有 prd），R4 精度修正为"3 文件 × 2 分支"。

## Risks（用户已随范围决定接受）

- 本仓库自身工作流未修：根目录规划仍可全程不读 spec 收敛（09-22 式事故可在根目录重演）；根 AGENTS.md:15 歧义句保留。
- 根↔模板分叉扩大：模板改动扩大 live↔manifest 漂移（安装器 fail closed 至 v1.3 发布收尾重生成，分支既有模式）；同时 planning_gate 等 8 类文件根↔模板由零差异转为模板领先。
- 与同胞任务 `09-24-template-platform-hint-and-step-text` 共享模板 3 文件不同区域：后实施者以内容 grep 重锚，禁按规划期行号盲改。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
