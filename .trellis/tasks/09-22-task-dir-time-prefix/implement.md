# Implement: 任务目录前缀 MM-DD-HHmm(仅模板)

前置:任务状态 in_progress;改动全部位于 `templates/embedded-c-overlay/`。

## Checklist

1. [ ] **paths.py**:`generate_task_date_prefix()` 改为 `strftime("%m-%d-%H%M")`,更新 docstring(格式说明 + 示例 `"01-21-1435"`)。
2. [ ] **task_store.py**:
   - guard 正则改为 `^(\d{2})-(\d{2})-(?:(\d{4})-)?(.+)$`;保留月/日范围校验;HHmm 组存在时校验 00-23/00-59,不合法则视为普通 slug 不拦截。
   - 判定分支(见 design.md 契约):非当日 → 报错;当日无 HHmm → 剥离警告;当日 HHmm == 当前前缀 → 剥离警告;当日 HHmm ≠ 当前 → 报错(指向今天另一任务的目录名)。
   - 更新 287-316 行注释与警告/报错文案为新格式。
3. [ ] **task.py:485**:`--slug` help 文本改为 `MM-DD-HHmm date prefix`。
4. [ ] **文档同步**:`.trellis/workflow.md:42,383`、`.opencode/skills/trellis-brainstorm/SKILL.md:40`;全模板 grep `MM-DD` 核查 `.claude/`、`.agents/`、`TEMPLATE-CONTENTS.md` 等副本,凡指任务目录格式的表述一并更新(`YYYY-MM-DD` 日期占位、`archive/<YYYY-MM>` 不改)。
5. [ ] **新增测试** `templates/embedded-c-overlay/.trellis/scripts/tests/test_task_dir_time_prefix.py`:
   - 前缀格式断言(`^\d{2}-\d{2}-\d{4}$`,跨分钟容忍)。
   - `cmd_create` 驱动 guard 三分支 + exists 警告路径:TemporaryDirectory 假仓库根,预置最小 `.trellis` 脚手架;`unittest.mock.patch` 固定 `task_store.run_git`、`task_store.resolve_default_branch`、`task_store.generate_task_date_prefix`(直接返回固定前缀,避免 patch datetime 的连带面)与 `task_store` 内 `datetime`(供 createdAt 断言,可放宽为格式断言)。
   - 排序契约:两次 create(不同固定前缀)后 `sorted` 顺序 == 创建顺序。
6. [ ] **禁改清单自查**:`git status` 确认本项目 `.trellis/scripts/`、`.opencode/`、`.claude/`、`.codex/`、`tools/`、`history/` 无改动;任务目录 `09-22-task-dir-time-prefix/` 内的规划工件除外。

## Validation

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/paths.py templates/embedded-c-overlay/.trellis/scripts/common/task_store.py templates/embedded-c-overlay/.trellis/scripts/task.py templates/embedded-c-overlay/.trellis/scripts/tests/test_task_dir_time_prefix.py
git diff --check
```

全部通过后才可进入 review(standard:派发 trellis-check)。

## Review Gate

- Review level: standard → 派发独立 `trellis-check`,范围:模板改动文件 + 新测试;重点核对 guard 分支与 PRD 验收项一一对应、本项目零改动。

## Rollback Points

- 每步独立文本改动;任一步失败 `git checkout -- templates/embedded-c-overlay/` 整体回滚。
- 无数据迁移、无版本 manifest 变更、无本项目状态变更。
