# Final Report: 任务目录前缀 MM-DD-HHmm(仅模板)

- Task: `.trellis/tasks/09-22-task-dir-time-prefix`
- Execution plan: schema 3, revision 1,p1–p5 全部 completed
- 报告日期: 2026-09-27
- 结论: 5 个阶段全部完成;本任务 required_checks 全绿;安装器/升级工具套件存在与本任务无关的预存在失败(见 §3),发布收尾更新 manifest 后预期恢复。

## 1. 变更文件清单

模板交付物(全部位于 `templates/embedded-c-overlay/`,共 6 处修改 + 1 个新增文件):

| 文件 | 变更 |
| --- | --- |
| `.trellis/scripts/common/paths.py` | `generate_task_date_prefix()` 改为 `strftime("%m-%d-%H%M")`,docstring 示例 `01-21-1435`,保持纯函数 |
| `.trellis/scripts/common/task_store.py` | 新增 `_allocate_task_prefix()`(同分钟错峰、占用跳过、允许跨日、防御上限 n<1440);guard 正则升级为 `^(\d{2})-(\d{2})-(?:(\d{4})-)?(.+)$` + 四分支判定,body 改用 group(4);`cmd_create` 以真实时间 base 前缀做 guard、错峰分配后组装 `dir_name`;警告/报错文案为新格式 |
| `.trellis/scripts/task.py` | `--slug` help 改为 `MM-DD-HHmm date prefix` |
| `.trellis/workflow.md` | 任务目录格式改 `{MM-DD-HHmm-name}`;`--slug` 段改 `MM-DD-HHmm-` 并补错峰语义(同分钟顺延至空闲分钟;目录名分钟为排序记号,真实创建日期以 `task.json` `createdAt` 为准) |
| `.opencode/skills/trellis-brainstorm/SKILL.md` | 目录前缀说明改 `MM-DD-HHmm-` |
| `TEMPLATE-CONTENTS.md` | 按既有行格式为新增测试补一行(1.3 新增) |
| `.trellis/scripts/tests/test_task_dir_time_prefix.py`(新增) | 12 项契约测试:前缀格式、guard 四分支、错峰 3 连建/占用跳过/跨日、排序契约、exists 防防御分支 |

任务目录工件(plan.py 机制产物): `execution-plan.json`、`execution-events.jsonl`、`final-report.md`;`prd.md` / `design.md` / `implement.md` / `task.json` / `implement.jsonl` / `check.jsonl` 为规划期工作流更新的工件。

本项目根目录 `.trellis/scripts/`、`.opencode/`、`.claude/`、`.codex/`、`tools/`、`history/`、`docs/`、`README.md`、`VERSION`:本任务零改动(取证见 §5)。

## 2. 逐阶段结果

| 阶段 | 状态 | 检查记录 |
| --- | --- | --- |
| p1-code-prefix-stagger | completed | py-compile-code → pass |
| p2-contract-tests | completed | unittest-new-file → pass(12/12);py-compile-test → pass |
| p3-docs-sync | completed | residual-scan → pass(17 处命中全部为白名单);py-compile-task → pass |
| p4-full-validation | completed | unittest-template-all → pass(224);unittest-root-all → pass(154);py-compile-touched → pass;git-diff-check → pass;boundary-audit → pass |
| p5-report | completed | 终态三项复跑 pass;report-written → pass(本文件) |

p3 期间为满足 implement.md「警告/报错文案为新格式」追加两处同任务小修:guard 旧格式分支警告文案去掉裸 `MM-DD` 字样、测试 docstring 同步措辞;随后复跑受影响的测试、语法检查与残留扫描,结论不变。

## 3. 检查结果分类

