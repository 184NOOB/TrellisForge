# 任务目录前缀升级为 MM-DD-HHmm 以支持同日创建时间排序

## Workflow Settings

- Review level: reinforced

## Goal

任务目录当前仅有 MM-DD 前缀,同日创建的任务按 slug 字母序排列,不符合"晚创建的任务排在下面"的体感;批量创建子任务常发生在同一分钟,更无先后可言。将发布模板的任务目录前缀升级为 MM-DD-HHmm 并对同分钟创建自动错峰,使文件系统按名称排序天然等于创建时间顺序、子任务目录序与父任务 children 挂接序一致。

## Scope(用户明确决定,且与 spec 一致)

父任务:`09-17-trellisforge-1-3-upgrade`(用户指定挂载)。本任务是 1.3 升级的独立可验证子任务;版本号、manifest、结构迁移链、README/接入指南由父任务侧的发布收尾工作统一处理,本任务不等待其他子任务、也不阻塞其进度。

依据 `.trellis/spec/main/tooling/templates-and-docs.md`「下游功能修改的默认归属」:下游功能默认只改模板、根目录 `.trellis/` 为只读参考、契约测试优先落在模板内、manifest/版本号只归发布收尾任务。用户决定与该 spec 默认一致:

- 只修改 `templates/embedded-c-overlay/` 下的发布模板;**不改本项目 `.trellis/` 工作流脚本**(本任务目录内的规划工件除外)。
- 存量任务目录不迁移、不重命名。
- 契约测试只放模板自身的 `.trellis/scripts/tests/` 目录,不在本项目 `.trellis/scripts/tests/` 新增文件。
- 版本 manifest / history / README / 接入指南不在本任务范围(归 v1.3 发布收尾任务)。

## Requirements

