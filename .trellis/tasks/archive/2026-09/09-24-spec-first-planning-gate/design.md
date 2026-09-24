# Design: 模板规划门禁加固（spec 前置 + start 机械校验，仅模板）

前置：任务状态 in_progress 后才实施；父任务 `09-17-trellisforge-1-3-upgrade`。**全部改动位于 `templates/embedded-c-overlay/`，根目录只读（用户决定）。**

## 边界与总体结构

两层修复，互为纵深，只落模板：

- **硬层（机械门禁）**：模板 `planning_gate.py` + `task.py cmd_start` + `test_planning_gate.py`。缺工件即拒绝 start。
- **软层（文本契约）**：模板 workflow.md（1.1 + Guardrails + 两个 `[workflow-state:*]` 块）、brainstorm SKILL ×1、adapter SKILL ×2、hook 提示文本 ×3。告诉代理何时、如何读 spec 并留下工件；逐轮注入的载体是 workflow.md state 块，hook 文本只覆盖 SessionStart/no-task 时刻。

## 改动面清单（模板内，行号为规划期锚点，实施时以内容 grep 重锚）

| 文件 | 位置 | 方式 |
|---|---|---|
| `.trellis/scripts/common/planning_gate.py` | 校验函数 | 加参数 + 校验 A/B；直接 `from .task_store import _has_subagent_platform`（模板 task_store 不 import planning_gate，grep 核实无循环） |
| `.trellis/scripts/task.py` | cmd_start :99 | 门禁调用传 `repo_root`（:76 已有该变量）；**不碰 :449-474 弃用守卫（同胞任务目标 :466-469）** |
| `.trellis/scripts/tests/test_planning_gate.py` | fixture + 新用例 | READY_PRD 补 Spec References 节；新增 7 组用例 + 种子骨架合同用例 |
| `.trellis/scripts/common/task_store.py` | `_default_prd_content` :197-231 | 种子骨架补 `## Spec References` 节头 + 指引注释（**不含 `- ` 列表项**——占位项会让校验 A 形式化通过；与 Planning Convergence 种子 pending 值同模式）；grep 证实无测试钉住骨架文本 |
| `.opencode/commands/trellis/start.md` | :55-60 planning 分支穷举句 | 补 Spec References 与策展后 jsonl；**不碰 --platform 示例行（test_opencode_platform_contract 钉住）与 no-task triage 段**；`continue.md:12` 非穷举措辞不改 |
| `.trellis/workflow.md` | 1.1（:407 起）、Guardrails、state 块、**1.4 :560-562 门禁枚举、1.5 完成标准表（:570-584）** | 节级插入/更新；adapter 名保持 `PROJECT_PREFIX-` 占位；**禁触：no_task 块、Guardrails "Phase 2 source edits" 条目、Loading Step Detail、2.1.x** |
| `.opencode/skills/trellis-brainstorm/SKILL.md` | Evidence Rule / Planning Flow 2 / Artifact Rules / Quality Bar | 软引用改显式程序 + 工件要求 |
| `.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` + `.opencode/` 同名副本 | Planning Integration step 1 / step 7 | 正文同改，两份保持零差异，frontmatter 不动 |
| `.codex/hooks/session-start.py`（:~284）、`.claude/hooks/session-start.py`（:~396） | planning 状态的**两个 return 分支**（无 prd / 有 prd） | 各加一句；不得出现 `validate_planning_gate`（test_review_profile_contract.py:285 红线）；**禁触 Step detail 提示串 :725（同胞任务目标）** |
| `.opencode/lib/session-utils.js` | :~256 两个 planning return（无 prd / 有 prd） | 同句；**禁触 no-task 段与 Step detail 提示串 :625（同胞任务目标）** |

