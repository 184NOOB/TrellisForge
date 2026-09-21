# Codex 等待原生实施子代理期间禁止读取改动

父任务：`09-17-trellisforge-1-3-upgrade`（本任务是 1.3 功能子任务，排在固定收尾子任务之前）。

## Workflow Settings

- Review level: reinforced

## Goal

让 Codex 主会话在等待原生子代理（multi-agent `spawn_agent` / `wait_agent`，实施与审查）期间保持静默等待：不读改动、不做观测，只在收到终态后读取判断下一步所需的最小结果。同时修掉模板里三个让"写给 Codex 主会话的合同送不到"的可达性缺陷（编号子步骤被截断、`[Codex]` 平台别名不匹配、Codex 入口不传 `--platform codex`），并顺带修同源的 `--platform claude` 别名缺陷（实测下游 Claude 因此丢掉 2.1 派发指令）与 `write_json` 的 CRLF 噪声。

## Background

### 现象证据（仓库外只读证据，已核实）

- 下游项目会话 `~/.codex/sessions/2026-09-21/rollout-2026-09-21T20-21-50-01a0c3ea-*.jsonl`（Smart Community 目标仓库，使用 1.2 模板）中，主会话 `spawn_agent(agent_type=trellis-implement)` 后连续 `wait_agent {"timeout_ms":30000}`，并在等待间隙反复执行观测命令：`Get-ChildItem` 列文件、读文件大小/时间戳、`git status --short`、`git diff --stat`、`Get-Content -Tail execution-events.jsonl`、`Get-Process`、`list_agents`。
- 同一会话还重复出现 30 秒短窗口等待，与模板 Channel 合同禁止的 30 秒短周期轮询同类。
- **窗口上限已正面验证**：同一份 JSONL 中 `wait_agent` 的 `timeout_ms` 分布为 1280×2、10000×1、30000×8、60000×2、120000×1；其中 `timeout_ms=120000` 被工具接受并等满窗口（调用 `create_time 1790006910.59` → 输出 `1790007032.77`，约 122 秒），返回 `{"message":"Wait timed out.","timed_out":true}`。→ 分钟级窗口可行，30000 是模型自选而非工具上限；`timed_out:true` 是"仍在运行"信号。取证细节见 `research/codex-wait-agent-timeout-evidence.md`。

### 根因（模板内可达性缺陷）

1. **编号子步骤被截断**：模板 `.trellis/workflow.md` 的 Channel 等待合同位于 `#### 2.1.1`，正文包在 `[Codex]` 标签块里；`common/workflow_phase.py` 的 `_STEP_HEADING_RE` 只捕获 `X.Y`，`get_step("2.1")` 在下一个 `####` 收尾，因此 `2.1.1` 从不进入步骤 2.1 上下文；`get_step("2.1.1")` 因无法精确匹配而返回空（CLI 退出码 2）。
2. **平台别名不匹配**：`_platform_matches` 做归一化后的等值匹配，`--platform codex` 被 `resolve_effective_platform` 解析成 `codex-sub-agent` / `codex-inline`（归一化 `codexsubagent` / `codexinline`），永远不等于 `[Codex]`（归一化 `codex`），整块被丢弃。
3. **Codex 送达入口不传 `--platform codex`**：模板 `.trellis/workflow.md:356-363`（Loading Step Detail，位于 SessionStart 注入的 Phase Index 内）与 `.codex/hooks/session-start.py:470` 的 Step detail 提示串都只写 `--mode phase --step <X.Y>`；模板 `.agents/skills/` 只含 grill-me、trellis-channel、trellis-finish-work 与两个 `__PROJECT_PREFIX__` skill，**不含** `trellis-continue` / `trellis-start`（只有根目录自用版写了 `--platform codex`，属只读参考）。因此下游 Codex 实际执行的是不带 `--platform` 的命令，`filter_platform` 根本不运行（`common/git_context.py:92`），输出混入全部平台块与裸 `[Codex]` 标记行。
4. **同类 Claude 别名缺陷（实测现役）**：`--platform claude` 归一化为 `claude`，与 `[Claude Code]` 的 `claudecode` 不等值。实测模板根运行 `--mode phase --step 2.1 --platform claude`，输出中 `Spawn the implement sub-agent` 与 `**Agent type**: trellis-implement` 整段消失（同命令换 `--platform claude-code` 正常）；而模板 `.claude/commands/trellis/continue.md:10` 正是让下游 Claude 传 `--platform claude`。

