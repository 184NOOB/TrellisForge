# Python 工作流脚本

## 适用范围

Python 代码主要位于 `.trellis/scripts/`、`.claude/hooks/` 和 `.codex/hooks/`，用于任务生命周期、执行计划、上下文注入和回归测试。脚本使用 UTF-8，兼容 Windows PowerShell 调用方式。

## 实际模式

- 共享逻辑放在 `.trellis/scripts/common/`，入口脚本负责参数解析和调用；例如 `task.py` 使用任务存储层，执行计划由 `plan.py` 调用 `common/execution_plan.py`。
- 任务状态、执行计划和审计日志通过已有 CLI 推进，不直接手工改写状态字段。活动任务隔离由 `common/active_task.py` 和 `common/task_store.py` 维护。
- Hook 读取标准输入 JSON，输出可注入上下文；不要在 Hook 中执行产品构建或隐式修改工作树。
- 文本文件显式使用 UTF-8 读写并保留简体中文内容；命令示例必须能在 Windows PowerShell 中解释。

## Scenario: 模板执行计划 live 指针、完成态原地重开与 sequel

### 1. Scope / Trigger

- Trigger: 下游模板在有 `plan.py sequel` 与 live 计划解析之外，还允许同一 live 计划在全部完成（含 terminal report）后原地 `revise` 补加/重开步骤并重跑验收。任务可顺序持有多份闭环计划；命令签名、指针 JSON、冻结目录、完成态重开（`task_reopened`）和错误矩阵都是跨层合同（CLI / `execution_plan.py` / workflow / 各平台 Agent / Hook）。
- 合同目前只存在于 `templates/embedded-c-overlay/`。根目录自用 `.trellis/scripts/` 尚未同步（既没有 `cmd_sequel`，也没有完成态原地重开），不得把模板行为写成根目录已经具备的事实，也不得以"同步"名义回改根侧。

### 2. Signatures

- `python .trellis/scripts/plan.py [--task <path>] sequel --reason "..."`（兼容命令：冻结全完成的 live 计划并另开一本）
- `python .trellis/scripts/plan.py [--task <path>] revise --reason "..."`（完成态默认出口；只重开 live，不创建 sequel）
- 现有 `validate|status|start|record|done|block|revise` 全部只作用于 live plan。
- `common.execution_plan.resolve_live_plan(task_dir) -> tuple[int, Path]`
- `common.execution_plan.cmd_sequel(repo_root, task_dir, reason) -> str`
- `common.execution_plan.effective_completion_events(events) -> dict[str, dict]`、`pending_sanctioned_reopens(events, plan) -> list[str]`；`cmd_revise` 在重导后若全部阶段均 `completed` 且唯一 `level=report`，把该 report 置 `pending` 并清 `verification_results`。

### 3. Contracts

- 无 sequel 时（第 1 份 / 旧布局）：任务根 `execution-plan.json` 是真实 schema-3 计划，含 `tasks`。
- 有 sequel 时：任务根 `execution-plan.json` 仅为指针 `{"schema": 3, "live": N}`，不含 `tasks`。live 文件在 `plans/<N>/execution-plan.json` 与 `plans/<N>/execution-events.jsonl`；对应 `final-report.md` 也在该目录。
- `plan_sequel` 事件写入**新** live 账本，字段 `from`、`to`、`reason`。冻结账本只读，不再追加。
- 全完成的 live plan 用 `revise` 原地重开：未改动的已完成阶段保持 `completed`（fingerprint 不变），唯一 terminal report 重置为 `pending` 并清 managed 字段；批准时 `plan_approved` 的同一原子写追加每个重开 id 的 `task_reopened` 事件，批准后的推进不依赖旧完成指纹。完成后大修不再要求 `sequel`；`sequel` 保留给「显式另开一本计划」的场景，冻结布局与只读语义不变。
- `cmd_validate` 完成态规则：仍生效完成集 = 按事件序 `task_completed` 置完成、后续 `task_reopened` 取回；仍 `completed` 的 id 必须匹配其**最后一次** `task_completed` 的 fingerprint；历史完成 id 从 `tasks` 消失仍拒绝；已重开的 id 只能是非 `completed`（通常 `pending`），手工再标 `completed` 拒绝；完成过的计划在重开期间先前 terminal report 必须仍在位、`level=report` 且 `pending`。
- Hook / OpenCode 插件只展示 live 状态，不推进状态，也不复制路径常量。

### 4. Validation & Error Matrix