根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/`、`AGENTS.md`：**零改动**（templates-and-docs.md:16 单向约束——改模板不反向同步根）。

## 门禁合同（硬层）

- 签名：`validate_planning_gate(task_dir: Path, repo_root: Path | None = None)`。
- **校验 A（Spec References）**：复用 `_markdown_section(prd, "Spec References")`；节缺失或节内无任何 `^[ \t]*-[ \t]+` 列表行（容忍缩进）→ 错误 `prd.md must contain a Spec References section listing consulted spec files (or an explicit none-applicable entry)`。只做结构校验，内容真实性由 review 兜底。无条件生效（不依赖 repo_root）。
- **校验 B（jsonl 真实条目）**：仅当 `repo_root is not None` 且 `_has_subagent_platform(repo_root)` 为真时执行。对 `implement.jsonl`、`check.jsonl` 各自：文件缺失 → 错误（种子本应在 create 时创建；缺失说明平台目录晚于任务创建出现，`add-context` 可补建）；逐非空行 `json.loads`，解析失败 → 错误（fail closed，python.md:134 不吞异常）；含非空字符串 `file` 字段的行计为真实条目（种子 `_example` 行无 `file` 字段，语义同 task_context.py:176）；真实条目 < 1 → 错误 `implement.jsonl must contain at least one curated entry; seed _example rows do not count`。
- **平台条件**：直接 import 私有 `_has_subagent_platform`（同包内引用；codex 显式 inline 不计入，现逻辑已如此）。不做公开化更名——少一处 task_store 改动面。
- **检查顺序**：两项校验追加进现有 errors 累积列表；`status != "planning"` 直通语义、既有四字段校验全部不变（planning-inline 豁免保持现状）。
- **Hook 红线**：所有 hook/lib 文本改动不得出现字符串 `validate_planning_gate`。

## 文本合同（软层）

- **workflow.md 1.1**：开头 "Load trellis-brainstorm…" 段后插入 "Spec discovery (mandatory first evidence step)" 段：`get_context.py --mode packages` → 相关包 index → index 指向的 guideline 文件 → `.trellis/spec/guides/index.md` → 已读清单与适用约束记入 prd.md `## Spec References`（无适用 spec 时也必须写节并显式声明）。Guardrails 节加对应一条（锚在两侧一致的 "Planning must be persisted…" 条目后）。
- **`[workflow-state:planning]` / `[workflow-state:planning-inline]` 块**（逐轮注入的真实来源，hooks/plugins 仅逐字提取渲染；grep 证实无测试钉住块文本）：各加一句 spec 发现 + `## Spec References` 持久化要求；"blocks unless convergence and subsequent approval markers are present" 句补上 Spec References 与（子代理模式）策展后 jsonl，使文本与新门禁行为一致；其余行不动。
- **workflow.md 1.4 / 1.5（门禁行为描述同步，自查二轮新增）**：1.4 :562 "rejects planning tasks unless…" 枚举补 `## Spec References` 节与（子代理平台）策展后 jsonl 两项；:560 尾句补 "the start gate rejects missing or seed-only manifests"；1.5 完成标准表加一行 `prd.md contains a ## Spec References section with at least one entry | ✅`。grep 证实无测试钉住这些文案；`.claude/.opencode commands/trellis/*.md` 措辞非穷举式，不改。
- **brainstorm SKILL**（模板 `.opencode` 副本）：Evidence Rule 补显式发现程序句；Planning Flow step 2 的 "existing specs" 具体化为 "`.trellis/spec/` via `get_context.py --mode packages` → index → guideline files"；Artifact Rules 的 prd.md 清单加 `## Spec References` 项；Quality Bar 加一条（Spec References 已持久化）；:170 jsonl 句补 "(enforced by the start gate)"。
- **adapter SKILL**（2 份正文同改，frontmatter 不动，改后两份零差异）：Planning Integration step 1 "relevant Specs" 具体化为同一程序；step 7 收敛块前置条件补 "Spec References persisted"；**intro 段 "that gate only verifies the persisted convergence and approval markers" 更新为新校验集**（convergence/approval 标记 + Spec References + 策展后 jsonl），保留 "cannot prove that an AI classified every decision correctly" 的告诫。
- **hook 提示文本**（3 文件 × 2 个 planning return 分支）：无 prd 分支与有 prd 分支各追加一句 `Read the relevant .trellis/spec indexes and guideline files before the decision inventory, and persist consulted specs in prd.md under "## Spec References".`；不动 no-task 分诊段、其他状态分支与 Step detail 提示串（同胞任务目标）。
- **种子 prd 骨架**（`task_store._default_prd_content`）：在 `## Workflow Settings` 与 `## Goal` 之间（或 Goal 后）加 `## Spec References` 节头 + 一行指引注释；不加列表项——校验 A 要求 ≥1 条 `- ` 项，未填写的种子必须被如实拦截（与 Planning Convergence 种子写 pending 值同一设计哲学：骨架预置、通过靠实填）。
- **`.opencode/commands/trellis/start.md`**（:55-60）：planning 分支穷举句补 "a `## Spec References` section" 与（子代理平台）"curated jsonl manifests"；保留既有 --platform 示例与 triage 段原样。

