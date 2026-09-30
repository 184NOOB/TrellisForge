# 模板 Step detail 平台提示串与 task.py 步骤文案修复

父任务：`09-17-trellisforge-1-3-upgrade`（本任务是 1.3 功能子任务，排在固定收尾子任务之前）。
前置任务：`09-21-codex-native-wait-quiet`（已归档；它修好了模板 `.codex/hooks/session-start.py` 的提示串与提取器可达性，本任务补齐同一链条上剩下的模板侧文案缺陷）。

## Workflow Settings

- Review level: reinforced

## Goal

只改发布模板 `templates/embedded-c-overlay/`：让三平台的 SessionStart "Step detail" 提示串各自带上正确的 `--platform`，修掉 `task.py` 打印的必然失败的 `--step 1` 求助命令，并补防漂移断言，使下游模型无论照提示串还是照命令文档执行都走到同一条被过滤的步骤上下文路径。**本任务不动根目录自用 Trellis 实现**（用户决定）。

## Background（实测证据，2026-09-24；行号与测试计数于 2026-09-25 在提交 `92d0c65` 上复核修正——09-24 之后合入的 `6e95dba`（spec-first-planning-gate）移动了 hook 行号并新增 `test_planning_gate.py`，实施时若行号再漂移，以内容锚点"Full guide: .trellis/workflow.md. Step detail:"这句唯一字符串重新定位）

### B1. 三份 Step detail 提示串只有一份带 `--platform`

- `templates/embedded-c-overlay/.codex/hooks/session-start.py:476`：`... --mode phase --step <X.Y> --platform codex`（09-21 已修，有 `test_codex_native_wait_contract.py:242` 锁定）。
- `templates/embedded-c-overlay/.claude/hooks/session-start.py:731`：`... --mode phase --step <X.Y>`（**无 platform**）。
- `templates/embedded-c-overlay/.opencode/lib/session-utils.js:625`：`... --mode phase --step <X.Y>`（**无 platform**）。
- 后果：`common/git_context.py:92` 只在传了 `--platform` 时才调用 `filter_platform`。照提示串执行 → 拿到**未过滤**输出（`[Claude Code]` / `[Codex]` / `[OpenCode]` 三平台块混排，且裸标记行原样保留）；照命令文档执行（`.claude/commands/trellis/continue.md:10` 传 `--platform claude`、`.opencode/commands/trellis/start.md:34` 传 `--platform opencode`）→ 拿到过滤后的输出。同一平台两条路径行为不一致。
- 无任何测试断言三份提示串的一致性：mirror 类测试只比对 skill 文件（`test_trellis_channel_contract.py:78`、`test_opencode_platform_contract.py:234`、`test_review_profile_contract.py:220`），`test_opencode_platform_contract.py:219/224` 只断言 OpenCode **命令文档**里的 `--platform opencode`，不涉及 hook / lib 提示串。所以 09-21 只改 Codex 那份造成的漂移没有被拦住。

### B2. `task.py` 打印的求助命令必然失败

- `templates/embedded-c-overlay/.trellis/scripts/task.py:465-469`：jsonl 为空时向 stderr 打印 `See .trellis/workflow.md planning artifact guidance or run:`（465 行）+ `  python ./.trellis/scripts/get_context.py --mode phase --step 1`（467 行）。
- 实测（模板根）：`--mode phase --step 1` → `Step not found: 1`，**exit 2**。裸主版本号从不被 `get_step` 解析，且 09-21 新增的 `test_bare_major_numbers_stay_unresolved` 已把"裸编号仍 exit 2"锁死为合同行为。
- 即 CLI 自己推荐的求助命令 100% 失败，用户/模型照做只会看到报错。

### B3. 相关但不需要改的点（已核实）