- 静态检查(py_compile):**pass** — 4 个改动 Python 文件批量语法检查通过。注意 `-B` 不阻止 `py_compile` 写缓存,统一以 `PYTHONPYCACHEPREFIX` 指向临时目录执行,并确认 `templates/` 无今日新增 `__pycache__`/pyc(today_pyc=0)。
- 单元测试:**pass** — 模板套件 `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` → 224 tests OK(基线 212 + 新增 12);根目录套件 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` → 154 tests OK(本项目自用工作流未受牵连)。
- 安装器/升级工具测试:`python -B -m unittest discover -s tests -p "test_*.py"` → **fail(26 failures,预存在的 1.3 累积漂移,非本任务回归)**:
  - 安装校验 fail-closed 的漂移清单包含 20+ 个本任务未改动的文件(如 `.trellis/scripts/common/io.py`、`execution_plan.py`、`planning_gate.py`、`.opencode/lib/session-utils.js` 等);
  - hash 取证:`.trellis/scripts/common/io.py` 的 HEAD 内容已不等于 1.2 manifest canonical(漂移在本任务之前);`.trellis/scripts/common/paths.py` 的 HEAD 内容等于 1.2 manifest canonical,本任务的修改是它首次 1.3 漂移——同样属发布收尾职责;
  - 该套件不在本任务执行计划的 required_checks 内;v1.3 发布收尾更新版本 manifest/history 后预期恢复。
- 安装/升级 PowerShell 冒烟:**not run** — 本任务未修改 `tools/` 安装器与升级清单;冒烟与目标仓库部署归发布收尾任务。
- 下游验证:**not applicable** — 本仓库无下游目标;目标项目验证由使用者在目标项目中执行。
- 构建/硬件验证:**not applicable** — 本仓库不产出固件或可执行产品,无构建与硬件目标。

## 4. PRD 验收项逐条映射

| # | 验收项 | 结果 | 证据 |
| --- | --- | --- | --- |
| 1 | 前缀匹配 `^\d{2}-\d{2}-\d{4}$` 且与当前本地时间一致 | pass | `DatePrefixFormatTests`(双采样容忍跨分钟) |
| 2 | 同日先后创建的两个任务,目录名排序 == 创建顺序 | pass | `test_directory_sort_order_matches_creation_order`(stdout 目录名与 sorted 一致) |
| 3 | 同分钟 3 连建 → base、base+1、base+2;预置占用跳过 | pass | `test_same_minute_creates_take_successive_minutes`、`test_occupied_minute_is_skipped` |
| 4 | 23:59 顺延跨夜 → 次日 `00:00`;`createdAt` 仍为真实日期 | pass | `test_stagger_crosses_midnight`(09-22-2359 → 09-23-0000,createdAt 为真实日期) |
| 5 | guard 四分支:当日完整前缀剥离+警告;非当日报错且不建目录;合法 HHmm≠当前分钟报错;非法 HHmm 放行不剥离 | pass | `SlugGuardTests` 四个用例 + `test_created_at_stays_real_date` |
| 6 | 模板内无旧格式过时表述,文档含错峰语义 | pass | p3 residual-scan 仅剩 `YYYY-MM-DD` 占位与 `MM-DD-HHmm` 新格式;`workflow.md:386` 含错峰与 `createdAt` 说明 |
| 7 | 模板套件与根套件全绿 | pass | 终态复跑 224 OK / 154 OK |
| 8 | `git diff --check` 干净;改动仅在 `templates/` 与本任务目录 | pass(含既有噪声说明,见 §5) | `git diff --check -- . ":!.trellis/tasks"` exit 0;模板单独 diff-check exit 0;全量原始输出仅命中 `.trellis/tasks/**` 的 CRLF 既有噪声 |

## 5. 已知偏差与残余风险

1. `git diff --check` 全量原始输出在 `.trellis/tasks/**` 命中 CRLF "trailing whitespace":根 `.trellis/scripts/common/io.py` 的 `write_json` 未做 LF 修复(仅模板副本已修),属 spec 已记录的已知问题,根级修复需独立任务授权;执行计划已声明"任务目录规划工件与 task.json 除外";命中还包含 09-17/09-24 等其他会话的任务文件(mtime 9/25–9/26,非本任务)。
2. 安装器测试的 1.3 累积漂移:manifest/history 更新归发布收尾;本任务按要求只改模板,未提前扩展到 manifest。
3. 错峰分钟可能超前真实时间(方案 B 已披露并接受的代价):目录名分钟是排序记号,真实创建日期以 `task.json` `createdAt` 为准。
4. 跨年排序:`MM-DD` 无年份,次年 1 月任务排在上一年 12 月之前,为现状既有,本任务不改变也不修复。
5. 并发:两个并行 create 可能算得同一空闲前缀;slug 不同则共享前缀(退化为同分钟字母序),slug 相同触发 exists 警告——现状级兜底,不加锁。
6. 模板内 12 个 2026-09-25 既有 `__pycache__`/pyc 非本任务引入;本任务产生的 pyc 已清理。这些既有缓存若随发布安装会被安装器拒绝,清理与发布检查归发布收尾。
7. 边界取证:`.opencode/package.json`(mtime 2026-09-15)与 09-17/09-24/09-26/09-27 任务目录为其他会话的既有改动/未跟踪目录,本任务未触碰;禁改目录本任务零改动。

## 6. 未做项(明确归发布收尾或其他任务)

- 版本号、`history/embedded-c-overlay/versions/1.3` manifest、结构迁移链、README、`docs/接入指南.md` 更新。
- 根目录自用 `.trellis/scripts/` 的同步回移(含 `io.py` LF 修复与 guard/错峰逻辑)。
- 存量任务目录迁移/重命名;归档、排序与解析逻辑(已逐项取证兼容,不修改)。