- `--reason` 为空 -> 拒绝 sequel
- live 仍有未完成 phase，或缺少 terminal report / `plan_completed` -> 拒绝 sequel
- 指针缺 `live`、`live < 1`、混入 `tasks`、指向缺失目录、或 `plans/<n>` 自身又是指针 -> 全部变更命令 fail closed
- 冻结目录上的 `start|record|done|block|revise|validate` -> 拒绝
- 完成态 plan 的 report 改成普通阶段或再标 `completed` -> `validate` 拒绝（terminal report 必须保持 `level=report` 且 `pending`），不是 sequel 通道
- 已完成步骤仍标 `completed` 时改 guarded 正文 -> `validate` 拒绝 `rewritten after completion`；先重置为 `pending`（sanctioned 重开）才可改并重跑
- `revise` -> 只重开当前 live，不创建 sequel

### 5. Good/Base/Bad Cases

- Good: 旧单文件任务无需迁移即可 `validate` / `status` / 推进；全完成计划不跑 `sequel`、不新建任务，`revise` 补加新阶段、更新 report `depends_on` 后 `validate` 并重跑出新的 `final-report.md`。
- Base: 完成后 `sequel` 把第 1 份冻进 `plans/1/`，live 指针变为 2；第三次 `sequel` 得到 live 3。
- Bad: 计划未完成就 `sequel`；把完成态 report 改成普通阶段或手工再标 `completed` 冒充重开；损坏指针后继续 `start`。

### 6. Tests Required

- 模板 `test_execution_plan.py`：旧单文件兼容、完成后 `revise` 原地重开 report（pending + 清 managed 字段 + `reopened` 事件字段）、补加阶段后 `validate` 并重跑新 report、未改动 completed 保持且 fingerprint 校验、重开非 report 步骤可改正文、重开后手工再标 completed 拒绝、report 降级/再标 completed 拒绝、完成后 sequel 冻结（兼容）、未完成拒绝、第三次 sequel、损坏指针 fail closed、`status` 只详列 live、`revise` 不创建 sequel、sequel 回滚清掉空的 `plans/1/`。
- 模板 `test_small_patch_and_sequel_contract.py`：workflow / implement 协议含用户声明优先的小修门槛、阻塞修复默认小修、以及完成后原地 `revise` 完成态出口（不再写「完成后必须 sequel」）；Claude hook 完成后提示指向 `revise --reason`。

### 7. Wrong vs Correct

#### Wrong

为同一需求继续，先把已完成计划 `sequel` 封掉再开空白新本（冻结不是必需）；把完成态 report 改成普通阶段或手工再标 `completed`；或让 `plan.py` 自动判断一次编辑算不算小修。

#### Correct

小修（用户明确说小修/不走 `plan.py`，或满足四条客观门槛；阻塞修复默认如此）不碰已完成计划文件。同一需求的补加/改步骤走 `plan.py revise --reason "..."` → 编辑 live 计划（report 保持 `pending`、`level=report`、传递覆盖全部阶段）→ `validate` → 重跑；`sequel` 仅在明确要另开一本计划时使用。

## Scenario: 模板等待合同可达性（子步骤归并 / 平台家族别名 / 送达入口）

### 1. Scope / Trigger

- Trigger: 写给某一平台主会话的合同（如 Codex 的 Channel 等待合同 `#### 2.1.1`、原生静默等待合同 `#### 2.1.2`）必须真正出现在该平台的步骤上下文里。"合同文本存在"不等于"合同送达"：文本 → 提取器 → 平台过滤 → 入口文案 → 测试是一条跨层链，任一环断了合同就等于没写。
- 合同目前只存在于 `templates/embedded-c-overlay/`。根目录自用 `.trellis/workflow.md`、`.trellis/scripts/common/workflow_phase.py`、`.trellis/scripts/common/git_context.py`、`.trellis/scripts/common/io.py` 尚未同步，仍存在子步骤截断与 `--platform claude` / `--platform codex` 丢块缺陷，不得把模板行为写成根目录已经具备的事实。

### 2. Signatures

- CLI：`python .trellis/scripts/get_context.py --mode phase --step <X.Y|X.Y.Z> [--platform claude|codex|opencode|...]`，**cwd 必须是模板根（下游即仓库根）**，否则会误读仓库根的 `workflow.md`。
- `common.workflow_phase.get_step(step_id) -> str`
- `common.workflow_phase.filter_platform(content, platform) -> str` / `_platform_matches(platform, block_names) -> bool`
- `common.workflow_phase.resolve_effective_platform(platform, config) -> str`
- `common.io.write_json(path, data) -> bool`

### 3. Contracts

