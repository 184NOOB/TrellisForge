# Codex 原生静默等待与等待合同可达性技术设计

## 1. 范围与边界

- 功能写入只落在 `templates/embedded-c-overlay/`：
  - `.trellis/workflow.md`（新增 `#### 2.1.2` Codex 主会话原生子代理静默等待合同；Loading Step Detail 补按平台传 `--platform` 的说明）
  - `.trellis/scripts/common/workflow_phase.py`（编号子步骤归并 + Codex / Claude 平台家族别名）
  - `.trellis/scripts/common/git_context.py`（`--step` 帮助文案补 `2.1.1` 例子，一行）
  - `.trellis/scripts/common/io.py`（`write_json` 以 `newline="\n"` 打开临时文件，一行）
  - `.codex/hooks/session-start.py`（Step detail 提示串补 `--platform codex`，一行文案）
  - `.trellis/scripts/tests/test_codex_native_wait_contract.py`（新增：送达 + 别名矩阵 + 合同文本）
  - `.trellis/scripts/tests/test_write_json_lf.py`（新增：`write_json` 换行）
  - `TEMPLATE-CONTENTS.md`（登记上述两个新增测试文件）
- 只读参考、禁止同步：根目录 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/`、`VERSION`、`history/`、`README.md`、`docs/`。
- 唯一允许的根目录写入是任务目录本身与 Phase 3.3 的 spec 文档更新（`.trellis/spec/main/tooling/python.md`），用于记录模板级可达性合同。

## 2. 送达链路与三处根因

```text
workflow.md
  ├── ### Loading Step Detail (Phase Index 内, 356-363)   <-- 根因 3：示例不带 --platform
  └── #### 2.1 Implement (607)
        ├── [Claude Code, codex-sub-agent, OpenCode] 正文 (609-624)
        ├── [codex-inline] 正文 (626-634)
        ├── #### 2.1.1  Channel 等待合同 (636-678)  <-- [Codex] 块
        └── #### 2.1.2  原生静默等待合同            <-- [Codex] 块（本任务新增）

.codex/hooks/session-start.py:470  提示串 "--mode phase --step <X.Y>"  <-- 根因 3
get_context.py --mode phase --step 2.1 [--platform codex]
  └── get_step("2.1")      <-- 根因 1：在下一个 #### 截断，2.1.1/2.1.2 从不进入上下文
  └── resolve_effective_platform("codex", config) → "codex-sub-agent" | "codex-inline"
  └── filter_platform(content, effective)
        └── _platform_matches("codexsubagent", ["Codex"])  <-- 根因 2：不等值，整块被丢弃
        └── _platform_matches("claude", ["Claude Code"])   <-- 根因 2 同源：Claude 也丢块
```

三处缺陷叠加：根因 1 让合同根本不在提取范围内；根因 2 让 `[Codex]` 块即使进入范围也被过滤掉；根因 3 让下游 Codex 走的其实是"不带 `--platform`、不过滤"的路径。修复后：带 `--platform codex` 与不带 `--platform` 两条路径都能同时送达 2.1.1 与 2.1.2。

## 3. 合同设计

### 3.1 `get_step` 编号子步骤归并（`common/workflow_phase.py`）

- 标题正则由 `^####\s+(\d+\.\d+)\b.*$` 改为捕获完整编号：`^####\s+(\d+(?:\.\d+)+)\b.*$`（现正则会把 `#### 2.1.1 ...` 的 group(1) 解析成 `2.1`，是截断行为的直接来源）。
- 归属判定：候选编号 `== requested` 或 `startswith(requested + ".")`。
- 起点：优先精确匹配 `requested` 的标题；没有时，仅当 `requested` 含 `.`（形如 `X.Y`）才退化为第一个 `requested.` 前缀标题（用于文档只写了子标题的场景）。
- 终点：遇到 `## `、列 0 的 `---`、或不属于 requested 的 `#### ` 标题即结束；无法解析编号的 `#### ` 行仍按旧逻辑结束。
- 结果：
  - `get_step("2.1")` = 2.1 正文 + 2.1.1 + 2.1.2；
  - `get_step("2.1.1")` = 仅 2.1.1（到 2.1.2 标题停止）；
  - `get_step("2.2")` 及所有不含子步骤的步骤输出不变（模板中 `2.1.1` 是唯一编号子步骤，已核实全部 14 个 `####` 标题）；
  - 裸编号 `get_step("1")` / `"2"` / `"3"` 不触发 fallback，仍返回空、CLI 退出码 2。
