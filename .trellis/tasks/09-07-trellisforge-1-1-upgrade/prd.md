# 升级 TrellisForge 到 1.1 并提供 1.0 升级方案

## Workflow Settings

- Review level: standard

## Goal

TBD.

## Requirements

- TBD

## Acceptance Criteria

- [ ] TBD

## Planning Convergence

- Status: pending
- Blocking user decisions: pending
- Blocking technical decisions: pending
- Final summary ready: no

## Handoff Notes From Child Task 1（子任务 1 交接）

- 模板 `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/command-reference.md`（及其 `.claude/skills/trellis-channel/references/command-reference.md` 镜像）与根上游源 `.agents/skills/trellis-channel/references/command-reference.md` **并非逐字节一致**。做版本识别 / 哈希迁移比对时，不要把这个差异误判为「用户改动」或「内容漂移」。差异共两处：
  1. 模板副本多约 6 行公共规则（如 "Standard dispatch use..." 段落），是子任务 1 有意写入的交付内容。
  2. 模板副本比根源少 1 个空行——根源自带一个多余空行，子任务 1 为过 `git diff --check`（新增文件报空行错误）从**模板副本**截除；只因根源在子任务 1 禁改清单内不能改，才留下这处差异。
- 建议正解（子任务 2 内处理）：把根源该多余空行规范化删掉，令「根上游源 = 模板基准」重新字节一致，并据此更新哈希 / 版本基准；而不是在迁移比对时把该差异当作异常兼容特例。

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