- 步骤标题正则为 `^####\s+(\d+(?:\.\d+)+)\b.*$`，必须捕获完整编号：`get_step("X.Y")` 归并其全部 `X.Y.Z` 子步骤，`get_step("X.Y.Z")` 可独立定位；归属判定是 `candidate == step_id` 或 `candidate.startswith(step_id + ".")`。
- 起点优先精确匹配；只有在 `step_id` 含 `.` 时才允许退化到第一个 `step_id + "."` 前缀标题。裸编号 `1` / `2` / `3` 不得 fallback，仍返回空并由 CLI 退出码 2 表达。
- 正文终点：`## ` 开头、`---` 规则行、或**不属于**该 step 的 `#### ` 标题；无法解析编号的 `#### ` 行同样终止。不含子步骤的步骤输出必须逐字节不变。
- 平台家族别名在归一化（转小写、去 `-` / `_` / 空格）后生效：`codex ↔ {codexsubagent, codexinline}`（后两者互不别名）、`claude ↔ claudecode`；`opencode` 保持等值匹配；禁止跨家族别名。
- `filter_platform` 的唯一消费者是 `--mode phase`（`common/git_context.py`）。SessionStart 紧凑上下文由各平台 hook 自行抽取 Phase Index（`.codex/hooks/session-start.py` 的 `_build_workflow_toc`），不做平台过滤，因此别名改动不影响 SessionStart 注入。
- 空内容检查早于平台过滤：被过滤到只剩标题的子步骤仍退出码 0，标签块外的标题行必然保留。测试按"标题可见、正文不得泄露"断言，不得断言输出为空。
- 送达入口约定：`workflow.md` 的 `### Loading Step Detail` 必须给出 `--platform claude` / `--platform codex` / `--platform opencode` 三行平台中立示例（该段在 Phase Index 内、不做平台过滤，所以不能写成标签块）；三份 SessionStart Step detail 提示串必须各自带正确旗标——`.claude/hooks/session-start.py` 带 `--platform claude`、`.codex/hooks/session-start.py` 带 `--platform codex`、`.opencode/lib/session-utils.js` 带 `--platform opencode`。
- Codex 终端术语（`exec_command`、`write_stdin`、`yield_time_ms`、`session_id`）与原生术语（`spawn_agent`、`wait_agent`）只能出现在 `[Codex]` 块正文内；Claude / OpenCode 的过滤输出不得含这些术语正文。
- `write_json` 必须以 `newline="\n"` 打开临时文件，保证 Windows 上写出的 JSON 是 LF（见"常见错误"）。

### 4. Validation & Error Matrix

- `--step 2.1 --platform codex` 与 `--step 2.1`（不带 platform）都必须同时含 2.1.1 的 `write_stdin` 与 2.1.2 的 `wait_agent`；后者是下游 Codex 的真实调用形态。
- `--step 2.1 --platform claude` 必须含 `Spawn the implement sub-agent` 与 `trellis-implement`；`--platform claude-code`、`--platform opencode` 同样必须含派发指令。
- `--platform claude` / `claude-code` 的输出不得含上述 6 个 Codex 术语正文。
- `--step 2.1.1`、`--step 2.1.2` 退出码 0；`--step 2.2` 不含 2.1.x 内容；`--step 1|2|3` 退出码 2 且 stderr 含 `Step not found`。
- 别名矩阵：`[Codex]` 对 `codex-sub-agent` 与 `codex-inline` 都渲染；`[codex-sub-agent]` 与 `[codex-inline]` 互不渲染；`[Claude Code]` 对 `claude` 与 `claude-code` 都渲染；组合标记 `[Claude Code, codex-sub-agent, OpenCode]` 对 `codex-inline` 不渲染。
- 合同文本禁止项：全文不得出现 `"timeout_ms":30000` 形式的示例短窗口，`[Codex]` 块内不得出现 `yield_time_ms=30000`（`yield_time_ms=300000` 是 Channel 合同的固定窗口）。

### 5. Good/Base/Bad Cases

- Good: 新增 `#### X.Y.Z` 合同后无需改任何提取代码，`--step X.Y` 自动带上它，`--step X.Y.Z` 也能单独定位。
- Base: 只改合同文本时，真实 CLI 输出与别名矩阵测试立即反映送达结果。
- Bad: 用裸编号做主版本聚合；把平台术语写在标签块外；只做文本层断言（`assertIn` 读 `workflow.md` 原文）而不走真实 CLI —— 这正是 `test_trellis_channel_contract.py` 当初没拦住可达性缺陷的原因。

### 6. Tests Required

