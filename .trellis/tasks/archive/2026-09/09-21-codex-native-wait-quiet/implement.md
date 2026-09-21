# Codex 原生静默等待实施计划

## 实施前条件

- [ ] 用户已明确批准最新规划摘要（rev.2）；批准前不得运行 `task.py start` 或修改模板产品文件。
- [ ] 当前任务由本会话精确 `session:*` 指针绑定，状态为 `planning`；启动后才进入 `in_progress`。
- [ ] 已读取 `prd.md`、`design.md`、本文件、`implement.jsonl`、`check.jsonl`、`research/codex-wait-agent-timeout-evidence.md` 及 jsonl 中列出的 Spec。
- [ ] 已按 `workflow.md:354` Guardrail 用 `plan.py` 创建并批准 live `execution-plan.json`，且本文件的批次 1-6 已映射为 plan 阶段；Phase 2 源码改动只能在 plan 批准后发生，状态推进只走 `plan.py`。
- [ ] `git status --short` 已记录现有用户改动（当前含 `.opencode/package.json`、`09-17-readme-integration-guide-upgrade-patch/prd.md`、父任务 `task.json`），这些不属于本任务，不得回滚或提交进本任务改动。
- [ ] 已确认写入白名单只有 `design.md` §1 列出的模板路径；根目录 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/` 不在写入范围。

## 实施批次

### 1. 合约测试先行（红基线）

- [ ] 新增 `templates/embedded-c-overlay/.trellis/scripts/tests/test_codex_native_wait_contract.py`：按 `design.md` 3.6 写真实送达测试、别名矩阵纯函数测试与合同文本禁止项测试。
- [ ] 路径用 `SCRIPTS_DIR = Path(__file__).resolve().parents[1]` / `TEMPLATE_ROOT = SCRIPTS_DIR.parents[1]`，子进程 `cwd=str(TEMPLATE_ROOT)`；不得硬编码 `templates/embedded-c-overlay`。
- [ ] 子进程统一带 `PYTHONIOENCODING=utf-8` 环境与 `encoding="utf-8", errors="replace"`、固定 `timeout`；不得真实 spawn / wait 任何 agent。
- [ ] 覆盖四条 CLI 形态：`--step 2.1 --platform codex`、`--step 2.1`（不带 `--platform`）、`--step 2.1 --platform claude`、`--step 2.1 --platform claude-code`；外加 `--step 2.1.1` / `2.1.2` / `2.2` / 裸编号 `1|2|3`，以及 `--step 2.1.2 --platform claude-code` 退出码 0、标题行可见但不含 Codex 正文术语（不断言输出为空）。
- [ ] 新增 `templates/embedded-c-overlay/.trellis/scripts/tests/test_write_json_lf.py`：临时目录内调用模板 `common.io.write_json`，断言字节不含 `b"\r\n"` 且 `json.loads` 回读相等；不触碰仓库内任何 `task.json`。
- [ ] 先运行两个新测试并在任务目录记录红基线（2.1.1 未送达、`--step 2.1.1` 退出码 2、2.1.2 不存在、`--platform claude` 丢派发指令、`write_json` 写出 CRLF）。

### 2. 可达性修复 A：`get_step` 编号子步骤归并

- [ ] 标题正则改为 `^####\s+(\d+(?:\.\d+)+)\b.*$`；实现 `X.Y` 归属 `X.Y.Z` 的起点/终点规则（前缀 fallback 仅在 requested 含 `.` 时生效，裸 `--step 1/2/3` 保持退出码 2）；更新模块与函数 docstring（含"空内容检查早于平台过滤"的边界说明）。
- [ ] 模板 `common/git_context.py:66` 的 `--step` 帮助文本补 `2.1.1` 例子（仅文案）。
- [ ] 运行测试确认 `--step 2.1.1` 退出码 0、`--step 2.1`（不带 `--platform`）已含 2.1.1、`--step 2.2` 与裸编号行为不变。

### 3. 可达性修复 B：平台家族别名

- [ ] `_platform_matches` 加入两组家族别名：`codex` ↔ `codex-sub-agent` / `codex-inline`（后两者不互相别名）、`claude` ↔ `claude-code` / `Claude Code`；保持等值匹配与其他平台行为不变；不引入跨家族别名。
- [ ] 更新 `filter_platform` / `resolve_effective_platform` docstring，写明别名矩阵（`design.md` 3.2 表格）与"影响面只在 `--mode phase`"。
- [ ] 运行测试确认别名矩阵全绿：`--platform codex` 送达 `[Codex]` 块，`--platform claude` 恢复 `Spawn the implement sub-agent`，`--platform claude-code` 不含 Codex 术语正文。

### 4. 送达入口

- [ ] 模板 `.trellis/workflow.md` 的 Loading Step Detail（356-363）追加平台中立说明与三行示例（Claude Code → `claude`、Codex → `codex`、OpenCode → `opencode`）；不用 `[Codex]` 标签块（该段在 Phase Index 内，SessionStart 不做平台过滤）。
- [ ] 模板 `.codex/hooks/session-start.py:470` 的 Step detail 提示串补 `--platform codex`；只改字符串，不改 `_build_workflow_toc` 逻辑、不新增 Hook 通道。
- [ ] 不改 `.claude/hooks/session-start.py`、`.opencode/lib/session-utils.js`、`.claude/commands/*`、`.opencode/commands/*`。
- [ ] 运行模板全量测试，确认 mirror 类与平台合同类测试未受影响。

### 5. 原生静默等待合同 2.1.2