- CLI 副作用：`get_context.py --mode phase --step 2.1.1` 由"退出码 2"变为正常输出；`common/git_context.py:66` 的 `--step` 帮助文本补 `2.1.1` 示例（`get_context.py` 只是 shim，argparse 在 `git_context.py`）。
- 已知边界：`git_context.py:87-96` 的空内容检查发生在平台过滤之前，因此 `--step 2.1.2 --platform claude-code` 退出码为 0；又因 2.1.2 标题按 3.3 留在 `[Codex]` 块外，过滤后输出**仍保留标题行**、只丢正文，所以不得断言输出为空，只断言不含 `wait_agent` / `spawn_agent` 等 Codex 正文术语。

### 3.2 平台家族别名（`common/workflow_phase.py`）

归一化（去 `-` / `_` / 空格、转小写）后的别名规则：

| 标签 \ 传入平台 | `codex-sub-agent` | `codex-inline` | `claude` / `claude-code` | `opencode` |
|---|---|---|---|---|
| `[Codex]` | 保留 | 保留 | 丢弃 | 丢弃 |
| `[codex-sub-agent]` | 保留 | 丢弃 | 丢弃 | 丢弃 |
| `[codex-inline]` | 丢弃 | 保留 | 丢弃 | 丢弃 |
| `[Claude Code]` | 丢弃 | 丢弃 | 保留 | 丢弃 |
| `[Claude Code, codex-sub-agent, OpenCode]` | 保留 | 丢弃 | 保留 | 保留 |
| `[OpenCode]` | 丢弃 | 丢弃 | 丢弃 | 保留 |

- 匹配规则：等值匹配保持；额外允许两组家族别名 —— `codex` ↔ `{codex-sub-agent, codex-inline}`（后两者不互相别名）、`claude` ↔ `{claude-code, Claude Code}`。不引入跨家族别名。
- 模板中现存标记名只有 `Claude Code`、`Claude Code, codex-sub-agent, OpenCode`、`Codex`、`codex-inline`、`OpenCode`（已核实），别名集合覆盖完整。
- 影响：
  - Codex 主会话重新获得 Active Task Routing 的 `[Codex]` 段（`workflow.md:318-328`）、2.1.1 Channel 合同与 2.1.2 原生合同；
  - Claude 主会话恢复 `.claude/commands/trellis/continue.md:10` 那条 `--platform claude` 路径下的 `[Claude Code]` 正文（当前实测整段丢失）；
  - inline 也看到 2.1.1/2.1.2 是有意为之：inline 模式仍需派发独立 `trellis-check` 原生子代理，同样受静默等待约束，且 Channel 命令在 inline 下仍可用；
  - 影响面只在 `--mode phase`：`filter_platform` 的唯一调用点是 `common/git_context.py:96`；SessionStart 紧凑上下文由 `.codex/hooks/session-start.py:462-478` 自行做范围抽取与 breadcrumb 剥离，不调用 `filter_platform`，故 Phase Index 注入不受别名改动影响。

### 3.3 2.1.2 原生静默等待合同（`workflow.md`）

结构：`#### 2.1.2 Codex 主会话：原生子代理派发与静默等待` + `[Codex]` 包裹正文；标题留在标签块外，与 2.1.1 保持一致的最小 diff（代价：`--platform claude-code` 输出会看到两行含 "Codex" 的标题，正文关键词仍被过滤；PRD R6 / AC3 按"标题可见、正文不得出现"断言）。合同要点：

