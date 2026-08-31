# Trellis 维护合同

本文件保护项目级 Trellis 定制不被上游更新意外覆盖。它是通用模板，不能替代
目标仓库自己的 `AGENTS.md` 或产品 Spec。

## 更新前

1. 确认目标仓库 Git 工作区状态并保存当前差异。
2. 先运行 `trellis update --dry-run`，查看上游将修改的文件。
3. 若 Trellis 版本变化，使用 `--create-new` 或等价方式取得上游新文件，
   再逐项比较和合并；禁止使用整体 `--force` 覆盖项目定制。

## 受保护的项目定制

- `.trellis/workflow.md`
- `.trellis/agents/`
- `.trellis/scripts/common/planning_gate.py` 及其任务/会话隔离依赖和测试
- `.trellis/spec/shared/` 中的项目维护与验证合同
- `.agents/skills/` 项目级 Skill，特别是定制 `trellis-finish-work`
- `.claude/` 和 `.codex/` 的项目代理、Hook 与平台配置
- 根 `AGENTS.md` 的 Trellis 管理块及项目规则

不得复制或覆盖 `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/`
或 `.trellis/.template-hashes.json` 等目标仓库运行状态。

## 更新后

重新检查规划门禁、会话隔离、Grill Me/adapter、审查 profile、auto/inline 派发、
上下文注入、禁止自动提交和未跟踪任务审查。至少运行：

```powershell
python -B ./.trellis/scripts/tests/test_planning_gate.py
python -B ./.trellis/scripts/tests/test_active_task_session_isolation.py
python -m py_compile .claude/hooks/*.py .codex/hooks/*.py
git diff --check
```

最后创建一个小型文档任务做规划、审批、`task.py start`、代理派发和 Hook 注入
冒烟验证，再接受上游更新。