## 兼容性

- 既有测试以 `validate_planning_gate(task_dir)` 调用（无 repo_root）→ 跳过校验 B；但校验 A 无条件生效，`READY_PRD` fixture 须补 `## Spec References` 节（既有 7 用例断言不变，补 fixture 后应全绿——自查证实不补则 3 个期望通过用例击穿）。
- 文本/门禁不对称（有意）：`planning-inline` 任务在 state 块中同样被要求写 Spec References，但门禁豁免现状保持（gate 只对 `status == "planning"` 生效）——不扩大授权面。
- 主会话实施的影响面（用户问询后明确）：正式 inline 模式（codex `dispatch_mode: inline` → 状态 `planning-inline`）被 gate 状态短路完全豁免，行为不变；口头指定主会话实施但状态仍为 `planning` 的任务，校验 A/B 照常执行（gate 无任务级实施模式开关，仅有状态 + 仓库平台探测两层判断）——实施者需照常策展 jsonl，其中 implement.jsonl 在不派发实施代理时不被消费，属已接受的轻微冗余（防旁路优先；要零负担走正式 inline 配置）。本仓库根目录零改动，此影响仅适用于装了本模板的下游项目。
- 下游升级路径：本任务只改 live 模板正文，不动 manifest/对象；下游要拿到修复须等 v1.3 发布收尾重生成资产后走升级器（overlay-upgrade.md 电梯模型，正文一步直达三方合并）。下游**在飞任务**升级后走到 start 会被新校验拦截（prd 缺 Spec References 节 / jsonl 种子-only）——不豁免，补件即过（机械操作，与 09-22 在根目录的处境同理）。
- 测试基线（2026-09-24 实测）：根 154 OK / 模板 201 OK；实施后模板 = 201 + 新增用例，根保持 154 OK。
- 同胞任务 `09-24-template-platform-hint-and-step-text` 共享模板 3 文件（`.claude/hooks/session-start.py`、`session-utils.js`、`task.py`）不同区域：实施前 `git log/status` 确认其是否先合入；先合入则按最新文本重锚；互不触碰对方目标行（Step detail 提示串 :725/:625、task.py:466-469）。
- 根目录行为零变化：根 planning_gate/skills/hooks/workflow.md 不动，根任务（含 09-22）不受本任务任何影响。

## Tradeoffs

- **模板-only（用户决定）**：下游得到修复，本仓库自身工作流缺陷保留（同类事故可在根目录重演、根 AGENTS.md 歧义保留）；换取根目录零风险与更小的审查面。根侧回移将来按 python.md:139 模式另开任务。
- 新增根↔模板分叉（planning_gate、gate 测试、workflow.md 三处、SKILL 三类、hook 3 处）：与分支既有"模板领先"模式一致，回移欠账记入 Risks。
- 门禁只验结构不验真伪：可审计的自证 + review 兜底；语义级校验不可行。
- planning_gate import 私有 helper：同包内引用，换取 task_store 零改动；若将来根侧回移需公开化，届时一并处理。
- 不向模板 `.agents/.claude` 新增 brainstorm 发布面：新增受管路径需 manifest + adoption-baseline（templates-and-docs.md:18 归发布收尾）；下游 Claude/Codex 主会话经 workflow.md 1.1/state 块 + hook 文本获得同等约束，不留空洞。

## Rollback

- 硬层（步骤 1）与软层（步骤 2-4）相互独立，可分别 `git checkout -- templates/embedded-c-overlay/<paths>` 回滚。
- 根目录零改动 → 本仓库工作流行为不变，回滚无运行态影响；无数据迁移、无状态机字段变更（gate 只新增校验项）。