1. 每个工作单元只 `spawn_agent` 一次；等待只针对同一 agent/thread 连续进行；单次 `timeout_ms` 取工具允许的最大值，正常路径按分钟级且不低于 120000（实测可行，见 `research/codex-wait-agent-timeout-evidence.md`）；30 秒级只允许出现在明确诊断场景，正常路径禁用 30000 这类短周期窗口。未实测的更大值不得写成工具上限。
2. `wait_agent` 返回 `{"timed_out":true}` / "Wait timed out." 表示窗口到期而 agent 仍在运行，不是失败：复用同一 agent/thread 继续等待，不重新派发、不新建等待循环。
3. 等待期间禁止读取代码或 diff 正文：`git diff`、`git log`、被改动文件内容、`execution-events.jsonl` / 半成品 `final-report.md` 正文、`plan.py status`、周期性 `list_agents`；理由写清（半成品误判 + 无意义上下文灌入，实施子代理失去意义）。
4. 允许且仅允许两种"最小上下文进展确认"，各自最多一次：(a) 派发后早期一次轻量存活探测，只看改动信号（文件路径、时间戳、大小，或 `git status --short` 路径清单），不读文件内容；(b) 长时间无终态需判断时一次 `send_message` 询问实施/审查 agent，由其摘要回复；不得重复追问或用询问替代终态等待。
5. 用户在等待期间发来的新指令属交互中断，不算轮询。
6. 终态后只读判断下一步所需的最小最终结果，再回 Phase 2 正常路径；完整 diff 阅读属于审查步骤而非等待。
7. 异常入口：工具报错、明确失败或长时间无进展时允许一次最小诊断（最多一次 `list_agents` 或一次状态读取），据此决定中止/恢复/重新派发；禁止无条件重复等待循环。
8. 收尾声明：以上只约束 Codex 主会话；Claude Code / OpenCode 主会话不要求使用 `spawn_agent` / `wait_agent`。

措辞约束（可测试）：包含"取该工具允许的最大值"、"分钟级"、"120000"、"禁用 30000 这类短周期窗口"、`timed_out`、"交互中断"、"最小最终结果"、"读代码或 diff 正文"、早期一次探测与一次询问的限额；不出现 `"timeout_ms":30000` 形式的 JSON 示例，也不出现 `yield_time_ms=30000`（既有 `test_trellis_channel_contract.py:135` 已锁定该模式），正文术语不得越出 `[Codex]` 块（`test_trellis_channel_contract.py:102` 锁定 `exec_command` / `write_stdin` / `yield_time_ms` / `session_id` 的作用域）。

### 3.4 送达入口（`workflow.md` + `.codex/hooks/session-start.py`）

- `workflow.md` Loading Step Detail（356-363）在现有两行示例后追加平台说明，例如：

  ```text
  # Pass your platform so platform-tagged blocks are filtered:
  #   Claude Code: --platform claude   Codex: --platform codex   OpenCode: --platform opencode
  ```

  用平台中立文本而非 `[Codex]` 标签块：该段位于 Phase Index 内，SessionStart 不做平台过滤，标签块会对所有平台原样显示。
- `.codex/hooks/session-start.py:470` 的提示串改为
  `Step detail: \`python ./.trellis/scripts/get_context.py --mode phase --step <X.Y> --platform codex\`.`
  —— 只改字符串，不改 `_build_workflow_toc` 逻辑、不新增 Hook 通道；已核实无模板测试断言该串，且 mirror 类测试只比对 skill 文件（`test_trellis_channel_contract.py:78`、`test_opencode_platform_contract.py:234`、`test_review_profile_contract.py:220`），不涉及 hook 文案。
- `.claude/hooks/session-start.py:726` 与 `.opencode/lib/session-utils.js:626` 的同类提示串不在本任务范围：Claude / OpenCode 的命令文档已分别传 `--platform claude` / `--platform opencode`，R3 的 Claude 别名修复即可让其生效；OpenCode 等值匹配本就正常。

