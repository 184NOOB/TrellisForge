# Python 工作流脚本

## 适用范围

Python 代码主要位于 `.trellis/scripts/`、`.claude/hooks/` 和 `.codex/hooks/`，用于任务生命周期、执行计划、上下文注入和回归测试。脚本使用 UTF-8，兼容 Windows PowerShell 调用方式。

## 实际模式

- 共享逻辑放在 `.trellis/scripts/common/`，入口脚本负责参数解析和调用；例如 `task.py` 使用任务存储层，执行计划由 `plan.py` 调用 `common/execution_plan.py`。
- 任务状态、执行计划和审计日志通过已有 CLI 推进，不直接手工改写状态字段。活动任务隔离由 `common/active_task.py` 和 `common/task_store.py` 维护。
- Hook 读取标准输入 JSON，输出可注入上下文；不要在 Hook 中执行产品构建或隐式修改工作树。
- 文本文件显式使用 UTF-8 读写并保留简体中文内容；命令示例必须能在 Windows PowerShell 中解释。

## Scenario: 模板执行计划 live 指针与 sequel

### 1. Scope / Trigger

- Trigger: 下游模板新增 `plan.py sequel` 与 live 计划解析。任务可顺序持有多份闭环计划；命令签名、指针 JSON、冻结目录和错误矩阵都是跨层合同（CLI / `execution_plan.py` / workflow / 各平台 Agent / Hook）。
- 合同目前只存在于 `templates/embedded-c-overlay/`。根目录自用 `.trellis/scripts/` 尚未同步，不得把模板行为写成根目录已经具备的事实。

### 2. Signatures

- `python .trellis/scripts/plan.py [--task <path>] sequel --reason "..."`
- 现有 `validate|status|start|record|done|block|revise` 全部只作用于 live plan。
- `common.execution_plan.resolve_live_plan(task_dir) -> tuple[int, Path]`
- `common.execution_plan.cmd_sequel(repo_root, task_dir, reason) -> str`

### 3. Contracts

- 无 sequel 时（第 1 份 / 旧布局）：任务根 `execution-plan.json` 是真实 schema-3 计划，含 `tasks`。
- 有 sequel 时：任务根 `execution-plan.json` 仅为指针 `{"schema": 3, "live": N}`，不含 `tasks`。live 文件在 `plans/<N>/execution-plan.json` 与 `plans/<N>/execution-events.jsonl`；对应 `final-report.md` 也在该目录。
- `plan_sequel` 事件写入**新** live 账本，字段 `from`、`to`、`reason`。冻结账本只读，不再追加。
- Hook / OpenCode 插件只展示 live 状态，不推进状态，也不复制路径常量。

### 4. Validation & Error Matrix

- `--reason` 为空 -> 拒绝 sequel
- live 仍有未完成 phase，或缺少 terminal report / `plan_completed` -> 拒绝 sequel
- 指针缺 `live`、`live < 1`、混入 `tasks`、指向缺失目录、或 `plans/<n>` 自身又是指针 -> 全部变更命令 fail closed
- 冻结目录上的 `start|record|done|block|revise|validate` -> 拒绝
- 把已完成 report 改成普通阶段 -> `validate` 仍拒绝（防伪史，不是 sequel 通道）
- `revise` -> 只重开当前 live，不创建 sequel

### 5. Good/Base/Bad Cases

- Good: 旧单文件任务无需迁移即可 `validate` / `status` / 推进。
- Base: 完成后 `sequel` 把第 1 份冻进 `plans/1/`，live 指针变为 2；第三次 `sequel` 得到 live 3。
- Bad: 计划未完成就 `sequel`；手改已完成 report 冒充下一轮；损坏指针后继续 `start`。

### 6. Tests Required

- 模板 `test_execution_plan.py`：旧单文件兼容、完成后 sequel 冻结、未完成拒绝、第三次 sequel、损坏指针 fail closed、`status` 只详列 live、`revise` 不创建 sequel、已完成 report 仍不可改写、sequel 回滚清掉空的 `plans/1/`。
- 模板 `test_small_patch_and_sequel_contract.py`：workflow / implement 协议含用户声明优先的小修门槛、阻塞修复默认小修、以及 `sequel` 完成态出口。

### 7. Wrong vs Correct

#### Wrong

完成后把 `report` 改成普通阶段再 `revise`，或让 `plan.py` 自动判断一次编辑算不算小修。

#### Correct

