# 最终验收报告 — 规范 Trellis Channel worker 派发与等待流程

任务:`.trellis/tasks/09-07-trellis-channel-dispatch-wait`
分支:`trellis-channel-dispatch-wait-and-upgrade`
审查等级:`standard`(实施后独立 affected-scope 审查)

## 变更范围

所有产品变更均位于 `templates/embedded-c-overlay/`。根目录现用的
`.trellis/`、`.agents/`、`.claude/`、`.codex/` 工作流、`docs/接入指南.md`、
`README.md`、`templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 与
`tools/install-embedded-c-overlay.ps1` 均未改动。安装、1.0 升级、迁移与版本
发布全部按计划留给子任务 2。

### 新增文件

| 路径 | 说明 |
|---|---|
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/SKILL.md` | 完整 Skill 索引，含一次 spawn/一次 wait、`done,error` 终止事件与 progress 诊断边界 |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/command-reference.md` | wait 命令补充标准派发用法说明 |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/forum.md` | 完整 forum 参考（原样保留） |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/progress-debugging.md` | 新增 "Normal Path vs Diagnostics"，明确 progress 仅限诊断 |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/workers.md` | 新增 "Dispatcher Wait Discipline" |
| `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/workflows.md` | Pattern B 重写为实施/审查标准 PowerShell 示例 |
| `templates/embedded-c-overlay/.claude/skills/trellis-channel/`(全部 6 个文件) | Claude Skill 镜像，公共文件与 `.agents` 逐字节一致 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_trellis_channel_contract.py` | 契约测试（10 个用例）：文件树完整性、镜像一致、Codex 术语作用域、唯一 wait、禁止轮询、worker 契约 |

### 修改文件

| 路径 | 说明 |
|---|---|
| `templates/embedded-c-overlay/.trellis/workflow.md` | 在 `#### 2.1.1 [Codex]` 范围加入唯一 wait 终端编排（exec_command/write_stdin/yield_time_ms/session_id 复用、等待期安静、异常处理） |
| `templates/embedded-c-overlay/.trellis/agents/implement.md` | 新增 "Channel Termination Contract" |
| `templates/embedded-c-overlay/.trellis/agents/check.md` | 新增 "Channel Termination Contract" |
| `.trellis/tasks/09-07-trellis-channel-dispatch-wait/task.json` | 仅清理 4 行既有元数据后缀 CR，使 `git diff --check` 通过（内容未变） |

## 阶段结果

| 阶段 | 状态 | 说明 |
|---|---|---|
| discover-baseline | completed | 确认根目录两套 Skill 逐字节一致（diff -r IDENTICAL），模板尚无该 Skill |
| import-skill-overlay | completed | 导入完整文件树（SKILL.md + 5 references × 两套） |
| update-public-rules | completed | 5 个公共文件写入派发/等待规则，镜像逐字节一致 |
| update-codex-workflow | completed | workflow.md 写入 `[Codex]` 专属终端编排 |
| update-worker-contracts | completed | 两个角色卡补充终止事件契约 |
| extend-contract-tests | completed | 新增 10 个契约测试用例全部通过 |
| run-verification | completed | 全部检查通过 |
| final-report | completed | 本报告 |

## 验收项对照

- 所有实际变更位于 `templates/embedded-c-overlay/`:通过(见变更范围)。
- 完整 Skill 文件树而非片段:`SKILL.md + 5 references`,两套镜像 12 个文件全部就位;契约测试 `test_skill_trees_are_complete_and_symmetric` 覆盖。
- 两套公共文件逐字节一致且描述一次 spawn、一次 wait、终止事件、progress 诊断边界:`diff -r` 为空;契约测试 `test_public_skill_files_byte_identical_between_mirrors` 覆盖。
- Codex 专属过程限定在模板 workflow.md:`exec_command`/`write_stdin`/`yield_time_ms`/`session_id` 只出现在 `[Codex]` 块;契约测试 `test_codex_terminal_terms_scoped_to_codex_blocks_in_workflow` 与 `test_codex_terms_and_plan_status_stay_out_of_public_skill_layer` 覆盖。
- 实施/审查各一条 PowerShell 可解释示例、timeout 可调整、区分 CLI timeout 与 Codex 读取窗口:`workflows.md` 两个 Standard 段均明确"30 分钟只是示例";workflow.md 区分 wait 总上限(退出码 124)与 `yield_time_ms` 单次读取窗口。
- 正常等待禁止重复 wait、额外 channel、progress/完整聊天轮询、执行计划状态查询:SKILL.md "Unique wait pattern"、workers.md "Dispatcher Wait Discipline"、progress-debugging.md "Normal Path vs Diagnostics" 均写明;契约测试反例 `test_standard_dispatch_examples_have_no_polling` 覆盖。
- 契约测试可检测缺失、漂移、越界与错误轮询示例:10 个用例分别对应上述维度。
- standard 审查:实施完成后由主会话按受影响范围派发一次独立 `trellis-check`;不执行 full-scope。

## 验证结果

- 根目录 Python 单测:`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` **pass**(89 个)。
- 模板 Python 单测:`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` **pass**(99 个,含新增 10 个契约测试)。
- Python 语法检查:`python -B -m py_compile` 覆盖根目录与模板的 `.trellis/scripts`、`.claude/hooks`、`.codex/hooks` 下 Python 文件 **pass**。
- `git diff --check`:**pass**(模板改动零告警;同时清理了任务元数据既有 CR 尾部)。
- 模板缓存:`templates/embedded-c-overlay/` 无 `__pycache__`/`.pyc`/`.pyo` **pass**。
- 构建/部署:not applicable(本仓库为工具仓库与发布模板,无可构建产品)。
- 硬件验证:not applicable(仓库不含固件目标或硬件设备;下游项目自行验证)。

## 已知风险与说明

- Skill 覆盖层是完整版本,子任务 2 必须基于文件版本/哈希与用户修改状态设计
  安装与升级,不得把本任务的模板文件直接静默覆盖到既有 1.0 项目。
- `task.json` 因既有元数据 CR 尾部问题做过 4 行尾随 `\r` 清理(内容未变),
  其余 CRLF 行未改动。
- 标准示例引用 `--from <worker>` 与 `--as main`;worker handle 与 `spawn --as`
  应一致,属使用契约而非运行时校验。