### 3.5 `write_json` 换行（`common/io.py`）

- `io.py:47` 的 `os.fdopen(fd, "w", encoding="utf-8")` 改为 `os.fdopen(fd, "w", encoding="utf-8", newline="\n")`；`payload` 由 `json.dumps(..., indent=2)` 生成，含 `\n`，Windows 文本模式默认翻译成 `\r\n` 是噪声根因（已实测：`core.autocrlf=false`、HEAD 中 `task.json` 为 LF、`git diff --check` 在父任务 `task.json:23` 报 trailing whitespace 且 exit 2）。
- 原子写语义不变（tempfile + `os.replace`），JSON 内容不变，只改换行。
- 兼容：下游若已提交 CRLF 的 `task.json`，安装本模板后首次 `task.py` 写盘会产生一次性全文件换行 diff，之后稳定；`.gitattributes` 不由模板分发，故不依赖 git 换行归一化。
- 根目录 `common/io.py` 同源同病，但按 AC11 保持无 diff（模板优先，根同步另议）；因此本仓库自身的 `task.json` 仍需在 `git diff --check` 前人工规范化为 LF。

### 3.6 合约测试

- `test_codex_native_wait_contract.py`
  - 路径约定：`SCRIPTS_DIR = Path(__file__).resolve().parents[1]`、`TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]`，与现有 6 个模板测试一致；子进程 `cwd=str(TEMPLATE_ROOT)`，**不得**硬编码 `templates/embedded-c-overlay`，否则安装到下游即失效。
  - 编码：子进程环境带 `PYTHONIOENCODING=utf-8`，`subprocess.run(..., encoding="utf-8", errors="replace", timeout=...)`；否则 Windows 管道默认 GBK，父进程 UTF-8 解码抛 `UnicodeDecodeError`，中文断言必红。
  - 真实送达断言：
    - `--step 2.1 --platform codex`：包含 `write_stdin`、`yield_time_ms=300000`、`wait_agent`、"取该工具允许的最大值"、"分钟级"、`120000`、`timed_out`、禁止读代码/diff 正文的措辞、两种限额探测/询问短语；
    - `--step 2.1`（不带 `--platform`）：同样包含两段合同关键词（下游 Codex 的真实调用形态）；
    - `--step 2.1 --platform claude`：包含 `Spawn the implement sub-agent`、`trellis-implement`，不含 `write_stdin` / `wait_agent` / `spawn_agent` 正文；
    - `--step 2.1 --platform claude-code`：不含 `exec_command` / `write_stdin` / `yield_time_ms` / `session_id` / `wait_agent` / `spawn_agent`；
    - `--step 2.1.1` / `--step 2.1.2`：退出码 0，各自只含本小节关键词；
    - `--step 2.2`：不含 2.1.x 关键词；裸编号 `--step 1` / `2` / `3`：退出码 2；
    - `--step 2.1.2 --platform claude-code`：退出码 0，标题行可见但不得出现 `wait_agent` / `spawn_agent` 等 Codex 正文术语（不断言输出为空）。
  - 纯函数断言（进程内导入模板 `common.workflow_phase`）：`resolve_effective_platform` 的 codex 映射；`filter_platform` 的 3.2 别名矩阵（含 claude 家族与跨家族不匹配）。
  - 文本断言：2.1.2 正文位于 `[Codex]` 块内；禁止 `"timeout_ms":30000` 与 `yield_time_ms=30000`；不真实 spawn / wait 任何 agent。
  - 基线策略：先写测试并运行，把红基线（2.1.1 未送达、`--step 2.1.1` 退出码 2、2.1.2 不存在、`--platform claude` 丢派发指令）记录到任务目录，再实现修复。
- `test_write_json_lf.py`：在临时目录调用模板 `common.io.write_json` 写一个含中文与嵌套结构的 dict，读回字节断言 `b"\r\n" not in raw` 且 `json.loads` 内容与输入相等；不触碰仓库内任何 `task.json`。

