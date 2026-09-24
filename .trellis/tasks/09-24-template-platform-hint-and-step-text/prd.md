# 模板 Step detail 平台提示串与 task.py 步骤文案修复

父任务：`09-17-trellisforge-1-3-upgrade`（本任务是 1.3 功能子任务，排在固定收尾子任务之前）。
前置任务：`09-21-codex-native-wait-quiet`（已归档；它修好了模板 `.codex/hooks/session-start.py` 的提示串与提取器可达性，本任务补齐同一链条上剩下的模板侧文案缺陷）。

## Workflow Settings

- Review level: standard

## Goal

只改发布模板 `templates/embedded-c-overlay/`：让三平台的 SessionStart "Step detail" 提示串各自带上正确的 `--platform`，修掉 `task.py` 打印的必然失败的 `--step 1` 求助命令，并补防漂移断言，使下游模型无论照提示串还是照命令文档执行都走到同一条被过滤的步骤上下文路径。**本任务不动根目录自用 Trellis 实现**（用户决定）。

## Background（实测证据，2026-09-24）

### B1. 三份 Step detail 提示串只有一份带 `--platform`

- `templates/embedded-c-overlay/.codex/hooks/session-start.py:470`：`... --mode phase --step <X.Y> --platform codex`（09-21 已修，有 `test_codex_native_wait_contract.py:242` 锁定）。
- `templates/embedded-c-overlay/.claude/hooks/session-start.py:725`：`... --mode phase --step <X.Y>`（**无 platform**）。
- `templates/embedded-c-overlay/.opencode/lib/session-utils.js:625`：`... --mode phase --step <X.Y>`（**无 platform**）。
- 后果：`common/git_context.py:92` 只在传了 `--platform` 时才调用 `filter_platform`。照提示串执行 → 拿到**未过滤**输出（`[Claude Code]` / `[Codex]` / `[OpenCode]` 三平台块混排，且裸标记行原样保留）；照命令文档执行（`.claude/commands/trellis/continue.md:10` 传 `--platform claude`、`.opencode/commands/trellis/start.md:34` 传 `--platform opencode`）→ 拿到过滤后的输出。同一平台两条路径行为不一致。
- 无任何测试断言三份提示串的一致性：mirror 类测试只比对 skill 文件（`test_trellis_channel_contract.py:78`、`test_opencode_platform_contract.py:234`、`test_review_profile_contract.py:220`），`test_opencode_platform_contract.py:219/224` 只断言 OpenCode **命令文档**里的 `--platform opencode`，不涉及 hook / lib 提示串。所以 09-21 只改 Codex 那份造成的漂移没有被拦住。

### B2. `task.py` 打印的求助命令必然失败

- `templates/embedded-c-overlay/.trellis/scripts/task.py:466-469`：jsonl 为空时向 stderr 打印 `See .trellis/workflow.md planning artifact guidance or run:` + `  python ./.trellis/scripts/get_context.py --mode phase --step 1`。
- 实测（模板根）：`--mode phase --step 1` → `Step not found: 1`，**exit 2**。裸主版本号从不被 `get_step` 解析，且 09-21 新增的 `test_bare_major_numbers_stay_unresolved` 已把"裸编号仍 exit 2"锁死为合同行为。
- 即 CLI 自己推荐的求助命令 100% 失败，用户/模型照做只会看到报错。

### B3. 相关但不需要改的点（已核实）

- `templates/embedded-c-overlay/.trellis/workflow.md:361-366`：Loading Step Detail 已在 09-21 补上三平台 `--platform` 示例，本任务不再改。
- `.trellis/workflow.md:94`：`--mode phase --step <X.Y>  # detailed guide for a workflow step` 是仓库无关的泛型示例，其后紧接的 Loading Step Detail 已给出三平台口径。
- `.claude/commands/trellis/continue.md:7`、`.opencode/commands/trellis/continue.md:7`、`.opencode/commands/trellis/start.md:30`：这些是不带 `--step` 的 Phase Index 调用，平台过滤对 Phase Index 无意义（SessionStart 本就不过滤），不需要 `--platform`。
- `common/git_context.py:66/70` 的帮助文案已在 09-21 补 `2.1.1` 例子，本任务不再改。

## Requirements