- 模板 `test_codex_native_wait_contract.py`：四个 TestCase 类分别覆盖真实 CLI 送达（`TestStepExtraction`）、进程内别名矩阵（`TestPlatformAlias`）、送达入口文案（`TestDeliveryEntry`）、2.1.2 冻结文本（`TestNativeWaitContractText`）。按类拆分是为了让分阶段实施能跑绿子集。
- 模板 `test_write_json_lf.py`：`write_json` 输出字节不含 `\r\n`、回读相等、无 `.tmp` 残留。
- 模板 `test_step_detail_platform_hints.py`：三份 SessionStart Step detail 提示串各自含 `--platform claude` / `codex` / `opencode` 且整文件级互不串平台；`task.py` 每个 `--step <id>` 提示经进程内 `get_step` 解析为非空（须 patch `common.workflow_phase.get_repo_root` 为模板根，避免在 TrellisForge 仓库根误读根 `workflow.md`），并用边界正则 `--step 1(?![.\d])` 禁止裸 `--step 1`；真实 CLI `--step 1.1` 在模板根退出码 0；Loading Step Detail 三平台示例为第二道锁。
- 测试写法约定：`REPO_ROOT = Path(__file__).resolve().parents[3]`（安装到下游后自然退化为仓库根，禁止硬编码 `templates/embedded-c-overlay`）；子进程 `[sys.executable, "-B", str(SCRIPTS_DIR / "get_context.py"), ...]` 带 `cwd=str(REPO_ROOT)`、`env={**os.environ, "PYTHONIOENCODING": "utf-8"}`、`encoding="utf-8", errors="replace"`、固定 `timeout`；不得真实 spawn / wait 任何 agent，也不得调用 `trellis channel`。
- 多用例 CLI 矩阵用可重放驱动脚本承载（先例：任务目录 `research/cli_matrix.py`，逐项打印 `PASS/FAIL <name>`、任一失败退出 1），并把脚本路径记进 `plan.py record` 的 `--command` / `--artifact`；PowerShell 5.1 会拆散内嵌引号的多语句命令，不要把它当作可重放的 command id。

### 7. Wrong vs Correct

#### Wrong

只在 `workflow.md` 里写 `[Codex]` 合同并断言文本存在，就认为 Codex 主会话会收到它。

#### Correct

同时验证五环：合同文本在标签块内、`get_step` 能提取到该编号、`filter_platform` 对该平台渲染该标签、平台入口文案真的会传 `--platform`、并有走真实 CLI 子进程的测试锁定送达结果。

## Scenario: 模板规划门禁 Spec 前置校验（Spec References / jsonl 真实条目）

### 1. Scope / Trigger

- Trigger: 下游模板给 `task.py start` 规划门禁新增两项机械校验（Spec References 存在性、jsonl 真实条目），签名、错误消息、种子骨架、平台条件与全套行为描述文本都是跨层合同（CLI / `planning_gate.py` / `task_store` 种子 / workflow.md / SKILL / command 文档 / hook 提示）。
- 合同目前只存在于 `templates/embedded-c-overlay/`。根目录自用 `.trellis/scripts/common/planning_gate.py` 尚未同步（根 gate 仍只查 meta 标记、Review level 与 Planning Convergence），不得把模板行为写成根目录已经具备的事实；根侧回移属根级工具修复、需单独任务授权。

### 2. Signatures

- `common.planning_gate.validate_planning_gate(task_dir: Path, repo_root: Path | None = None) -> PlanningGateResult`
- `common.planning_gate._missing_spec_references(prd: str) -> bool`、`_manifest_problem(name: str, path: Path) -> str | None`、`_SPEC_LIST_ITEM = re.compile(r"^[ \t]*-[ \t]+", re.MULTILINE)`（只在节体内匹配）
- 种子骨架：`common.task_store._default_prd_content` 含 `## Spec References` 节头 + HTML 注释指引，**不含 `- ` 列表项**
- 接线：模板 `task.py cmd_start` 把已解析的 `repo_root` 传入 gate；平台条件直接 import 私有 `_has_subagent_platform`（同包引用，task_store 不得反向 import planning_gate）

### 3. Contracts

