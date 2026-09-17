# 最终验收报告：小修绕过与同一任务后续计划

- 任务：`.trellis/tasks/09-17-small-patch-and-sequel-plans`
- 父任务：`09-17-trellisforge-1-3-upgrade`
- 执行计划：revision 1，5 个 phase 全部由 `plan.py` 推进
- 审查等级：reinforced（独立 `trellis-check` 由主会话在提交前派发）

## 变更文件

功能写入仅位于 `templates/embedded-c-overlay/`：

| 文件 | 变更 |
| --- | --- |
| `.trellis/scripts/common/execution_plan.py` | live 计划解析（指针 + `plans/<n>`）、冻结只读护栏、`cmd_sequel`、协议/状态/冻结摘要、artifact 改为 live 目录解析 |
| `.trellis/scripts/plan.py` | 新增 `sequel --reason` 子命令与用法说明 |
| `.trellis/workflow.md` | Phase 2 门禁改为按计划状态分流；新增大修/小修硬规则与完成态出口 |
| `.trellis/agents/implement.md`、`.trellis/agents/check.md` | Channel 运行时实施/审查代理协议同步 |
| `.claude/agents/trellis-implement.md`、`.claude/agents/trellis-check.md` | Claude 子代理协议同步 |
| `.codex/agents/trellis-implement.toml` | Codex 子代理协议同步 |
| `.opencode/agents/trellis-implement.md`、`.opencode/agents/trellis-check.md` | OpenCode 子代理协议同步 |
| `.claude/hooks/plan-pretool-reminder.py` | live 计划文件提醒；完成态给出小修/sequel 建议；指针与冻结历史篡改提醒 |
| `.trellis/scripts/tests/test_execution_plan.py` | 新增 13 项 sequel/指针/完成态测试 |
| `.trellis/scripts/tests/test_small_patch_and_sequel_contract.py` | 新增 9 项合约测试（workflow/代理文案、CLI 帮助、PreToolUse Hook） |

未改动：`VERSION`、历史 canonical、版本 manifest、结构迁移链、README、接入指南；根目录自用 `.trellis/`（除本任务 runtime 工件）、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/` 无本任务功能改动。

## 阶段结果

1. `plan-runtime`：live 解析、指针 fail-closed、冻结目录护栏、`sequel`（冻结 → 新 proposed 骨架 → 新账本 `plan_sequel` 事件 → 指针最后落盘，失败回滚）。旧单文件布局零迁移继续可用。
2. `protocol-hooks`：协议块在 live 计划完成后给出「小修不碰计划文件 / 同需求 sequel / 换需求开新任务」三条出口；`status`/breadcrumb 只详列 live 并附冻结摘要；Claude Hook 按 live 解析并提示完成态。
3. `workflow-agents`：workflow 门禁改为按计划状态分流；四平台 implement 协议写入小修硬规则、阻塞修复默认小修、sequel 与新任务分界；三份 check 协议改指向 live 计划。
4. `tests`：模板测试从 154 增至 176，覆盖旧单文件兼容、sequel 冻结、未完成拒绝、第三次 sequel、损坏/歧义指针 fail-closed、冻结目录禁止变更、完成 report 不可改写、`revise` 不创建 sequel、`status` 只详列 live、协议完成态出口、Hook 行为与合约文案。
5. `verify-final`：最终复跑全部检查并出具本报告。

## 检查结果

- 模板单元测试：pass — `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`，176 项通过（基线 154 + 新增 22）。
- 根目录只读回归：pass — `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`，154 项通过；根目录自用实现在本任务中无功能 diff。
- 模板 Python 语法：pass — `py_compile` 覆盖 `templates/embedded-c-overlay/.trellis/scripts`、`.claude/hooks`、`.codex/hooks` 全部 `.py`。
- 空白检查：pass（功能范围）— `git diff --check -- templates/` 退出码 0。
- 构建/部署/硬件验证：not applicable — 本仓库不产出固件或可执行产品，无硬件目标。

## 已知风险与说明

- 全仓库 `git diff --check` 会命中一条既有告警：`.trellis/tasks/09-17-trellisforge-1-3-upgrade/task.json:22` 的 CRLF 尾随空白（`.trellis/spec/main/tooling/python.md` 已记录该 `write_json` Windows 换行根因）。该文件是父任务 runtime 工件，属本任务写入范围之外，未修改。
- `sequel` 不提供自动回滚命令：指针损坏或冻结目录缺失时所有变更 fail-closed，由人工按任务目录修复（设计如此，避免静默改写历史）。
- 完成态小修与 `sequel` 的判定由 workflow/Agent 文本与协议注入约束模型，`plan.py` 不做「是否为小修」的运行时分类；`sequel` 只做客观前置校验（approved、全部 phase completed、唯一 terminal report、审计无 drift、`--reason` 非空）。
- 根目录自用 Trellis 本轮不获得该能力，需待下游模板安装/同步或另开根目录任务。

## 完成态小修追加记录

- `verify-final` 完成后对 `.claude/hooks/plan-pretool-reminder.py` 做了一处机械小修：删除 `live_number` 未使用变量的赋值，改为 `ep.resolve_live_plan(task_dir)[1]`（无行为变化，同一模块，不改验收）。
- 追加后按最终快照重跑全部检查：模板单测 176 项通过，根目录只读回归 154 项通过，模板 Python `py_compile` 通过，`git diff --check -- templates/` 退出码 0。
- 该小修未新建 phase、未 `revise`、未重建任务，符合本任务交付的完成态小修规则。