### R1. 三平台 Step detail 提示串各自带正确 `--platform`

- `.claude/hooks/session-start.py:725` 的提示串补 `--platform claude`；`.opencode/lib/session-utils.js:625` 补 `--platform opencode`；`.codex/hooks/session-start.py:470` 保持 `--platform codex` 不回退。
- 三处都只改字符串字面量，**不改任何行为逻辑**（`_build_workflow_toc`、`collectOpenCodeTemplates`、注入流程、开关判断全部零 diff）。
- 平台名与各平台命令文档已有口径一致：Claude 用 `claude`（模板 `_platform_matches` 的 `claude ↔ claude-code / Claude Code` 家族别名已在 09-21 交付，故 `claude` 可正确渲染 `[Claude Code]` 块）、OpenCode 用 `opencode`、Codex 用 `codex`。

### R2. `task.py` 求助文案改为可解析的 step id

- `templates/embedded-c-overlay/.trellis/scripts/task.py:467` 的 `--step 1` 改为 `--step 1.1`。
- 工程决定（不再二选一）：用 `--step 1.1` 而非退回 `--mode phase`（Phase Index），因为该提示出现在"jsonl 为空、需要规划指引"的语境，语义上要指向步骤级详情；`1.1` 是 Phase 1 的第一个实质步骤（Requirement exploration and Grill Me），且与 `workflow.md:362` 的既有示例一致。
- 不改该提示的其余文案与 stderr 流向，不改 `task.py` 任何其他行为。

### R3. 防漂移断言

- 新增模板测试 `templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py`，至少覆盖：
  - 三份提示串各自含 `--mode phase --step <X.Y> --platform <claude|codex|opencode>`，且**互不串平台**（Claude 那份不含 `--platform codex` / `--platform opencode`，其余同理）；
  - 提示串仍保留 `Full guide: .trellis/workflow.md` 与 `Step detail:` 结构（避免只断言旗标而丢失文案形状）；
  - `task.py` 源码中出现的每个 `--step <id>` 提示都能被模板 `get_step(<id>)` 解析为非空（用进程内导入或真实 CLI 子进程，二者择一并在测试里写明），并断言不再出现裸 `--step 1`；
  - `workflow.md` 的 Loading Step Detail 仍含三平台示例（把 09-21 的口径钉住，防止后续再次漂移）。
- 测试写法沿用模板既有约定：`REPO_ROOT = Path(__file__).resolve().parents[3]` / `SCRIPTS_DIR = parents[1]`，子进程 `[sys.executable, "-B", ...]` 带 `cwd=str(REPO_ROOT)`、`env` 补 `PYTHONIOENCODING=utf-8`、`encoding="utf-8", errors="replace"`、固定 `timeout`；不得硬编码 `templates/embedded-c-overlay`；不得真实 spawn / wait agent。
- 工程决定：放新文件而不是塞进 `test_opencode_platform_contract.py`，因为断言跨 Claude / Codex / OpenCode 三平台与 `task.py`，超出"OpenCode 平台合同"测试的职责边界。
- 在模板 `TEMPLATE-CONTENTS.md` 按既有表格行格式登记该新测试文件一行（标注 1.3 新增）。

### R4. 变更边界与回归

- 允许写入：`templates/embedded-c-overlay/.claude/hooks/session-start.py`、`.opencode/lib/session-utils.js`、`.trellis/scripts/task.py`、`.trellis/scripts/tests/test_step_detail_platform_hints.py`（新增）、`TEMPLATE-CONTENTS.md`（登记一行）、本任务目录。
- 禁止写入：根目录 `.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`（用户明确决定本任务不动根自用实现）；`VERSION`、`history/`、manifest、结构迁移链、README、接入指南（固定收尾子任务负责）；模板 `workflow_phase.py`、`io.py`、`git_context.py`、`workflow.md`、`.codex/hooks/session-start.py`（09-21 已交付，不得回退或重构）；并行窗口的 `09-22-task-dir-time-prefix` 与用户既有脏改动（`.opencode/package.json`、`09-17-readme-integration-guide-upgrade-patch/prd.md`）。
- 回归：模板全量测试全绿（现 201 例 + 本任务新增用例）；09-21 的 24 例合约测试仍绿；改动的 Python 文件 `python -m py_compile` 通过；`.opencode/lib/session-utils.js` 的改动由既有 Node harness 测试覆盖，若本机 Node 不可用则报告 `not run` 并说明，不得记假 pass；`git diff --check` 无输出；构建 / 部署 / 硬件验证 `not applicable`（本仓库不产出固件或可执行产品）。