- 校验 A（无条件，仅 `status == "planning"` 生效）：prd.md 须含 `## Spec References` 节且节内 ≥1 条列表项（容忍缩进）。只做结构校验，内容真实性由 review 兜底；HTML 注释内的 `- ` 行也计数，属已接受的可绕过面。
- 校验 B（仅 `repo_root is not None` 且 `_has_subagent_platform(repo_root)` 为真）：`implement.jsonl` 与 `check.jsonl` 各须 ≥1 条含非空字符串 `file` 字段的真实条目；种子 `_example` 行无 `file` 字段不计（语义同 `task_context.py`）。
- `repo_root` 缺省 → 校验 B 整体跳过（向后兼容旧调用方与既有测试），校验 A 不受影响。
- `status != "planning"`（含 `planning-inline`）直通语义不变；新校验追加进 errors 累积列表，不短路。
- 文本同步合同：workflow.md（1.1 Spec discovery 段、Guardrails、两个 `[workflow-state:planning*]` 块、1.4 门禁枚举、1.5 完成标准表）、`.opencode/commands/trellis/start.md` planning 分支、brainstorm SKILL、adapter SKILL intro（不得残留 "only verifies the persisted convergence and approval markers" 类失真）、3 个 hook 文件的两个 planning 分支，必须与 gate 实际校验集一致；hook/lib 文本不得出现字符串 `validate_planning_gate`（`test_review_profile_contract.py` 锁定）。

### 4. Validation & Error Matrix

- `## Spec References` 节缺失或节内无列表项 -> 拒绝，消息含 `must contain a Spec References section`
- jsonl 文件缺失 -> 拒绝（提示用 `task.py add-context` 补建；种子行不满足门禁）
- 非空行 JSON 解析失败 -> 拒绝 fail closed（`contains a line that is not valid JSON`）
- 种子-only（无真实条目）-> 拒绝（`must contain at least one curated entry; seed _example rows do not count`）
- `file` 字段为空串/非字符串 -> 不计为真实条目
- 无任何子代理平台目录，或仅 `.codex` 且显式 inline -> 不因 jsonl 拒绝
- 未传 `repo_root` -> 校验 B 跳过；task.json 缺失/损坏、非 planning 直通 -> 行为同旧版

### 5. Good/Base/Bad Cases

- Good: 新建任务的种子 prd 自带空 `## Spec References` 节；规划填写清单并策展 jsonl 后 start 通过。
- Base: 旧调用方不传 `repo_root` 只受校验 A 约束；inline-only 仓库自动豁免校验 B。
- Bad: 种子骨架写 `- TBD` 占位项骗过校验 A；新增校验后漏改 1.4 枚举 / adapter intro 造成文本失真；hook 文本引用 `validate_planning_gate`。

### 6. Tests Required

- 模板 `test_planning_gate.py`（18 例）：既有 7 例（`READY_PRD` fixture 补节、断言不变）+ 校验 A 3 例（缺节/空节拒绝、有条目通过）+ 种子骨架合同 1 例（`_default_prd_content` 含节头且无占位列表项）+ 校验 B 7 例（种子-only 拒绝、缺文件拒绝、策展通过、无平台跳过、未传 repo_root 跳过、损坏行拒绝、blank file 不计）。
- 送达验证必须以模板根为 cwd 跑真实 CLI（`get_context.py --mode phase --step 1.1` 输出含 Spec discovery 段），不得只做文本断言（见上一 Scenario 教训）。

### 7. Wrong vs Correct

#### Wrong

把新校验只写进 SKILL/workflow 散文（"must contain at least one real entry before start"）而不落 `planning_gate.py`；或为了"新任务顺畅过闸"在种子骨架里写占位列表项。

#### Correct

门禁在 `validate_planning_gate` 机械执行并由 `cmd_start` 传入 `repo_root`；种子骨架只给节头 + 注释指引，未填写的种子被如实拦截；所有描述门禁校验集的文本（workflow/state 块/1.4/1.5/start.md/SKILL/hook）与代码行为同步更新。

## Scenario: 模板任务目录时间前缀与同分钟错峰（MM-DD-HHmm）

### 1. Scope / Trigger

- Trigger: 发布模板任务目录前缀由 `MM-DD` 升级为 `MM-DD-HHmm` 并对同分钟创建自动错峰；前缀生成、--slug guard、错峰分配与文档表述是跨层合同（`paths.py` / `task_store.py` / `task.py` help / `workflow.md` / brainstorm SKILL / TEMPLATE-CONTENTS）。
- **有意分叉声明**:合同只存在于 `templates/embedded-c-overlay/`。根目录自用 Trellis 仍为 `MM-DD`——这是用户明确决定的分叉（任务 `09-22-task-dir-time-prefix`），**不是漂移**；不得以"同步"名义回改任何一侧,根侧升级需单独任务授权。

### 2. Signatures

- `common.paths.generate_task_date_prefix() -> str`:返回 `strftime("%m-%d-%H%M")`,纯函数、真实本地时间、不感知仓库状态。
- `common.task_store._allocate_task_prefix(tasks_dir, base_prefix) -> str`:同分钟错峰分配。
- guard 正则:`^(\d{2})-(\d{2})-(?:(\d{4})-)?(.+)$`,group(3)=HHmm(可空)、**group(4)=body**(旧代码 body 是 group(3),改造时两处使用点都要换)。