结果：Channel 等待合同从未送达 Codex 主会话；原生子代理路径更是完全没有主会话等待合同，模型只能自行发明"边等边观测"的行为；同一函数还让下游 Claude 丢掉 2.1 派发指令。

## Requirements

### R1. Codex 主会话原生子代理静默等待合同

- 在模板 `.trellis/workflow.md` 的 `#### 2.1.1` 之后新增编号子步骤 `#### 2.1.2`，用 `[Codex]` 作用域写明原生子代理派发与等待规则，适用于 `spawn_agent` / `wait_agent` 的实施与审查派发（`codex-sub-agent` 与 `codex-inline` 主会话都适用）。
- 每个工作单元只派发一次；等待期间只对同一 agent/thread 连续等待；单次 `timeout_ms` 取该工具允许的最大值，正常路径锚点为**分钟级且不低于实测可行的 120000**；30 秒级窗口只允许出现在明确诊断场景，正常路径禁用 30000 这类短周期窗口。未实测的更大值（如 300000）不得写成工具上限。
- `wait_agent` 返回 `{"timed_out":true}`（"Wait timed out."）表示窗口到期而 agent 仍在运行，**不是失败信号**：复用同一 agent/thread 继续等待，不重新派发、不新建等待循环。
- 等待期间禁止读取代码或 diff 正文，包括：`git diff` / `git log`、被改动文件内容、`execution-events.jsonl` 或半成品 `final-report.md` 正文，也不运行 `plan.py status` 或反复 `list_agents` 做周期观测。
- 允许的"最小上下文进展确认"只有两种，且各自最多一次：(1) 派发后早期允许一次轻量存活探测，只看"是否有改动"的信号（文件路径、时间戳、大小，或 `git status --short` 的路径清单），不得读取文件内容；(2) 长时间没有终态且需要判断时，允许一次 `send_message` 向实施/审查 agent 询问进度，由该 agent 用摘要回复，不得重复追问或用它替代终态等待。
- 用户在等待期间的新指令是交互中断，不算轮询；收到终态后只读取判断下一步所需的最小最终结果，再回到 Phase 2 正常路径（`plan.py status`、审查派发或报告）；完整 diff 阅读属审查步骤而非等待。
- 异常入口：`wait_agent` 报错、agent 明确失败或长时间无进展时，允许一次最小诊断（最多一次 `list_agents` 或一次状态读取），据此决定中止、恢复或重新派发；不得把重复等待写成无条件循环。
- 合同只约束 Codex 主会话，不要求 Claude Code / OpenCode 主会话使用 `spawn_agent` / `wait_agent`。

### R2. 编号子步骤可达性修复（`get_step`）

- 模板 `common/workflow_phase.py` 的 `get_step` 支持编号子步骤：`get_step("X.Y")` 返回 `X.Y` 正文并包含其 `X.Y.Z` 子步骤；`get_step("X.Y.Z")` 可直接定位该子步骤；非 `X.Y.*` 的 `####` 标题仍在原处截断。
- 裸编号 `--step 1` / `--step 2` / `--step 3` 行为不变（返回空、退出码 2），不引入主版本聚合。
- 修复后现有 `#### 2.1.1` Channel 等待合同重新进入步骤 2.1 上下文；`2.1.1` 是模板中唯一的编号子步骤，故步骤 2.2 等其他步骤输出不变。

### R3. 平台家族别名修复（`filter_platform` / `_platform_matches`）

- `[Codex]` ↔ `codex-sub-agent` / `codex-inline` 双向别名：`--platform codex` 解析出的两种有效平台都渲染 `[Codex]` 块；`[codex-inline]` 仍只在 inline 渲染，`[codex-sub-agent]` 仍只在 sub-agent 渲染，两者不互相别名。
- `[Claude Code]` ↔ `--platform claude` 别名：`claude` 与 `claude-code` / `Claude Code` 互相匹配，修复下游 Claude 按 `.claude/commands/trellis/continue.md` 传 `--platform claude` 时整段派发指令被丢弃的现役缺陷。
- 不引入跨家族别名：`claude` 不匹配 `[Codex]`，`codex` 不匹配 `[Claude Code]`；`OpenCode` 等值匹配与其他平台行为不变。
- 别名修复的影响面只在 `--mode phase`（`filter_platform` 的唯一调用点是 `common/git_context.py:96`）；SessionStart 紧凑上下文不走 `filter_platform`（`.codex/hooks/session-start.py:474-476` 只做范围抽取与 breadcrumb 剥离），故 Phase Index 注入不受影响。