- `templates/embedded-c-overlay/.trellis/workflow.md:359-370`：Loading Step Detail 已在 09-21 补上三平台 `--platform` 示例（现位于 367-369 行，`6e95dba` 后行号有移动），本任务不再改。
- `.trellis/workflow.md:94`：`--mode phase --step <X.Y>  # detailed guide for a workflow step` 是仓库无关的泛型示例，其后紧接的 Loading Step Detail 已给出三平台口径。
- `.claude/commands/trellis/continue.md:7`、`.opencode/commands/trellis/continue.md:7`、`.opencode/commands/trellis/start.md:30`：这些是不带 `--step` 的 Phase Index 调用，平台过滤对 Phase Index 无意义（SessionStart 本就不过滤），不需要 `--platform`。
- `common/git_context.py:66/70` 的帮助文案已在 09-21 补 `2.1.1` 例子，本任务不再改。

## Requirements

### R1. 三平台 Step detail 提示串各自带正确 `--platform`

- `.claude/hooks/session-start.py:731` 的提示串补 `--platform claude`；`.opencode/lib/session-utils.js:625` 补 `--platform opencode`；`.codex/hooks/session-start.py:476` 保持 `--platform codex` 不回退。
- 三处都只改字符串字面量，**不改任何行为逻辑**（各自宿主函数零 diff：`.claude/hooks/session-start.py` 的 `_build_workflow_overview`（723-739 行）、`.opencode/lib/session-utils.js` 的 `buildSessionContext`（594 行起）、注入流程与开关判断；`.codex` 提示串宿主 `_build_workflow_toc` 位于禁写文件内，天然零 diff。注意：rev.2 曾误列 `collectOpenCodeTemplates`——它是上游 npm 包 `@mindfoldhq/trellis` 的函数（仅 collector parity 测试调用），不存在于模板源码，与本任务三个文件无关）。
- 平台名与各平台命令文档已有口径一致：Claude 用 `claude`（模板 `_platform_matches` 的 `claude ↔ claude-code / Claude Code` 家族别名已在 09-21 交付，故 `claude` 可正确渲染 `[Claude Code]` 块）、OpenCode 用 `opencode`、Codex 用 `codex`。

### R2. `task.py` 求助文案改为可解析的 step id

- `templates/embedded-c-overlay/.trellis/scripts/task.py:467` 的 `--step 1` 改为 `--step 1.1`。
- 工程决定（不再二选一）：用 `--step 1.1` 而非退回 `--mode phase`（Phase Index），因为该提示出现在"jsonl 为空、需要规划指引"的语境，语义上要指向步骤级详情；`1.1` 是 Phase 1 的第一个实质步骤（Requirement exploration and Grill Me），且与 `workflow.md:365` 的既有示例一致。
- 不改该提示的其余文案与 stderr 流向，不改 `task.py` 任何其他行为。

### R3. 防漂移断言

- 新增模板测试 `templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py`，至少覆盖：
  - 三份提示串各自含 `--mode phase --step <X.Y> --platform <claude|codex|opencode>`，且**互不串平台**（Claude 那份不含 `--platform codex` / `--platform opencode`，其余同理）。串平台断言可按整文件级做：已实测 `.claude/hooks/session-start.py` 与 `.opencode/lib/session-utils.js` 全文除待改提示串外**零**其他 `--platform` 出现，`.codex` hook 全文仅提示串（476 行）一处；
  - 提示串仍保留 `Full guide: .trellis/workflow.md` 与 `Step detail:` 结构（避免只断言旗标而丢失文案形状）；
  - `task.py` 源码中出现的每个 `--step <id>` 提示都能被模板 `get_step(<id>)` 解析为非空（用进程内导入或真实 CLI 子进程，二者择一并在测试里写明），并断言不再出现裸 `--step 1`（用边界正则 `--step 1(?![.\d])`，避免被 `--step 1.1` 的子串误报恒真；已实测模板 `task.py` 全文 `--step` 仅此一处，断言对象单一）；
  - `workflow.md` 的 Loading Step Detail 仍含三平台示例。注意：该口径已有第一道锁（`test_codex_native_wait_contract.py:229-238` 的 `test_loading_step_detail_names_all_three_platforms`），本断言是**刻意冗余的第二道锁**（跨文件防御，避免 09-21 合约测试被重构时丢锁），不是填补空白；B1 所述"无测试锁定"仅指 `.claude` / `.opencode` 两份 session-start 提示串本身。