### 3. Contracts

- 目录名 `MM-DD-HHmm-slug`;guard 对比**真实时间 base 前缀**,错峰发生在 guard 之后、`dir_name` 组装之前。
- 错峰:占用 = `tasks_dir` 直接子目录(排除 `archive/`)名以 `candidate + "-"` 开头;候选 = `datetime(now.year, MM, DD, HH, mm) + timedelta(minutes=n)` 按 `%m-%d-%H%M` 格式化,n 从 0 取首个空闲;允许跨日(23:59 → 次日 `00:00`);防御上限 n<1440,耗尽回退 base(由既有 exists 警告兜底)。
- `task.json.createdAt` 保持 `%Y-%m-%d` 真实日期;顺延分钟只是排序记号,不是创建时刻。
- 排序语义:目录名排序 == 创建顺序 == 父任务 `children` 数组挂接顺序;`task.py list` 树视图本就按 `children` 数组显示子任务,与目录名无关。

### 4. Validation & Error Matrix

- `--slug` 含当日完整前缀(HHmm == 真实 base) -> 剥离 + 警告
- `--slug` 含当日旧格式 `MM-DD-` -> 剥离 + 警告
- `--slug` 非当日日期前缀,或 HHmm 合法但 ≠ base(今天另一任务的目录名) -> 报错退出、不建目录
- `--slug` HHmm 非法(时>23/分>59,如 `09-22-2461-foo`) -> 不拦截,按普通 slug 放行
- 同一分钟批量创建 -> 前缀依次 +1 分钟;预置占用目录被跳过

### 5. Good/Base/Bad Cases

- Good: 父任务同一分钟批量创建 3 个子任务,目录名顺序即挂接顺序,文件管理器视图与 list 视图一致。
- Base: 存量旧格式目录(`MM-DD-slug`)不迁移;与新目录同日混排时(字母开头 vs 数字 HHmm)旧目录靠后,已接受。
- Bad: 把根目录 `MM-DD` 当"漏改"回改;用错峰后的目录名分钟反推真实创建时刻(应读 `createdAt`)。

### 6. Tests Required

- 模板 `test_task_dir_time_prefix.py`:前缀格式(跨分钟容忍)、guard 四分支、错峰(连建 3 次 base/+1/+2、占用跳过、23:59 跨日、exists 防御分支)、排序契约;mock 密闭(patch `task_store.get_repo_root` / `run_git` / `resolve_default_branch` / `generate_task_date_prefix`,args 带 `assignee` 与 `no_start=True`,createdAt 只做格式断言)。

### 7. Wrong vs Correct

#### Wrong

发现根目录 `.trellis` 仍是 `MM-DD`,为"消除分叉"把根侧改成 HHmm,或把模板改回 `MM-DD`。

#### Correct

分叉是用户决定:模板侧合同由 `test_task_dir_time_prefix.py` 锁定;根侧升级只能由明确授权的根级任务执行,并各自保持测试与文档同步。

## Scenario: 模板单次派发走完执行计划链（链遍历义务 / 失败契约 / 链行）

### 1. Scope / Trigger

- Trigger: 模板把"一次 implement 派发 = 串行走完整条剩余 phase 链，直到终端 report phase `done`"与"做不下去必须 `plan.py block` + 结构化上报，静默空返回属协议违规"写进三平台共享文本（`execution_contract()` / `plan_protocol_block()` / `workflow.md` / 四份 implement 代理定义），并让 `format_status()`（`plan.py status` 与三平台 `<execution-plan>` 面包屑）显示本轮链。A/A'/B/C/D/E 的文本同步、parity 与"用户显式指令优先"例外都是跨层合同（CLI / `execution_plan.py` / workflow / 各平台 Agent / Hook）。
- 合同目前只存在于 `templates/embedded-c-overlay/`。根目录自用 `.trellis/scripts/`、根 `.trellis/workflow.md`、根三份代理定义与 hooks 尚未同步本次链遍历义务与链行，不得把模板行为写成根目录已经具备的事实；根侧回移属根级工具修复、需单独任务授权。
- 用户 2026-09-26 明确：主会话侧约束一律写成默认口径 + "用户显式指令优先"例外——主会话可自行实施，也可先写/批准 plan 再派发；不新增任何主会话"返回后 gate"或机械拦截通道。

### 2. Signatures