### R4. Codex 送达入口修复

- 模板 `.trellis/workflow.md` 的 Loading Step Detail 补充"按平台传 `--platform`"的说明与三行示例（Claude Code → `claude`、Codex → `codex`、OpenCode → `opencode`），用平台中立文本，不用标签块（该段在 Phase Index 内，SessionStart 不做平台过滤）。
- 模板 `.codex/hooks/session-start.py:470` 的 Step detail 提示串补 `--platform codex`（仅一行文案，不新增 Hook 通道、不改 Hook 行为）。
- `.claude/hooks/session-start.py`、`.opencode/lib/session-utils.js` 的同类提示串不在本任务范围（其命令文档已分别传 `--platform claude` / `--platform opencode`）。

### R5. `write_json` 换行稳定

- 模板 `common/io.py` 的 `write_json` 以 `newline="\n"` 打开临时文件，使 Windows 上写出的 `task.json` 保持 LF，消除 `git diff --check` 的 trailing whitespace 噪声与每次检查前的人工换行规范化。
- 根目录自用 `common/io.py` 同源同病但不在本任务范围（模板优先；根同步另议）。本仓库自身的 `task.json` 由根 `io.py` 写出，故 AC10 的人工规范化前置仍然保留。

### R6. 合约测试

- 新增模板测试，用真实子进程调用 `get_context.py --mode phase`（子进程必须设置 `PYTHONIOENCODING=utf-8` 并以 `encoding="utf-8", errors="replace"` 解码，否则本机 GBK 管道会让中文断言必红）；`cwd` 用 `TEMPLATE_ROOT = Path(__file__).resolve().parents[3]`（与现有模板测试一致），不得硬编码 `templates/embedded-c-overlay`，保证安装到下游后仍可用。断言集合：
  - `--step 2.1 --platform codex` 同时包含 Channel 等待合同（`write_stdin` / `yield_time_ms=300000` / 唯一等待）与原生静默等待合同（`wait_agent` / ≥120000 分钟级锚点 / `timed_out` 非失败 / 禁止等待期读代码或 diff 正文 / 早期一次轻量探测与一次 `send_message` 询问）；
  - `--step 2.1` **不带 `--platform`**（下游 Codex 的真实调用形态）同样包含两段合同；
  - `--step 2.1 --platform claude` 包含 `Spawn the implement sub-agent` 与 `trellis-implement`（别名修复回归），且不含 Codex 契约术语正文；
  - `--step 2.1 --platform claude-code` 输出不含 `exec_command` / `write_stdin` / `yield_time_ms` / `session_id` / `wait_agent` / `spawn_agent` 正文（2.1.1 / 2.1.2 标题可见，标题在标签块外属既有现状）；
  - `--step 2.1.1` 与 `--step 2.1.2` 可独立定位且退出码 0；`--step 2.2` 不含 2.1.x 内容；裸编号 `--step 1` / `--step 2` / `--step 3` 退出码 2；
  - `git_context.py:87-96` 的空内容检查在平台过滤**之前**，故 `--step 2.1.2 --platform claude-code` 退出码为 0；又因 2.1.2 标题留在 `[Codex]` 块外，过滤后仍保留标题行、只丢正文，测试只断言不含 Codex 正文术语，不得断言输出为空。
- 用进程内 `filter_platform` / `resolve_effective_platform` 断言 Codex 与 Claude 两个家族的别名与互斥矩阵。
- 新增 `write_json` 测试：写出的 JSON 文件内容不含 `\r\n`。
- 静态断言模板 workflow 的原生合同包含禁止项与限额清单（"读代码或 diff 正文"、早期一次探测、一次询问、"取该工具允许的最大值"、≥120000 锚点），且不出现 `"timeout_ms":30000` 这类示例短窗口；不得出现 `yield_time_ms=30000`（既有 `test_trellis_channel_contract.py:135` 已锁定该模式）；测试不得真实 spawn / wait 任何 agent。
- 基线策略：先写测试并运行，把红基线（2.1.1 未送达、`--step 2.1.1` 退出码 2、2.1.2 不存在、`--platform claude` 丢派发指令、`write_json` 写出 CRLF）记录到任务目录，再实现修复。

### R7. 变更边界与回归