- 测试写法沿用模板既有约定：`REPO_ROOT = Path(__file__).resolve().parents[3]` / `SCRIPTS_DIR = parents[1]`，子进程 `[sys.executable, "-B", ...]` 带 `cwd=str(REPO_ROOT)`、`env` 补 `PYTHONIOENCODING=utf-8`、`encoding="utf-8", errors="replace"`、固定 `timeout`；不得硬编码 `templates/embedded-c-overlay`；不得真实 spawn / wait agent。
- 工程决定：放新文件而不是塞进 `test_opencode_platform_contract.py`，因为断言跨 Claude / Codex / OpenCode 三平台与 `task.py`，超出"OpenCode 平台合同"测试的职责边界。
- 在模板 `TEMPLATE-CONTENTS.md` 按既有表格行格式登记该新测试文件一行（标注 1.3 新增）。

### R4. 变更边界与回归

- 允许写入：`templates/embedded-c-overlay/.claude/hooks/session-start.py`、`.opencode/lib/session-utils.js`、`.trellis/scripts/task.py`、`.trellis/scripts/tests/test_step_detail_platform_hints.py`（新增）、`TEMPLATE-CONTENTS.md`（登记一行）、根 `.trellis/spec/main/tooling/python.md`（仅限"送达入口约定"条目，见 R5）、本任务目录。
- 禁止写入：根目录 `.trellis/`（唯一例外：R5 的 spec 送达入口约定条目）、`.claude/`、`.codex/`、`.opencode/`、`.agents/`（用户明确决定本任务不动根自用实现）；`VERSION`、`history/`、manifest、结构迁移链、README、接入指南（固定收尾子任务负责）；模板 `workflow_phase.py`、`io.py`、`git_context.py`、`workflow.md`、`.codex/hooks/session-start.py`（09-21 已交付，不得回退或重构）；并行窗口的 `09-22-task-dir-time-prefix` 与用户既有脏改动（2026-09-25 实测为 `.opencode/package.json` 与 `09-22-task-dir-time-prefix` 的 5 个规划文件；该清单会随并行窗口漂移，实施时以开工前的 `git status` 快照为准，快照内的脏文件一律不得触碰或回滚）。
- 回归（三套件基线，均 2026-09-25 实测）：① 模板全量测试全绿（基线 212 例 + 本任务新增用例；原 201 基线已因 `6e95dba` 新增 `test_planning_gate.py` 过期），09-21 的 24 例合约测试仍绿；② 根目录套件 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` 全绿（基线 154 例；AGENTS.md 标准检查，且 R5 会改根 spec 文件，必须跑）；③ 仓库级 `tests/test_overlay_tools.py` 套件为**结构性红基线**（48 例、26 失败，全部源于 1.3 开发期活模板与 1.2 manifest 漂移触发安装器 fail-closed，归收尾子任务切 1.3 manifest 时收口；本任务改的 3 个模板文件已在基线漂移清单内，新测试文件与 `TEMPLATE-CONTENTS.md` 不在 1.2 manifest（151 项）中，不会扩大漂移面）——开工前与提交前各跑一次，**失败集合必须完全一致**，不得新增红项，也不得为"修绿"触碰 manifest / history / VERSION。其余：改动的 Python 文件 `python -m py_compile` 通过；`.opencode/lib/session-utils.js` 的改动由既有 Node harness 测试覆盖（harness 直接 import 该模块并执行 session-start 注入路径），若本机 Node 不可用则报告 `not run` 并说明，不得记假 pass；`git diff --check` 无输出；构建 / 部署 / 硬件验证 `not applicable`（本仓库不产出固件或可执行产品）。

### R5. Spec 收敛（Phase 3.3）

- 根 `.trellis/spec/main/tooling/python.md` 的"送达入口约定"条目（现 88 行）目前只要求 `.codex/hooks/session-start.py` 提示串带 `--platform codex`；本任务交付后事实变为三平台提示串各自带正确旗标，该条目须同步扩为三平台口径，防止 spec 落后于模板事实（09-21 Phase 3.3 有同类先例）。
- 只改该条目相关文字，不动 python.md 其他 Scenario；根自用实现仍未同步的事实表述（70 行"不得把模板行为写成根目录已经具备的事实"）保持原样，本任务的 spec 文字只描述模板合同。

## Acceptance Criteria

- [ ] AC1: 模板三份 Step detail 提示串各自含正确旗标 —— `.claude/hooks/session-start.py` 含 `--mode phase --step <X.Y> --platform claude`、`.codex/hooks/session-start.py` 含 `... --platform codex`（未回退）、`.opencode/lib/session-utils.js` 含 `... --platform opencode`；三者互不串平台。
- [ ] AC2: 三处改动都是纯字符串 diff（`git diff` 中不出现任何逻辑行、函数签名或控制流变化）。
- [ ] AC3: 模板 `task.py` 的求助提示为 `--step 1.1`，不再含**裸** `--step 1`（子串陷阱警示：`--step 1.1` 本身包含 `--step 1` 子串，断言必须用边界正则 `--step 1(?![.\d])` 或等价手段，朴素子串检查恒真无效）；该 id 经模板 `get_step` 解析为非空、真实 CLI `--mode phase --step 1.1` 在模板根退出码 0。
- [ ] AC4: 新增 `test_step_detail_platform_hints.py` 覆盖 R3 的四组断言并全绿；`TEMPLATE-CONTENTS.md` 已按既有格式登记该文件一行。
- [ ] AC5: 模板全量测试全绿（报告用例数，应 ≥ 212 + 新增，212 为 2026-09-25 实测基线）；`test_codex_native_wait_contract.py` 23 例与 `test_write_json_lf.py` 1 例仍绿；根目录套件 154 例全绿；`tests/test_overlay_tools.py` 失败集合与开工前基线（48 例、26 失败，1.3 漂移结构性红）完全一致、无新增；改动的 Python 文件 `py_compile` 通过；Node harness 相关测试 pass 或明确报告 `not run` 及原因。
- [ ] AC6: `git diff --check` 无输出；功能改动只出现在 `templates/embedded-c-overlay/`（外加任务目录与 R5 的 spec 条目）；除 R5 条目外根目录 `.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`、`tools/`、`docs/`、`README.md`、`VERSION`、`history/` 零 diff；用户既有脏改动与并行窗口任务未被触碰或回滚。
- [ ] AC7: 根 `python.md` 的"送达入口约定"条目已扩为三平台提示串口径，且该文件其余部分零 diff。

## Out Of Scope

- **根目录自用 Trellis 实现的全部同步**（用户决定）：根 `.trellis/scripts/common/workflow_phase.py` 的旧 `_STEP_HEADING_RE` 与缺失的平台家族别名、根 `.trellis/workflow.md` 的 `#### 2.1.1` 不可达与 Loading Step Detail 缺平台示例、根 `.claude/hooks/session-start.py` 与 `.opencode/lib/session-utils.js` 的提示串、根 `.trellis/scripts/task.py:467` 的同一失效文案、根 `.trellis/scripts/common/io.py` 的 `write_json` CRLF、以及是否把 `#### 2.1.2` 原生静默等待合同移植到根 `workflow.md`。
- 仓库内 12 个仍为 CRLF 的 `task.json` 与 `.gitattributes` 的 eol 策略（属根仓库资产，且新增 `.gitattributes` 到模板会牵动 manifest 与结构链，归固定收尾子任务）。
- `VERSION`、canonical 对象库、版本 manifest、结构迁移链、README、接入指南、升级补丁。
- Channel worker 运行时、`trellis channel` 行为、`#### 2.1.1` 正文。
- Codex CLI、用户级 `~/.codex/config.toml`、`multi_agent_v2` 等待超时配置。
- 新增 Hook / 插件注入通道（本任务只改既有提示串文案）。
- 并行窗口任务 `09-22-task-dir-time-prefix` 与用户既有脏改动。