- `common.subagent_prompt_policy.execution_contract() -> str`：三平台共享派发合同唯一文本源（Claude/Codex hook import 取值；OpenCode 经 `--json` bridge）。
- `.opencode/lib/session-utils.js` `STATIC_EXECUTION_CONTRACT`：OpenCode 桥接失败时的静态兜底，必须与 Python 返回值逐字相等。
- `common.execution_plan.plan_protocol_block(repo_root, task_dir) -> str`：进行分支含中性 Chain duty。
- `common.execution_plan._dispatch_chain(plan: dict) -> list[str]`：本轮剩余链推导。
- `format_status(task_dir, repo_root, *, verbose=...)` 增 `dispatch chain: a -> b -> report` 行。
- `workflow.md` `[workflow-state:in_progress]` 块与 `#### 2.1` 派发范围句；`get_context.py --mode phase --step 2.1 --platform claude|codex|opencode` 为送达入口（cwd 必须是模板根）。

### 3. Contracts

- `execution_contract()` 追加段：一次派发拥有剩余整条链（`start -> 编辑（限 scope.write）-> 跑声明检查 -> record -> done`），不得在单个 phase `done` 后返回；`complete` 指终端 report phase `done`，不再是当前 phase 的 scope 完成；无法继续 → `plan.py block <id> --reason` + 结构化失败报告；静默空返回属违规；唯一另一种合法提前返回是上下文预算耗尽（先 `record`/`done` 当前 phase，再返回并列出剩余 runnable）。
- 共享合同文本不得包含双引号字符：JS 静态常量由"剥出双引号段再拼接"的 parity 正则读取，裸 `"` 会打破 Python ↔ `--json` bridge ↔ JS 三方逐字相等；`--reason` 占位用单引号 `'...'`。
- `plan_protocol_block()` 只在**进行分支**追加中性 Chain duty："A dispatched sub-agent must not return …"必须带 dispatched 限定，并含"主会话即实施者（Codex inline 或用户显式要求实施/先写 plan）时同一链遍历与失败上报义务适用"句；完成分支不得出现该短语（既有 `assertNotIn "Per phase loop"` 同时保持）。
- `workflow.md`：246 行主语为 `By default the implement sub-agent`；`Dispatch granularity (default)` 定义 round；`User instructions override these defaults` 例外含两个 `explicitly asks` 情形；`[workflow-state:in_progress-inline]`、`[codex-inline]` 与 2.1.2 冻结文本零 diff；`(or continue inline)` 保留。
- 四份 implement 代理定义（含 Codex TOML 与 channel worker 卡）共享短语：`Do not return after a single phase`、completion = 整个计划（`not the end of the current phase`）、报告两行 `Plan phases advanced:` / `Remaining runnable:`。
- `_dispatch_chain`：种子 = `in_progress` + runnable `pending`；沿反向邻接只纳入 `pending`/`in_progress`，`completed` 剪枝、`blocked` 剪枝且不穿过；Kahn 拓扑 + plan 声明序 tie-break；`allow_parallel_tasks=true` 输出整棵剩余森林；异常/畸形计划 fail soft 返回 `[]`。
- 链行只在链非空时输出、位于 verbose 分支之外（保证 `verbose=False` 面包屑可见）；不得含 `frozen plans:` 子串，不得模仿 `[<status 右对齐 12>] <id>` 行；全完成时由既有 `ALL TASKS COMPLETED` 行表达终态，不显示链行；既有 `next runnable` 行原样保留。

### 4. Validation & Error Matrix

- 单 phase `done` 后返回（零 diff、未 record、未 block）→ 协议违规（文本合同；无机械 gate，靠 2.2 审查与状态可见性兜底）
- 真受阻 → `block <id> --reason` + 结构化报告；预算耗尽 → 先收尾当前 phase 再报告剩余 runnable；两者不得混用
- 计划全完成，或无 `in_progress` 且无 runnable → 不显示链行
- 畸形计划、审计损坏、live 指针歧义 → `_dispatch_chain` 与 `plan_breadcrumb` 不抛异常，链行退化为不显示
- `--step 2.1` 输出只要求派发范围句与 `Spawn the implement sub-agent`；round 定义与例外句只属于 tag 块，不得断言到 2.1 输出

### 5. Good/Base/Bad Cases

- Good: 一次派发从当前 phase 串行走到终端 report `done`，`status`/面包屑每轮显示 `dispatch chain:`；真受阻时 block + 报告，主会话据审计决定 revise。
- Base: `allow_parallel_tasks=true` 有多个独立 runnable 时仍输出整棵剩余森林；legacy 与 sequel 布局下链行只描述 live 计划，且不与 `frozen plans:` 行混淆。
- Bad: 主会话按 phase 逐格派发；预算将尽时误用 `block` 把可用 phase 标成阻塞；把 round/例外断言到 `--step 2.1` 输出；给共享合同文本加双引号导致 JS parity 破裂。