- 功能写入只允许 `templates/embedded-c-overlay/`，具体为：`.trellis/workflow.md`、`.trellis/scripts/common/workflow_phase.py`、`.trellis/scripts/common/git_context.py`（`--step` 帮助文案）、`.trellis/scripts/common/io.py`（`write_json` 一行）、`.codex/hooks/session-start.py`（提示串一行）、`.trellis/scripts/tests/` 新增测试、`TEMPLATE-CONTENTS.md` 登记新增测试文件。根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/` 只读参考，不反向同步。
- 模板测试套件与根目录回归测试全绿；模板 Python `py_compile` 通过；`git diff --check` 无输出（前置：把本任务与父任务的 `task.json` CRLF 规范化为 LF，只改换行、不改 JSON 内容）。
- 不更新 `VERSION`、`history/`、manifest、结构迁移链、README、接入指南；这些留给固定收尾子任务。模板内 `TEMPLATE-CONTENTS.md` 只登记本任务新增的测试文件行。

## Acceptance Criteria

- [ ] AC1: 模板根运行 `python .trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex` 同时输出 2.1.1 Channel 等待合同与 2.1.2 原生静默等待合同。
- [ ] AC2: 模板根运行同命令但**不带 `--platform`** 时，同样输出两段合同（下游 Codex 的真实调用路径）。
- [ ] AC3: `--step 2.1 --platform claude-code` 输出不含 `exec_command`、`write_stdin`、`yield_time_ms`、`session_id`、`wait_agent`、`spawn_agent` 正文（2.1.1 / 2.1.2 标题可见）。
- [ ] AC4: `--step 2.1 --platform claude` 输出包含 `Spawn the implement sub-agent` 与 `trellis-implement`，且不含 AC3 所列 Codex 术语正文。
- [ ] AC5: `--step 2.1.1` 与 `--step 2.1.2` 各自返回对应小节且退出码为 0；`--step 2.2` 输出与修复前一致（不含 2.1.x 内容）；裸编号 `--step 1` / `--step 2` / `--step 3` 仍为退出码 2。
- [ ] AC6: `[Codex]` 对 `codex-sub-agent` 与 `codex-inline` 都渲染；`[codex-inline]` 对 `codex-sub-agent` 不渲染；`[codex-sub-agent]` 对 `codex-inline` 不渲染；`[Claude Code]` 对 `claude` 与 `claude-code` 都渲染；`claude` 不渲染 `[Codex]`，`codex` 不渲染 `[Claude Code]`。
- [ ] AC7: 模板 workflow 的原生等待合同包含：唯一派发与连续等待、最大等待窗口与 ≥120000 分钟级锚点并禁用 30000 短窗口、`timed_out:true` 非失败且复用同一 agent 继续等待、等待期禁止读代码与 diff 正文（`git diff` / 文件内容 / `execution-events.jsonl` / 半成品 `final-report.md` / `plan.py status` / 周期性 `list_agents`）、最多一次的早期轻量存活探测与最多一次的 `send_message` 询问、交互中断例外、终态后最小读取、异常入口不得无条件重复等待。
- [ ] AC8: 模板 `workflow.md` 的 Loading Step Detail 含按平台传 `--platform` 的说明与三行示例；模板 `.codex/hooks/session-start.py` 的 Step detail 提示串含 `--platform codex`；两个 Hook 除该文案外无行为改动（现有模板测试全绿即为佐证）。
- [ ] AC9: 模板 `common/io.py` 的 `write_json` 写出的文件不含 `\r\n`，并有测试覆盖；根目录 `common/io.py` 无 diff。
- [ ] AC10: 新增模板测试通过；模板测试套件全量通过；根目录回归测试通过；`python -m py_compile` 通过；`git diff --check` 无输出。
- [ ] AC11: `git diff` 的功能改动只出现在 `templates/embedded-c-overlay/` 内（外加任务目录与 Phase 3.3 允许的 spec 文档）；根目录 `.trellis/workflow.md`、`.trellis/scripts/common/workflow_phase.py`、`.trellis/scripts/common/io.py` 无功能 diff。
- [ ] AC12: 模板 CLI 复核命令在模板根运行（不得从仓库根运行而误读根 workflow.md）；`TEMPLATE-CONTENTS.md` 已登记本任务新增的测试文件。

## Out Of Scope

- 修改 Codex CLI、用户级 `~/.codex/config.toml` 或 `multi_agent_v2` 等待超时配置（模板 `.codex/config.toml:20-28` 明确不写该块，沿用 Codex 默认值）。
- 修改 Channel worker 运行时、`trellis channel spawn/wait` 行为与其既有合同；修改 `#### 2.1.1` 正文。
- 新增 Hook / 插件通道；修改 `.claude/`、`.opencode/` 的 hook 提示串与 `session-utils.js` 文案（本任务只改 `.codex/hooks/session-start.py` 一行提示串）。
- 根目录自用 Trellis 的同步（`.trellis/workflow.md`、`workflow_phase.py`、`io.py`）、`.codex/` 自用代理定义同步。
- 模板 `task.py` 中 `--step 1` 提示文案（既存失效、与 Codex 等待无关），记录为后续候选任务。
- README、接入指南、VERSION、canonical 对象库、版本 manifest 与升级补丁。

