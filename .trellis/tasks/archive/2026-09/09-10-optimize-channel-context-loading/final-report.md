# Final Report — 优化 Trellis Channel 上下文与等待加载

## 任务

- Task：`.trellis/tasks/09-10-optimize-channel-context-loading`
- Plan revision 1，8 个 phase，全部完成；audit log 30 条事件，无损坏。

## 目标摘要

把下游模板 `templates/embedded-c-overlay/` 的 Channel Implement/Check 上下文
加载改为混合模型：system prompt 只承载稳定协议与角色卡，任务 PRD/设计/实施
计划/Spec/Research 正文由 worker 按 brief 中的 `Active task` 与 manifest
主动从共享工作区读取；并把 Codex 唯一 wait session 的后续读取窗口固定为
`yield_time_ms=300000`，阻止短周期空轮询。

## 修改文件

| 文件 | 改动 |
|---|---|
| `templates/embedded-c-overlay/.trellis/agents/implement.md` | 新增 `Mandatory context precheck (fail-closed)`：活动任务路径解析与工作区信任边界、`implement.jsonl` 逐行解析、任务文档 `prd.md`（`design.md`/`implement.md` 存在时必读）批量读取、首次交付写入前门禁、失败 `error` 报告（`missing|unreadable|invalid|outside-workspace`）、成功路径无单独回执/文件列表/内容指纹 |
| `templates/embedded-c-overlay/.trellis/agents/check.md` | 对称实现 `check.jsonl` 门禁；首次工作边界放宽定义为查看任务 diff、正式审查或自修复之前；保留 review profile 与 task-change-manifest 流程 |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/workflows.md` 与 `.claude` 镜像 | Standard Implement/Check 与 Parallel Reviewers 示例改为无全文注入的 brief 定位模式（Active task + manifest + 预检提醒）；brainstorm 显式注入保留；每个示例仍一次 spawn/一次 wait |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/workers.md` 与 `.claude` 镜像 | `--file`/`--jsonl` 明确定义为保留的显式快照能力；新增 `Explicit snapshot vs. shared-workspace active read` 区分段；共享工作区 Implement/Check 标为主动读取默认值 |
| `templates/embedded-c-overlay/.trellis/workflow.md` | `[Codex]` 2.1.1 唯一等待编排改为：首次短窗口取终态/`session_id`，之后每次 `write_stdin` 固定 `yield_time_ms=300000` 复用同一 ID；五分钟是单次读取上界而非 wait 总超时；30000 短窗口仅诊断/交互例外；保留 `done/error`、CLI 超时 124、进程失败与用户中断边界 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_trellis_channel_contract.py` | 新增 4 个测试：Codex 等待窗口固定 300000 并阻止 `yield_time_ms=30000` 默认、标准派发无任务正文注入且 brief 定位、Parallel Reviewers 主动读取、workers 文档保留快照且默认主动读取、两张 Agent 卡 fail-closed 预检门禁与成功路径静默 |

`.trellis/tasks/09-10-optimize-channel-context-loading/{execution-plan.json,execution-events.jsonl}` 为本任务 sanctioned 状态文件；任务目录 `prd.md`/`implement.md`/`task.json` 的既有修改来自父会话规划期，非本实施产出。根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 无功能性修改（扫描确认）。

## 阶段结果

| Phase | 结果 | 记录检查 |
|---|---|---|
| discover-template-contract | completed | 只读盘点，无检查（no_check_reason） |
| update-agent-cards | completed | agent-cards-fail-closed-gates, agent-cards-codex-terms-absent 均 pass |
| update-skill-docs | completed | standard-dispatch-no-fulltext-injection, workers-snapshot-capability-kept, skills-mirror-byte-identical 均 pass |
| update-workflow-codex-window | completed | workflow-wait-window-contract pass |
| extend-contract-tests | completed | channel-contract-suite（14 条）, contract-tests-wait-window-guard（对 HEAD 基线全 Red）均 pass |
| cross-file-consistency | completed | template-unit-suite（118 条）, repo-changes-confined 均 pass |
| full-validation | completed | root-regression-suite（99 条）, template-py-compile, git-diff-check 均 pass |
| final-report | completed | acceptance-criteria-trace, report-written |

## 验收条件逐项核对

1. 标准 Implement Channel 派发不再 `--file`/`--jsonl` 注入正文，brief 提供活动任务路径与 `implement.jsonl` 定位 —— **通过**（workflows.md Standard Implement Dispatch + 测试断言）。
2. 标准 Check Channel 派发采用相同边界并 `check.jsonl` 定位 —— **通过**（Standard Check Dispatch）。
3. Implement/Check worker 首次工作（写入/审查/自修复）前按序批量读取全部必需任务文档与 manifest 有效条目 —— **通过**（两张 Agent 卡 precheck 顺序 + `Batch-read`）。
4. 任一必读文件缺失/不可读/越界/manifest 无效/加载不完整时，worker 在修改交付文件前报告阻塞并终止 —— **通过**（Agent 卡 fail-closed `error` 契约，失败类型枚举）。
5. 加载成功无单独回执/文件列表；失败仅走 `error` 终态报告路径与原因 —— **通过**（Agent 卡静默成功 + error 终态）。
6. `implement.jsonl`/`check.jsonl` 仍是必需清单，规划门禁未被绕过 —— **通过**（未改动 workflow 1.3/1.4 readiness gate 与 manifest 选材职责，仅改 Channel 获取时机）。
7. 稳定协议、角色、安全边界、禁止提交、执行/审查职责与终止报告契约仍在 system prompt —— **通过**（Agent 卡结构保留，终止契约测试继续通过）。
8. `--file`/`--jsonl` 能力保留且显式快照与主动读取边界清楚 —— **通过**（workers.md + command-reference.md 未删参数）。
9. Codex 取得 `session_id` 后复用同一 ID 并将每次 `write_stdin` 固定为 `yield_time_ms=300000` —— **通过**（workflow `[Codex]` 规则 + 测试）。
10. 合约测试断言确切 `yield_time_ms=300000` 且阻止 `30000` 短轮询默认 —— **通过**（词边界正则 `yield_time_ms=30000(?!0)`）。
11. 五分钟窗口到期仍复用原 session；`done/error`、CLI 总超时、用户中断边界明确；不把读取窗口当总超时 —— **通过**（workflow rule 3 与 6）。
12. 模板全部标准派发示例与 Agent 说明对混合加载契约一致 —— **通过**（spawn 示例全量扫描，唯一任务型默认派发移除全文注入）。
13. 功能改动仅位于 `templates/embedded-c-overlay/` —— **通过**（git status 范围扫描）。
14. 测试覆盖标准派发参数、必读文件集合、失败前置门禁、成功无回执、显式注入保留 —— **通过**（4 个新测试方法全覆盖）。
15. Python 单测、语法检查、`git diff --check` 通过；构建/部署/硬件验证 N/A —— **通过**（见下方验证）。

## 验证结果

- 模板单元测试：**pass** — `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`，118 条 OK。
- Channel 合约测试：**pass** — 扩展后 14 条 OK；对 HEAD 基线验证过全部新断言 Red（旧派发仍 `--file`/`--jsonl`、旧 Codex 块无 300000、旧 Agent 卡无门禁）。
- 根目录回归测试：**pass** — `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`，99 条 OK。
- 模板 Python 语法：**pass** — `.trellis/scripts`、`.claude/hooks`、`.codex/hooks` 全部 `.py` 通过 `py_compile`，无失败项。
- `git diff --check`：**pass（任务范围）** — `git diff --check -- templates/embedded-c-overlay` 退出码 0。全仓命令会因父会话规划期写入的 `task.json` CRLF 行（4 行）报尾随空白，属既有规划产物，非本任务改动；未越权修改该文件。
- 构建、部署、硬件验证：**not applicable** — 本仓库为 Trellis 工作流模板仓库，不产出固件、可执行产品或硬件目标，无对应命令可执行。

## 未运行项与说明

- 未运行任何真实 Channel 派发/外部 provider 挂接；本任务全部为静态模板契约测试，设计上不启动 worker（符合 `test_trellis_channel_contract.py` 首注释声明）。
- 未修改维护 `@mindfoldhq/trellis` CLI 或 Claude/Codex adapter；未改动事件 schema、provider adapter、worker 生命周期与任务生命周期。
- 未更新 `VERSION`、历史 canonical 对象、版本 manifest、结构迁移链、README 或接入指南（父任务收尾子任务统一处理）。

## 已知风险与后续

- Agent 卡读取要求属于执行前置契约，无法从机制上证明模型真正执行了读取或理解了全部语义；若未来需要强证明，应另设确定性加载器或 provider adapter 校验，而非恢复 worker 自报回执。
- 通用手工派发仍可显式注入超大正文；本任务只优化模板默认工作流，不承诺修复所有自定义命令的操作系统参数上限。
- 固定五分钟窗口会降低无终态时的主会话响应及时性；工具在 wait 进程提前退出时仍即时返回，不强制等待满五分钟。
- 回滚可独立进行：主动读取契约回退 Agent 卡与标准派发示例；等待窗口规则独立回退 workflow `[Codex]` 块。