- [ ] 在模板 `.trellis/workflow.md` 的 `#### 2.1.1` 之后插入 `#### 2.1.2 Codex 主会话：原生子代理派发与静默等待`，正文包在 `[Codex]` 块内，按 `design.md` 3.3 的 8 条要点撰写（唯一派发与连续等待、≥120000 分钟级锚点、`timed_out:true` 非失败、禁止读代码/diff 正文清单、两种"最多一次"的最小进展确认、交互中断例外、终态后最小读取、异常入口不得无条件循环、只约束 Codex 主会话）。
- [ ] 明确 inline 审查派发同样适用；数值锚点只写实测可行的 120000，不把 300000 等未实测值写成工具上限。
- [ ] 不修改 2.1.1 正文；不出现 `"timeout_ms":30000` 示例，不出现 `yield_time_ms=30000`；`exec_command` / `write_stdin` / `yield_time_ms` / `session_id` 只出现在 `[Codex]` 块内。
- [ ] 在模板 `TEMPLATE-CONTENTS.md` 登记 `test_codex_native_wait_contract.py` 与 `test_write_json_lf.py` 两行（1.3 新增）。

### 6. `write_json` 换行

- [ ] 模板 `common/io.py:47` 改为 `os.fdopen(fd, "w", encoding="utf-8", newline="\n")`；不动原子写逻辑与 JSON 内容。
- [ ] 运行 `test_write_json_lf.py` 与模板全量测试确认转绿；确认根目录 `.trellis/scripts/common/io.py` 无 diff。

### 7. 全量验证与边界审计

- [ ] 运行新增测试与模板全量测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_codex_native_wait_contract.py"
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_write_json_lf.py"
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 只读运行根目录回归，确认根自用实现无功能 diff：

  ```powershell
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 模板 Python 语法检查：

  ```powershell
  python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/workflow_phase.py
  python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/io.py
  python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/git_context.py
  python -m py_compile templates/embedded-c-overlay/.trellis/scripts/get_context.py
  python -m py_compile templates/embedded-c-overlay/.codex/hooks/session-start.py
  ```

- [ ] 手工复核真实 CLI 输出（`--step 2.1` × `codex` / 无 platform / `claude` / `claude-code`，`--step 2.1.1` / `2.1.2` / `2.2`，裸编号 `1|2|3`）；**必须在模板根运行**（`Set-Location templates/embedded-c-overlay` 或用工具 workdir），从仓库根运行会误读根 workflow.md。
- [ ] 把本任务与父任务的 `task.json` 规范化为 LF（只改换行，不改 JSON 内容），再运行 `git diff --check`；根目录 `io.py` 未在本任务修复，`task.py` / `plan.py` 每次写盘会重新引入 CRLF，提交前需重做。
- [ ] `git diff --check`。
- [ ] 确认功能改动只出现在 `templates/embedded-c-overlay/`（外加任务目录与 Phase 3.3 的 spec 文档），根目录 `.trellis/workflow.md`、`common/workflow_phase.py`、`common/io.py` 无功能 diff；用户既有改动（`.opencode/package.json`、兄弟任务 `prd.md`）未被触碰。
- [ ] 构建、部署、硬件验证报告 `not applicable`。

### 8. 审查（reinforced）

- [ ] 按 `reinforced` 派发独立 `trellis-check` agent，范围为 affected-scope：本任务完整 diff、送达测试（真实 CLI 子进程 + `TEMPLATE_ROOT`）、别名矩阵（Codex 与 Claude 两个家族）、送达入口文案、`write_json` 换行与全部验收项（AC1-AC12）。
- [ ] 每轮阻塞问题修复后，**派发全新的独立 `trellis-check` agent 做完整复审**，循环直到阻塞发现为零；不得用主会话自审或"只重跑失败检查"替代新一轮独立复审。
- [ ] 主会话在每轮之间只负责修复与重跑受影响的验证命令（模板/根目录测试、`py_compile`、`git diff --check`）。
- [ ] 达到零阻塞后不追加 commit-ready 独立复审（`reinforced` 不要求，`strict` 才要求）。

### 9. Spec 更新（Phase 3.3）

- [ ] 在根 `.trellis/spec/main/tooling/python.md` 增加"模板等待合同可达性"场景：`get_step` 子步骤归并、Codex / Claude 平台家族别名矩阵、`--platform` 送达入口约定、模板测试要求（真实 CLI 子进程 + `TEMPLATE_ROOT` + `PYTHONIOENCODING`）、`write_json` 换行约定；注明根自用实现尚未同步，不得写成根目录已具备的事实。

## 回滚点

- 批次 2 失败：还原 `workflow_phase.py` 的 `get_step` 与帮助文案，保留红基线测试作为待办证据。
- 批次 3 失败：还原 `_platform_matches` 别名分支，保留批次 2 成果（此时 2.1.1 已能通过不带 `--platform` 的路径送达）。
- 批次 4 失败：还原 Loading Step Detail 与 `.codex/hooks/session-start.py:470` 文案；不影响批次 2/3 的可达性修复。
- 批次 5 失败：删除 2.1.2，避免留下"合同存在但不可达"的半截状态。
- 批次 6 失败：还原 `io.py` 一行并恢复"每次检查前人工规范化 `task.json`"的步骤（`design.md` 3.5 的风险 5 规避路径）。
- 全部为纯文本 / 一行级改动，`git checkout` 对应模板路径即可回滚；无 manifest、canonical 或运行时状态影响。

## 发布边界

- 不更新 `VERSION`、canonical、manifest、结构链、README、接入指南（固定收尾子任务负责）。
- 不修改根目录自用 Trellis 实现（含 `io.py`）、`.codex/` 自用代理定义或任何 Hook 行为。
- 不新增 Hook / 插件通道；`.codex/hooks/session-start.py` 只改一行提示串文案。