### 6. Tests Required

- 模板 `test_dispatch_chain_contract.py`（新建，A–E）：`execution_contract()` 关键短语与动态三方 parity、协议块进行分支短语 + 完成分支 `assertNotIn`、`[workflow-state:in_progress]` 块 round/例外/246 default 主语 + 三平台真实 CLI 只锁 2.1 派发范围句、四份代理新短语与 Codex TOML 可解析、`_dispatch_chain` 推导矩阵（线性/菱形/blocked/completed/全完成/畸形/并行森林/声明序）与 `format_status` 链行（legacy/sequel/fail-soft）。
- 既有 4 个测试文件零改动、作为回归防线：`test_subagent_prompt_contract.py`（Python ↔ JS parity）、`test_execution_plan.py`（完成分支禁区、`frozen plans:`、verbose 行格式）、`test_small_patch_and_sequel_contract.py`（`IMPLEMENT_AGENTS` 四文件循环）、`test_codex_native_wait_contract.py`（2.1 送达与 `Spawn the implement sub-agent`）。
- 运行方式：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`。

### 7. Wrong vs Correct

#### Wrong

在 `workflow.md` 里定义 round 却只对 `--step 2.1` 做断言（该 step 抽不到 tag 块与 611 行）；把"不得返回主会话"写成无条件禁令（inline 主会话与用户显式要求场景被堵死）；把链行写进 verbose 分支（面包屑看不到）或复用字典序 runnable。

#### Correct

共享合同文本 Python/JS 同步并保持无裸双引号写法；协议块落进行分支且限定 dispatched 子代理；tag 块锁默认口径 + `explicitly asks` 例外；链行在 verbose 之外、拓扑序、fail soft，并保留既有 `next runnable` 行不动。

## 测试与示例

- 执行计划状态机的行为测试在 `.trellis/scripts/tests/test_execution_plan.py`。
- 规划门禁和会话隔离分别由 `.trellis/scripts/tests/test_planning_gate.py`、`.trellis/scripts/tests/test_active_task_session_isolation.py` 覆盖。
- 代理提示与 Hook 合同由 `.trellis/scripts/tests/test_subagent_prompt_contract.py` 覆盖。
- 模板侧的送达链路与换行合同由 `templates/embedded-c-overlay/.trellis/scripts/tests/test_codex_native_wait_contract.py`、`test_write_json_lf.py` 覆盖；运行方式 `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`。
- 模板任务目录时间前缀与同分钟错峰合同由 `templates/embedded-c-overlay/.trellis/scripts/tests/test_task_dir_time_prefix.py` 覆盖。

## 禁止事项

- 不用字符串拼接替代 JSON/结构化解析。
- 不吞掉异常或把不可执行的检查伪造为通过；应报告 `not applicable`，必要时用 `plan.py block/revise`。
- 不提交 `__pycache__`、`.pyc` 或 `.pyo`；模板安装器会主动拒绝这些缓存。

## 常见错误

- **Windows 下 `task.json` 变 CRLF 触发 `git diff --check` 尾随空白**：`common/io.py` 的 `write_json` 若用 `os.fdopen(fd, "w", encoding="utf-8")` 写文件（未传 `newline=`），Windows 文本模式把 `\n` 转成 `\r\n`，因此 `task.py`/`plan.py` 推进状态落盘的 `task.json` 等 JSON 会成为 CRLF。仓库 `core.autocrlf=false` 且 `.gitattributes` 无 JSON 换行规则，`git diff --check` 会把新增行的 CRLF 判为 `trailing whitespace` 报错。模板侧已根治：`templates/embedded-c-overlay/.trellis/scripts/common/io.py` 传 `newline="\n"`，由 `test_write_json_lf.py` 锁定；根目录自用 `io.py` 尚未同步，属根级工具修复、需单独任务授权。
- **规范化 CRLF 的 `task.json` 会产生一次性全文件换行 diff**：HEAD 中被跟踪的 13 个 `task.json` 全部是 CRLF（9 个 `execution-plan.json` 是 LF；全仓 375 LF / 23 CRLF）。把工作区文件转成 LF 后，`git diff` 会显示整文件行变化，而 JSON 语义差异可能只有一行。核对方式：把两侧都 `replace("\r\n", "\n")` 后再做 `difflib` 比较，确认只有预期内容变化；提交信息里要说明这是换行规范化。
