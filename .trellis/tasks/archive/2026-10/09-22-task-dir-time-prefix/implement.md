# Implement: 任务目录前缀 MM-DD-HHmm(仅模板)

前置:任务状态 in_progress;改动全部位于 `templates/embedded-c-overlay/`。

## Checklist

1. [ ] **paths.py**:`generate_task_date_prefix()` 改为 `strftime("%m-%d-%H%M")`,更新 docstring(格式说明 + 示例 `"01-21-1435"`)。
2. [ ] **task_store.py**:
   - guard 正则改为 `^(\d{2})-(\d{2})-(?:(\d{4})-)?(.+)$`;保留月/日范围校验;HHmm 组存在时校验 00-23/00-59,不合法则视为普通 slug 不拦截。
   - 判定分支(见 design.md 契约):非当日 → 报错;当日无 HHmm → 剥离警告;当日 HHmm == 当前前缀 → 剥离警告;当日 HHmm ≠ 当前 → 报错(指向今天另一任务的目录名);HHmm 组存在但非 00-23/00-59 → 视为普通 slug 放行。
   - **捕获组序号**:body 由 group(3) 变 group(4),剥离赋值与报错提示 `Pass only the slug body, e.g. --slug {...}` 两处都要改(见 design.md 实施陷阱);guard 对比的是**真实时间 base 前缀**(错峰在其后)。
   - **新增 `_allocate_task_prefix(tasks_dir, base_prefix)`**(design.md §1a):占用 = tasks_dir 直接子目录(排除 `archive/`)名以 `{candidate}-` 开头;`datetime(now.year, MM, DD, HH, mm) + timedelta(minutes=n)` 递增取首个空闲前缀(允许跨日);防御上限 n<1440,耗尽回退 base;调用点在 guard 之后、`dir_name = f"{date_prefix}-{slug}"` 之前。
   - 更新 293-322 行注释与警告/报错文案为新格式(**模板副本行号**,与本项目副本 287-318 有偏移;逻辑一致,已核对)。
3. [ ] **task.py:485**:`--slug` help 文本改为 `MM-DD-HHmm date prefix`。
4. [ ] **文档同步**:`.trellis/workflow.md:42,386`、`.opencode/skills/trellis-brainstorm/SKILL.md:42`;全模板 grep `MM-DD` 复核残留,凡指任务目录格式的表述一并更新(`YYYY-MM-DD` 日期占位、session-insight `--since/--until`、`archive/<YYYY-MM>` 不改);在 workflow.md 前缀说明处补一句错峰语义(同分钟创建自动顺延至空闲分钟,真实创建日期以 task.json 为准)。
5. [ ] **TEMPLATE-CONTENTS.md**:为新测试文件补一行(路径 | 覆盖后新增(1.3 新增) | 契约说明),沿用 `test_write_json_lf.py` 行的格式;不改其他行。
6. [ ] **新增测试** `templates/embedded-c-overlay/.trellis/scripts/tests/test_task_dir_time_prefix.py`:
   - 前缀格式断言(`^\d{2}-\d{2}-\d{4}$`,跨分钟容忍)。
   - `cmd_create(args)` 驱动 guard 四分支(已核实签名为 `cmd_create(args)`,内部 `get_repo_root()` 定位仓库根):TemporaryDirectory 假仓库根;`unittest.mock.patch` 固定 `task_store.get_repo_root`(返回临时根)、`task_store.run_git`(返回 `(0, "main\n", "")`)、`task_store.resolve_default_branch`(返回 `"main"`)、`task_store.generate_task_date_prefix`(直接返回固定前缀,避免 patch datetime 的连带面);args 用 `argparse.Namespace(title, slug, description="", assignee="tester", priority="P2", parent=None, package=None, meta=None, base_branch=None, no_start=True)`——`assignee` 显式给定免除 developer 脚手架,`no_start=True` 免除会话激活(即使测试进程带有 `TRELLIS_CONTEXT_ID` 也保持密闭);临时根无 config → `is_monorepo` False、无 `.claude/.codex/.opencode` → 跳过 jsonl 种子,均无需 patch;createdAt 用格式断言(`^\d{4}-\d{2}-\d{2}$`)不冻结具体日期。四分支:当日完整前缀剥离+警告;当日旧格式剥离+警告(断言 body 用了 group(4),目录名 == `固定前缀-<body>`);非当日报错返回 1 且不建目录;非法 HHmm(如 `09-22-2461-foo`)按普通 slug 放行不剥离。
   - 错峰分配用例:固定 base 前缀连续 create 3 次 → 前缀依次 base、base+1、base+2;预置手工目录占用 base+1 → 跳到 base+2;base `09-22-2359` 第二次 create → 前缀 `09-23-0000`(跨日);patch `_allocate_task_prefix` 返回已占用前缀 → exists 警告防御分支。
   - 排序契约:连续 create 后 `sorted(tasks_dir.iterdir())` 顺序 == 创建顺序。
7. [ ] **禁改清单自查**:`git status` 确认本项目 `.trellis/scripts/`、`.opencode/`、`.claude/`、`.codex/`、`tools/`、`history/` 无改动;任务目录 `09-22-task-dir-time-prefix/` 内的规划工件除外。

## Validation

基线(规划自审实测):模板套件 212 tests OK、本项目套件 154 tests OK。统一使用 `python -B`,避免在模板目录写入 `__pycache__`(安装器发现缓存会拒绝继续)。

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -B -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/paths.py templates/embedded-c-overlay/.trellis/scripts/common/task_store.py templates/embedded-c-overlay/.trellis/scripts/task.py templates/embedded-c-overlay/.trellis/scripts/tests/test_task_dir_time_prefix.py
Get-ChildItem templates/embedded-c-overlay -Recurse -Include *.py,*.md,*.js,*.toml -File | Where-Object { $_.FullName -notmatch '__pycache__' } | Select-String -Pattern "MM-DD"
git diff --check
```

残留扫描允许项(仅这些,其余即漏改):`.codex|.opencode/agents/trellis-research` 的 `YYYY-MM-DD` 日期占位、session-insight `--since/--until YYYY-MM-DD`、design/prd 引文;新格式 `MM-DD-HHmm` 表述属预期。

全部通过后才可进入 review。

## Review Gate

- Review level: reinforced → 派发独立 `trellis-check`(affected-scope);若有 blocking 发现,批量修复后派发全新 `trellis-check` 重审完整 affected-scope,循环至最新一轮报告 blocking 为零;不做逐条小修即重审。
- 审查重点:guard 分支与 PRD 验收项一一对应、本项目禁改清单零改动、TEMPLATE-CONTENTS.md 行格式一致、文档无旧格式残留。

## Rollback Points

- 每步独立文本改动;任一步失败 `git checkout -- templates/embedded-c-overlay/` 整体回滚。
- 无数据迁移、无版本 manifest 变更、无本项目状态变更。