## Technical Notes

- 唯一权威事实源（只读；行号以 2026-09-25 提交 `92d0c65` 实测复核为准，漂移时用内容锚点重定位）：`templates/embedded-c-overlay/.claude/hooks/session-start.py:731`、`.opencode/lib/session-utils.js:625`、`.codex/hooks/session-start.py:476`、`.trellis/scripts/task.py:465-469`（`See ...` 在 465、`--step 1` 在 467）、`.trellis/workflow.md:94/359-370`（三平台示例在 367-369）、`.claude/commands/trellis/continue.md:7/10`、`.opencode/commands/trellis/{start.md:30/34/66,continue.md:7/10}`、`common/git_context.py:66/70/92-96`、`common/workflow_phase.py:185-212`（家族别名，09-21 交付）。
- 归档参照：`.trellis/tasks/archive/2026-09/09-21-codex-native-wait-quiet/`（`design.md` §3.4 送达入口、§3.6 合约测试（含测试写法约定）；`final-report.md` 残余风险 3、4 即本任务范围）。
- 已核实无测试断言 `.claude` / `.opencode` 两份提示串的现有文本，因此改字符串不会打破既有断言；但 `test_opencode_platform_contract.py` 的 Node harness 会加载 `session-utils.js`，改后必须跑该测试确认无回归。
- 父任务 `children` 次序策略为 `terminal-child-last`：本任务创建时曾被追加到收尾子任务之后，已用 `remove-subtask` + `add-subtask` 修正；后续新增子任务都要复核该次序。
- 换行事实：`core.autocrlf=false`，`.gitattributes` 无 eol 规则，模板 `io.py` 已写 LF（09-21），故本任务不会新增 CRLF 噪声；`git diff --check` 仍需在提交前跑一次。
- 延后但未建任务的候选（按用户"候选先不建"）：根侧可达性同步、根 `io.py` 换行、根三份提示串、根 `task.py` 文案、12 个 CRLF `task.json` 与 `.gitattributes` 策略。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
- 已解决的用户决策：本任务范围限定为"只改模板、不动根目录 Trellis"（2026-09-24 用户明确回答），因此 `#### 2.1.2` 不移植到根 `workflow.md`，根侧 4 项缺陷全部出范围并记入 Out Of Scope 与延后候选。
- 已解决的工程决策：`task.py` 提示用 `--step 1.1`；新测试独立成文件；`workflow.md:94` 的泛型示例不加平台旗标；不带 `--step` 的 Phase Index 命令不加 `--platform`；不新增模板 `.gitattributes`。
- Revision: rev.4（rev.2：2026-09-25 规划自审第一轮，修正 `6e95dba` 合入导致的行号漂移（`.claude` hook 725→731、`.codex` hook 470→476、模板 `workflow.md` 361-366→359-370、示例 362→365、`task.py` 466-469→465-469、`start.md` 64→66）、测试基线 201→212、R3 第四组断言标注为第二道锁、§3.6 章节名对齐、R4 脏改动清单改为以实施时 `git status` 快照为准。rev.3：第四轮自审修正 R1 零 diff 保护名单的函数名张冠李戴（`.claude` 宿主实为 `_build_workflow_overview`、`.opencode` 宿主实为 `buildSessionContext`；`collectOpenCodeTemplates` 系上游 npm 包函数、不在模板源码，予以除名），并新增 R5/AC7——根 `python.md` 送达入口约定条目随本任务扩为三平台口径，R4 允许/禁止写入清单同步开定点例外。rev.4：第五轮自审补漏——R4/AC5 回归从单套件扩为三套件（模板 212 绿、根 154 绿、`tests/test_overlay_tools.py` 48 例 26 失败为 1.3 漂移结构性红基线，要求前后失败集合一致且禁止触碰 manifest/history/VERSION）；AC3 与 R3 修正"不再含 `--step 1`"的子串陷阱（须用边界正则 `--step 1(?![.\d])`）；R3 固化串平台断言的文件级安全性实测结论；同轮排查确认根 planning_gate 机械要求已满足、模板无第四处提示串、新文件不在 1.2 manifest。rev.5：用户决策 Review level 由 standard 改为 reinforced（审查循环为"独立审查→批量修 blocking→全新独立复审，直到零 blocking"，非固定轮数））