小修（用户明确说小修/不走 `plan.py`，或满足四条客观门槛；阻塞修复默认如此）不碰已完成计划文件。同一需求的大修或过多冗杂复杂的阻塞修复才 `plan.py sequel --reason "..."`。

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
- 送达入口约定：`workflow.md` 的 `### Loading Step Detail` 必须给出 `--platform claude` / `--platform codex` / `--platform opencode` 三行平台中立示例（该段在 Phase Index 内、不做平台过滤，所以不能写成标签块）；`.codex/hooks/session-start.py` 的 Step detail 提示串必须带 `--platform codex`。
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
- 测试写法约定：`REPO_ROOT = Path(__file__).resolve().parents[3]`（安装到下游后自然退化为仓库根，禁止硬编码 `templates/embedded-c-overlay`）；子进程 `[sys.executable, "-B", str(SCRIPTS_DIR / "get_context.py"), ...]` 带 `cwd=str(REPO_ROOT)`、`env={**os.environ, "PYTHONIOENCODING": "utf-8"}`、`encoding="utf-8", errors="replace"`、固定 `timeout`；不得真实 spawn / wait 任何 agent，也不得调用 `trellis channel`。
- 多用例 CLI 矩阵用可重放驱动脚本承载（先例：任务目录 `research/cli_matrix.py`，逐项打印 `PASS/FAIL <name>`、任一失败退出 1），并把脚本路径记进 `plan.py record` 的 `--command` / `--artifact`；PowerShell 5.1 会拆散内嵌引号的多语句命令，不要把它当作可重放的 command id。

### 7. Wrong vs Correct

#### Wrong

只在 `workflow.md` 里写 `[Codex]` 合同并断言文本存在，就认为 Codex 主会话会收到它。

#### Correct

同时验证五环：合同文本在标签块内、`get_step` 能提取到该编号、`filter_platform` 对该平台渲染该标签、平台入口文案真的会传 `--platform`、并有走真实 CLI 子进程的测试锁定送达结果。

## 测试与示例

- 执行计划状态机的行为测试在 `.trellis/scripts/tests/test_execution_plan.py`。
- 规划门禁和会话隔离分别由 `.trellis/scripts/tests/test_planning_gate.py`、`.trellis/scripts/tests/test_active_task_session_isolation.py` 覆盖。
- 代理提示与 Hook 合同由 `.trellis/scripts/tests/test_subagent_prompt_contract.py` 覆盖。
- 模板侧的送达链路与换行合同由 `templates/embedded-c-overlay/.trellis/scripts/tests/test_codex_native_wait_contract.py`、`test_write_json_lf.py` 覆盖；运行方式 `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`。

## 禁止事项

- 不用字符串拼接替代 JSON/结构化解析。
- 不吞掉异常或把不可执行的检查伪造为通过；应报告 `not applicable`，必要时用 `plan.py block/revise`。
- 不提交 `__pycache__`、`.pyc` 或 `.pyo`；模板安装器会主动拒绝这些缓存。

## 常见错误

- **Windows 下 `task.json` 变 CRLF 触发 `git diff --check` 尾随空白**：`common/io.py` 的 `write_json` 若用 `os.fdopen(fd, "w", encoding="utf-8")` 写文件（未传 `newline=`），Windows 文本模式把 `\n` 转成 `\r\n`，因此 `task.py`/`plan.py` 推进状态落盘的 `task.json` 等 JSON 会成为 CRLF。仓库 `core.autocrlf=false` 且 `.gitattributes` 无 JSON 换行规则，`git diff --check` 会把新增行的 CRLF 判为 `trailing whitespace` 报错。模板侧已根治：`templates/embedded-c-overlay/.trellis/scripts/common/io.py` 传 `newline="\n"`，由 `test_write_json_lf.py` 锁定；根目录自用 `io.py` 尚未同步，属根级工具修复、需单独任务授权。
- **规范化 CRLF 的 `task.json` 会产生一次性全文件换行 diff**：HEAD 中被跟踪的 13 个 `task.json` 全部是 CRLF（9 个 `execution-plan.json` 是 LF；全仓 375 LF / 23 CRLF）。把工作区文件转成 LF 后，`git diff` 会显示整文件行变化，而 JSON 语义差异可能只有一行。核对方式：把两侧都 `replace("\r\n", "\n")` 后再做 `difflib` 比较，确认只有预期内容变化；提交信息里要说明这是换行规范化。