## 4. 兼容性与回滚

- 兼容：`get_step` 旧用例（无子步骤的步骤）输出逐字节不变；`filter_platform` 等值匹配路径不变；SessionStart / Phase Index 输出不变（不走 `filter_platform`）；根目录自用实现不改，其行为保持原样（模板内先交付）。
- 风险 1：未来 `X.Y.Z` 标题被误并入 `X.Y` —— 这是期望语义，且新测试锁定；`X.Y.ZZ` 等畸形标题不产生归属。
- 风险 2：inline 模式新增看到 Channel / 原生等待内容 —— 有意设计，非泄露（Claude / OpenCode 有断言兜底）。
- 风险 3：Claude 别名修复让下游 Claude 首次看到 `[Claude Code]` 正文 —— 这是恢复既有意图（模板 `.claude/commands` 一直传 `--platform claude`），不是新增行为；由 AC4 锁定。
- 风险 4：测试用子进程依赖工作目录 —— `cwd` 固定为 `TEMPLATE_ROOT` 并带超时，不依赖仓库根。
- 风险 5：`io.py` 改动让下游已提交 CRLF 的 `task.json` 出现一次性换行 diff —— 可接受、自愈；如需完全规避则回滚该行并保留人工规范化步骤。
- 回滚：全部为纯文本 / 一行级改动，`git checkout` 对应路径即可；无运行时状态、无 manifest、无 canonical 影响。分批回滚点见 `implement.md`。

## 5. 验证命令

从仓库根运行（测试与 py_compile 用相对路径；`get_context.py` 读的是 **cwd** 向上找到的 `.trellis/`，模板 CLI 必须在模板根用 `workdir` / `Set-Location` 运行）：

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_codex_native_wait_contract.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_write_json_lf.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/workflow_phase.py
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/io.py
python -m py_compile templates/embedded-c-overlay/.codex/hooks/session-start.py
$env:PYTHONIOENCODING = "utf-8"
# 以下四条 workdir 必须是 templates/embedded-c-overlay
python -B .trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex
python -B .trellis/scripts/get_context.py --mode phase --step 2.1
python -B .trellis/scripts/get_context.py --mode phase --step 2.1 --platform claude
python -B .trellis/scripts/get_context.py --mode phase --step 2.1.2
git diff --check
```

`git diff --check` 前置：本仓库的 `task.json` 由**根目录** `io.py`（本任务不修）写出，仍是 CRLF，当前父任务 `.trellis/tasks/09-17-trellisforge-1-3-upgrade/task.json:23` 已被判为 trailing whitespace（实测 exit 2）。检查前把本任务与父任务的 `task.json` 规范化为 LF，只改换行、不改 JSON 内容；`task.py` / `plan.py` 每次写盘会重新引入 CRLF，提交前需重做。

**Phase 2 实测修正（2026-09-22）**：HEAD 中被跟踪的 22 个 `.trellis/tasks/**.json` 里 13 个 `task.json` **全部是 CRLF**（9 个 `execution-plan.json` 为 LF；全仓前 400 个跟踪文件 375 LF / 23 CRLF），`core.autocrlf=false`。所以 LF 规范化不是"恢复到 HEAD 状态"，而是**一次性全文件换行改动**：父任务 `task.json` 实测 diff 34/33 行，换行归一后 JSON 内容差异只有 `children` 新增本任务一行（已用 `difflib` 逐行核对）。代价是它与其余 12 个 CRLF `task.json` 不一致；收益是 `git diff --check` 退出码 0（AC10），且方向与后续根级 `io.py` 修复一致。审查按"有意接受、已记录"处理，不得视为越界改动。彻底消除该噪声需要修根目录 `io.py`（本任务 Out Of Scope）或加 `.gitattributes` 的 `*.json text eol=lf`（模板不分发 `.gitattributes`），两者都记为后续候选。

构建、部署、硬件验证：`not applicable`（本仓库不产出固件或可执行产品）。