1. 模板 `generate_task_date_prefix()` 生成 `MM-DD-HHmm`(24 小时制)前缀,新任务目录名为 `MM-DD-HHmm-slug`。
2. **同分钟错峰(方案 B,用户选定)**:创建任务时,若活跃任务目录中已存在相同 `MM-DD-HHmm` 前缀的任务,前缀自动顺延至第一个空闲分钟(允许跨过 23:59 进入次日),使同一分钟批量创建的任务(含父任务批量创建子任务)目录名顺序 == 创建先后顺序 == 父任务 `children` 数组的挂接顺序。
3. `task.py create` 的 --slug 防重复前缀 guard(issue #377)升级为同时识别旧 `MM-DD-slug` 与新 `MM-DD-HHmm-slug` 两种粘贴形态:当日真实时间前缀 → 剥离并警告;非当日或 HHmm 不符 → 报错拒绝。
4. 模板内所有提及 `MM-DD` 目录格式的文档/帮助文本/Skill 同步更新(`workflow.md`、`task.py --slug` help、`.opencode/skills/trellis-brainstorm/SKILL.md`;需核查是否存在其他平台副本),并补充一句错峰语义说明。
5. `task.json` 的 `createdAt` 保持真实日期不变(最小改动;目录名的顺延分钟仅为排序记号,真实创建日期以 task.json 为准)。
6. 新增模板内契约测试覆盖:前缀格式、目录名排序即创建顺序、同分钟错峰分配(含跨日)、guard 的剥离/报错行为。

已核实无需改动:`task.py list` 树形视图本就按父任务 `children` 数组顺序显示子任务(模板 `task.py:327-337`),本任务不改 list 逻辑。

## Constraints

- 归档(`archive/<YYYY-MM>/<dir>`)、任务解析、排序逻辑均按目录名工作,不得要求它们感知前缀内部结构;仅确认兼容,不修改。
- Windows PowerShell 兼容、Python UTF-8,遵守 AGENTS.md。
- 本项目 `.trellis/scripts/` 与 `.opencode/`、`.claude/`、`.codex/` 目录零改动。

## Acceptance Criteria

- [ ] 在模板代码上,`generate_task_date_prefix()` 返回值匹配 `^\d{2}-\d{2}-\d{4}$` 且与当前本地时间一致。
- [ ] 同日先后创建的两个任务目录,按名称排序即为创建顺序。
- [ ] 同一分钟内连续创建 3 个任务,前缀依次为 base、base+1 分钟、base+2 分钟,目录名排序 == 创建顺序;预置占用目录时空闲分钟被正确跳过。
- [ ] 23:59 内错峰顺延跨过午夜时,前缀变为次日 `00:00`(排序单调不破坏);`task.json` 的 `createdAt` 仍为真实创建日期。
- [ ] `--slug 09-22-1435-foo`(当日完整目录名形态,HHmm == 当前真实时间)被剥离为 `foo` 并输出警告;`--slug 01-05-foo`(非当日)与 `--slug 09-22-1030-foo`(合法 HHmm 但非当前分钟,即今天另一任务的目录名)报错退出、不创建目录;`--slug 09-22-2461-foo`(非法 HHmm)按普通 slug 放行不剥离。
- [ ] 模板内不再有指向旧 `MM-DD-slug` 目录格式的过时文档表述,且文档含错峰语义说明。
- [ ] `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` 全绿;本项目 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` 保持全绿(证明未动本项目工作流)。
- [ ] `git diff --check` 干净;改动文件全部位于 `templates/embedded-c-overlay/` 与本任务目录。

## Decisions Log

- 方案 A(MM-DD-HHmm 前缀)— 用户选定;否决"仅 list 时间戳排序"(不解决文件管理器体感)与"当日序号前缀"(需扫描且并发竞争)。
- **同分钟错峰 = 方案 B(分钟顺延)— 用户选定**(2026-09-22 第二轮讨论):同 `MM-DD-HHmm` 前缀已被占用时顺延至空闲分钟。已披露并被接受的代价:目录名分钟可能超前真实时间(顺延记号),真实创建日期以 `task.json.createdAt` 为准。否决:秒级精度 A(目录名再 +2 字符)、约定序号 slug C(靠自觉不根治)、不处理 D(文件管理器同分钟字母序)。背景证据:`task.py list` 树视图已按 children 数组排序(模板 `task.py:327-337`),缺口仅在文件管理器/目录名排序;批量创建子任务常发生在同一分钟。
- 存量任务不动 — 用户选定;旧格式(字母开头 slug)与新格式(数字 HHmm)同日混排时旧任务靠后,可接受,存量多已归档。
- 只改模板 — 用户选定;与 spec `templates-and-docs.md` 单向同步约束一致(教训:首轮规划误读 AGENTS.md 为双向同步,已纠正)。
- 测试只放模板 tests 目录 — 用户选定;符合 spec "契约测试优先落在模板内"。
- Review level: reinforced — 用户明确选定(替代默认 standard);blocking 修复后需全新独立 trellis-check 重审至零 blocking。
- 规划自审(2026-09-22):基线测试实测全绿(模板 212 / 本项目 154);确认无测试冻结被改文本;补入 TEMPLATE-CONTENTS.md 新测试行(分支先例 7f01ce2);修正文档行号锚点(workflow.md:386、SKILL.md:42);验证统一 `python -B` 防模板内 `__pycache__`(安装器拒绝缓存)。
- 规划自审第二轮(2026-09-22):模板 task_store 副本 guard 位于 293-322 行(与本项目副本 287-318 有偏移,逻辑一致),implement.md 锚点已按模板副本修正;核实 `cmd_create(args)` 仅收 args、内部 `get_repo_root()`,测试 mock 点改为 patch `task_store.get_repo_root` + `no_start=True` + 显式 `assignee`,免除 developer 脚手架并保证会话激活密闭;核实 `resolve_task_dir` 精确名匹配、JS/py hooks 无日期前缀解析(全量 grep 零命中),兼容性结论升级为逐项取证。
- 规划自审第三轮(2026-09-22):发现并记录两个实施陷阱——guard 新正则捕获组序号变化(body 由 group(3)→group(4),剥离赋值与报错提示两处)与 `09-22-1435` 无前缀 body 的回溯边界;非法 HHmm(>23/>59)放行分支纳入 guard 契约并加入测试(三分支→四分支);取证 `archive_task_dir` 月份目录取归档时刻 `datetime.now()`(不解析前缀)、`find_task_by_name` 后缀匹配兼容新格式;跨年排序缺陷(01-xx 排在 12-xx 前)确认为现状既有、不在本任务修复;Validation 增加全模板 MM-DD 残留扫描命令与允许残留清单。
- createdAt 不加时间字段、guard 正则具体形态、`%H%M` 24 小时制 — 工程决定,见 design.md。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