## Technical Notes

- 证据源（只读）：上述 Codex 会话 JSONL（取证摘录见 `research/codex-wait-agent-timeout-evidence.md`）；模板 `workflow.md` 607-634（2.1 正文与平台块）、636-678（2.1.1）、356-363（Loading Step Detail）；`common/workflow_phase.py` 35（`_STEP_HEADING_RE`）、100-131（`get_step`）、134-141（`_platform_matches`）、144-175（`resolve_effective_platform`）、178-219（`filter_platform`）；`common/git_context.py` 64-97（`--step` / `--platform` 与退出码 2 路径）；`common/io.py` 27-61（`write_json`）；`.codex/hooks/session-start.py` 462-478（TOC 构建，不走 `filter_platform`）、470（提示串）；`.claude/commands/trellis/continue.md:10`。
- 实测复核（模板根，2026-09-22）：`--step 2.1 --platform codex` 送达 `[Claude Code, codex-sub-agent, OpenCode]` 块但不含 2.1.1；`--step 2.1 --platform claude` 丢失 `Spawn the implement sub-agent`；`--platform claude-code` 正常。`core.autocrlf=false`，`git diff --check` 在 `.trellis/tasks/09-17-trellisforge-1-3-upgrade/task.json:23` 报 trailing whitespace（exit 2），根因是 `io.py:47` 的 `os.fdopen(fd, "w", encoding="utf-8")` 未传 `newline="\n"`。
- 换行现状（实测，Phase 2 复核修正）：HEAD 中被跟踪的 22 个 `.trellis/tasks/**.json` 里 **13 个 `task.json` 全部是 CRLF**、9 个 `execution-plan.json` 是 LF；全仓前 400 个跟踪文件为 375 LF / 23 CRLF。因此把父任务 `task.json` 规范化为 LF 会产生**一次性全文件换行 diff**（实测 34/33 行，JSON 内容差异仅 `children` 新增本任务一行），并使其与其余 12 个 CRLF `task.json` 不一致；这是为满足 AC10（`git diff --check` 无输出）而有意接受的代价，方向与后续根级 `io.py` 修复一致。
- 模板中现存的平台标记名只有：`Claude Code`、`Claude Code, codex-sub-agent, OpenCode`、`Codex`、`codex-inline`、`OpenCode`（另有 `[workflow-state:*]` 由 hook 与 `get_phase_index` 消费），别名规则只需覆盖这五个名称。
- 现有模板合同测试（`test_trellis_channel_contract.py`）只做文本断言，从不调用 `get_context.py` CLI，因此没有拦住本次可达性缺陷；新测试必须走真实 CLI 路径。既有 `test_trellis_channel_contract.py:102/124/135` 锁定 Codex 终端术语只在 `[Codex]` 块内、`yield_time_ms=300000` 固定、禁止 `yield_time_ms=30000` 短窗口，2.1.2 文本必须继续满足。
- 工程决策（已在 `design.md` 固化）：编号子步骤归并规则、Codex 与 Claude 两个家族的别名规则、送达入口文案位置、原生合同放置位置与禁止项清单、`write_json` 换行策略。

## Planning Convergence

- Status: ready
- Revision: rev.3（审查等级 `standard` → `reinforced`：affected-scope 独立复审，每轮阻塞修复后派发全新 `trellis-check` 直到阻塞为零）
- Revision: rev.2（主会话规划复核后修订：新增 R4 送达入口、R3 扩至 Claude 家族、R5 `write_json` 换行，R1 数值锚点改为实测 ≥120000 并写入 `timed_out` 语义）
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