## Acceptance Criteria

- [ ] AC1: 模板三份 Step detail 提示串各自含正确旗标 —— `.claude/hooks/session-start.py` 含 `--mode phase --step <X.Y> --platform claude`、`.codex/hooks/session-start.py` 含 `... --platform codex`（未回退）、`.opencode/lib/session-utils.js` 含 `... --platform opencode`；三者互不串平台。
- [ ] AC2: 三处改动都是纯字符串 diff（`git diff` 中不出现任何逻辑行、函数签名或控制流变化）。
- [ ] AC3: 模板 `task.py` 的求助提示为 `--step 1.1`，不再含 `--step 1`；该 id 经模板 `get_step` 解析为非空、真实 CLI `--mode phase --step 1.1` 在模板根退出码 0。
- [ ] AC4: 新增 `test_step_detail_platform_hints.py` 覆盖 R3 的四组断言并全绿；`TEMPLATE-CONTENTS.md` 已按既有格式登记该文件一行。
- [ ] AC5: 模板全量测试全绿（报告用例数，应 ≥ 201 + 新增）；`test_codex_native_wait_contract.py` 23 例与 `test_write_json_lf.py` 1 例仍绿；改动的 Python 文件 `py_compile` 通过；Node harness 相关测试 pass 或明确报告 `not run` 及原因。
- [ ] AC6: `git diff --check` 无输出；功能改动只出现在 `templates/embedded-c-overlay/`（外加任务目录）；根目录 `.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`、`tools/`、`docs/`、`README.md`、`VERSION`、`history/` 零 diff；用户既有脏改动与并行窗口任务未被触碰或回滚。

## Out Of Scope

- **根目录自用 Trellis 实现的全部同步**（用户决定）：根 `.trellis/scripts/common/workflow_phase.py` 的旧 `_STEP_HEADING_RE` 与缺失的平台家族别名、根 `.trellis/workflow.md` 的 `#### 2.1.1` 不可达与 Loading Step Detail 缺平台示例、根 `.claude/hooks/session-start.py` 与 `.opencode/lib/session-utils.js` 的提示串、根 `.trellis/scripts/task.py:467` 的同一失效文案、根 `.trellis/scripts/common/io.py` 的 `write_json` CRLF、以及是否把 `#### 2.1.2` 原生静默等待合同移植到根 `workflow.md`。
- 仓库内 12 个仍为 CRLF 的 `task.json` 与 `.gitattributes` 的 eol 策略（属根仓库资产，且新增 `.gitattributes` 到模板会牵动 manifest 与结构链，归固定收尾子任务）。
- `VERSION`、canonical 对象库、版本 manifest、结构迁移链、README、接入指南、升级补丁。
- Channel worker 运行时、`trellis channel` 行为、`#### 2.1.1` 正文。
- Codex CLI、用户级 `~/.codex/config.toml`、`multi_agent_v2` 等待超时配置。
- 新增 Hook / 插件注入通道（本任务只改既有提示串文案）。
- 并行窗口任务 `09-22-task-dir-time-prefix` 与用户既有脏改动。

## Technical Notes

- 唯一权威事实源（只读）：`templates/embedded-c-overlay/.claude/hooks/session-start.py:725`、`.opencode/lib/session-utils.js:625`、`.codex/hooks/session-start.py:470`、`.trellis/scripts/task.py:466-469`、`.trellis/workflow.md:94/361-366`、`.claude/commands/trellis/continue.md:7/10`、`.opencode/commands/trellis/{start.md:30/34/64,continue.md:7/10}`、`common/git_context.py:66/70/92-96`、`common/workflow_phase.py:185-212`（家族别名，09-21 交付）。
- 归档参照：`.trellis/tasks/archive/2026-09/09-21-codex-native-wait-quiet/`（`design.md` §3.4 送达入口、§3.6 测试写法约定；`final-report.md` 残余风险 3、4 即本任务范围）。
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
