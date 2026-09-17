# 小修绕过与同一任务后续计划实施计划

## 实施前条件

- [ ] 用户已明确批准最新规划摘要；批准前不得运行 `task.py start` 或修改模板产品文件。
- [ ] 当前任务仍由本会话的精确 `session:*` 指针绑定，状态为 `planning`；启动后才进入 `in_progress`。
- [ ] 读取 `prd.md`、`design.md`、本文件、`implement.jsonl`、`check.jsonl` 和其中列出的 Spec。
- [ ] 用 `git status --short` 记录现有用户改动；功能写入仅允许位于 `templates/embedded-c-overlay/`。
- [ ] 确认根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/` 不在写入范围。

## 实施批次

### 1. 执行计划 live 解析与 sequel

- [ ] 在模板 `execution_plan.py` 中把 `plan_path` / `events_path` / report 路径解析到 live 目录；兼容任务根单文件布局。
- [ ] 增加指针格式、冻结目录只读、损坏指针 fail closed。
- [ ] 实现 `cmd_sequel`：仅当 live plan 全部完成后冻结旧计划并创建下一份 proposed live plan。
- [ ] `plan.py` 增加 `sequel --reason`；现有子命令继续只作用于 live。
- [ ] `revise` 继续只重开 live，不创建 sequel，也不能把已完成 report 改成普通阶段。

### 2. 协议、breadcrumb 与完成态出口

- [ ] `plan_protocol_block` / `plan_breadcrumb` / `format_status` 只展示 live；可附带冻结计划序号。
- [ ] live plan 全部完成时，协议提示小修不碰计划文件，大修走 `sequel`。
- [ ] Round 1 文案保留“无计划时先创建”，但不再把已完成 live plan 说成必须立刻再写一份根文件。

### 3. 工作流与 Agent 合同

- [ ] 更新模板 `.trellis/workflow.md`：小修硬规则（用户明确声明优先，否则适用四条客观门槛；阻塞修复默认小修，过多冗杂复杂才 sequel）、完成态出口、sequel 与新任务分界；改写“Phase 2 source edits require approved execution-plan.json”为按计划状态分流。
- [ ] 更新 Channel/Claude/Codex/OpenCode implement Agent 的执行计划协议。
- [ ] 更新 check Agent 对 live `execution-plan.json` 的引用，使其指向 live 解析结果而不是写死根文件。
- [ ] Claude `plan-pretool-reminder.py` 对 live 计划文件提醒；完成态编辑业务源码时只给 advisory 小修提示。
- [ ] OpenCode 插件继续桥接 Python，不复制新路径常量。

### 4. 测试

- [ ] 扩展模板 `test_execution_plan.py`：旧单文件兼容、sequel 冻结、未完成拒绝 sequel、第三次 sequel、损坏指针、已完成 report 仍不可改写、`status` 只详列 live。
- [ ] 增加或扩展模板合约测试，锁定 workflow / implement 协议含用户声明优先的小修门槛、阻塞修复默认小修和 `sequel`，且完成态不再被写成必须 `revise`。
- [ ] 不在根目录 `.trellis/scripts/tests/` 添加本任务功能测试。

### 5. 验证与边界审计

- [ ] 运行模板单元测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 只读运行仓库自用 Trellis 回归，确认根目录未被本任务改动：

  ```powershell
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 检查模板 Python 语法：

  ```powershell
  Get-ChildItem templates/embedded-c-overlay/.trellis/scripts,templates/embedded-c-overlay/.claude/hooks,templates/embedded-c-overlay/.codex/hooks -Recurse -Filter *.py -File |
    ForEach-Object { python -m py_compile $_.FullName }
  ```

- [ ] `git diff --check`
- [ ] 确认根目录自用实现无本任务功能 diff。
- [ ] 构建、部署、硬件验证报告 `not applicable`。

## 回滚点

- 批次 1 失败：删除模板 `plans/` 解析与 `sequel`，恢复单文件路径。
- 批次 3 失败：workflow / Agent 文案回退，不留下“可以 sequel 但 CLI 没有”的半截合同。
- 不提供自动把 sequel 指针拨回上一份的 CLI，避免改写冻结历史。

## 发布边界

- 不更新 `VERSION`、canonical、manifest、结构链、README、接入指南。
- 不修改根目录自用 Trellis。
