# 任务目录前缀升级为 MM-DD-HHmm 以支持同日创建时间排序

## Workflow Settings

- Review level: standard

## Goal

任务目录当前仅有 MM-DD 前缀,同日创建的任务按 slug 字母序排列,不符合"晚创建的任务排在下面"的体感。将发布模板的任务目录前缀升级为 MM-DD-HHmm,使文件系统按名称排序天然等于创建时间顺序。

## Scope(用户明确决定,且与 spec 一致)

父任务:`09-17-trellisforge-1-3-upgrade`(用户指定挂载)。本任务是 1.3 升级的独立可验证子任务;版本号、manifest、结构迁移链、README/接入指南由父任务侧的发布收尾工作统一处理,本任务不等待其他子任务、也不阻塞其进度。

依据 `.trellis/spec/main/tooling/templates-and-docs.md`「下游功能修改的默认归属」:下游功能默认只改模板、根目录 `.trellis/` 为只读参考、契约测试优先落在模板内、manifest/版本号只归发布收尾任务。用户决定与该 spec 默认一致:

- 只修改 `templates/embedded-c-overlay/` 下的发布模板;**不改本项目 `.trellis/` 工作流脚本**(本任务目录内的规划工件除外)。
- 存量任务目录不迁移、不重命名。
- 契约测试只放模板自身的 `.trellis/scripts/tests/` 目录,不在本项目 `.trellis/scripts/tests/` 新增文件。
- 版本 manifest / history / README / 接入指南不在本任务范围(归 v1.3 发布收尾任务)。

## Requirements

1. 模板 `generate_task_date_prefix()` 生成 `MM-DD-HHmm`(24 小时制)前缀,新任务目录名为 `MM-DD-HHmm-slug`。
2. `task.py create` 的 --slug 防重复前缀 guard(issue #377)升级为同时识别旧 `MM-DD-slug` 与新 `MM-DD-HHmm-slug` 两种粘贴形态:当日前缀 → 剥离并警告;非当日 → 报错拒绝。
3. 模板内所有提及 `MM-DD` 目录格式的文档/帮助文本/Skill 同步更新(`workflow.md`、`task.py --slug` help、`.opencode/skills/trellis-brainstorm/SKILL.md`;需核查是否存在其他平台副本)。
4. `task.json` 的 `createdAt` 保持日期格式不变(最小改动,时间信息由目录名承载)。
5. 新增模板内契约测试覆盖:前缀格式、目录名排序即创建顺序、guard 的剥离/报错行为。

## Constraints

- 归档(`archive/<YYYY-MM>/<dir>`)、任务解析、排序逻辑均按目录名工作,不得要求它们感知前缀内部结构;仅确认兼容,不修改。
- Windows PowerShell 兼容、Python UTF-8,遵守 AGENTS.md。
- 本项目 `.trellis/scripts/` 与 `.opencode/`、`.claude/`、`.codex/` 目录零改动。

## Acceptance Criteria

- [ ] 在模板代码上,`generate_task_date_prefix()` 返回值匹配 `^\d{2}-\d{2}-\d{4}$` 且与当前本地时间一致。
- [ ] 同日先后创建的两个任务目录,按名称排序即为创建顺序。
- [ ] `--slug 09-22-1435-foo`(当日完整目录名形态)被剥离为 `foo` 并输出警告;`--slug 01-05-foo`(非当日)报错退出。
- [ ] 模板内不再有指向旧 `MM-DD-slug` 目录格式的过时文档表述。
- [ ] `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` 全绿;本项目 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` 保持全绿(证明未动本项目工作流)。
- [ ] `git diff --check` 干净;改动文件全部位于 `templates/embedded-c-overlay/` 与本任务目录。

## Decisions Log

- 方案 A(MM-DD-HHmm 前缀)— 用户选定;否决 B(仅 list 排序,不解决文件管理器体感)与 C(当日序号,需扫描且有并发竞争)。
- 存量任务不动 — 用户选定;旧格式(字母开头 slug)与新格式(数字 HHmm)同日混排时旧任务靠后,可接受,存量多已归档。
- 只改模板 — 用户选定;与 spec `templates-and-docs.md` 单向同步约束一致(教训:首轮规划误读 AGENTS.md 为双向同步,已纠正)。
- 测试只放模板 tests 目录 — 用户选定;符合 spec "契约测试优先落在模板内"。
- createdAt 不加时间字段、guard 正则具体形态、`%H%M` 24 小时制 — 工程决定,见 design.md。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
