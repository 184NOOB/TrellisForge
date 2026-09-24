# Design: 任务目录前缀 MM-DD → MM-DD-HHmm(仅模板)

## 边界

只改 `templates/embedded-c-overlay/`;本项目 `.trellis/`、`.opencode/`、`.claude/`、`.codex/`、`tools/`、`history/` 零改动。下游项目在下次 overlay 安装/升级后获得新格式,安装器逻辑不感知前缀内部结构,无需改 `tools/`。

## 改动点与契约

### 1. `common/paths.py::generate_task_date_prefix()`

- `strftime("%m-%d")` → `strftime("%m-%d-%H%M")`(24 小时制,自然零填充,名称排序 == 时间排序)。
- docstring 示例更新为 `"01-21-1435"`。
- 契约:返回值匹配 `^\d{2}-\d{2}-\d{4}$`;月/日为当前本地日期,HHmm 为当前本地时间(分钟精度)。

### 2. `common/task_store.py` guard(issue #377 防重复前缀)

现有 guard 只识别 `^(\d{2})-(\d{2})-(.+)$`。升级为兼容两种粘贴形态:

```python
m = re.match(r"^(\d{2})-(\d{2})-(?:(\d{4})-)?(.+)$", slug)
```

判定规则(月 1-12、日 1-31 校验保留;新增 HHmm 存在时校验 00-23/00-59,降低对普通 slug 的误伤):

- `MM-DD` ≠ 今日 → 报错退出(现行为不变,消息更新为提示新格式)。
- `MM-DD` == 今日且无 HHmm 组 → 剥离 `MM-DD-`,警告(用户按旧习惯带了日期)。
- `MM-DD` == 今日且 `MM-DD-HHmm` == 当前 `date_prefix` → 剥离完整前缀,警告(粘贴了完整目录名;分钟不同则走下一条)。
- `MM-DD` == 今日但 HHmm ≠ 当前分钟 → 报错:这是今天另一个已存在任务的目录名,不是合法 slug 输入。

误伤分析:纯 slug 以两个合法数字组开头(如 `12-30-config`)会被误判——此为现有 guard 既有行为,不扩大;新增 HHmm 可选组只影响"三段数字前缀"形态,实际就是目录名粘贴。

### 3. 帮助文本与文档

- `task.py:485` `--slug` help:`MM-DD date prefix` → `MM-DD-HHmm date prefix`。
- `.trellis/workflow.md:42`(`{MM-DD-name}`)与 `:383`(前缀说明)更新为 `MM-DD-HHmm`。
- `.opencode/skills/trellis-brainstorm/SKILL.md:40` 更新;实施时全模板 grep `MM-DD` 核查 `.claude/`、`.agents/` 等平台副本与 `TEMPLATE-CONTENTS.md`,同步所有指目录格式的表述(`YYYY-MM-DD` 日期占位、归档 `archive/<YYYY-MM>` 等不属于目录前缀格式,不改)。

### 4. `task.json`

`createdAt` 保持 `%Y-%m-%d`。不新增字段:时间信息已由目录名承载,list/排序逻辑不读 createdAt。

### 5. 排序/归档/解析兼容性(确认,不修改)

- `common/tasks.py::iter_active_tasks` 按目录名排序 → 新前缀下同日即创建序;旧格式存量任务(字母开头 slug)同日混排时排在新格式(HHmm 数字)之后,已接受。
- `execution_plan.py` 归档解析、`_find_archived_task_by_dir_name` 按完整目录名匹配,前缀无关。
- 跨年:MM-DD 不含年份,同名冲突由现有 `task_dir.exists()` / 归档检查兜底,行为不变。

## 测试设计(新增 `templates/.../scripts/tests/test_task_dir_time_prefix.py`)

沿用 `test_write_json_lf.py` 的 sys.path 注入模式与 `test_execution_plan.py` 的 TemporaryDirectory 假仓库根模式:

1. 前缀格式:`generate_task_date_prefix()` 匹配 `^\d{2}-\d{2}-\d{4}$` 且与 `datetime.now()` 的 `%m-%d-%H%M` 一致(容忍跨分钟:两次采样断言其一)。
2. guard 行为:guard 逻辑保持 inline 不提取;测试直接驱动 `task_store.cmd_create`,在临时假仓库根内预置最小 `.trellis` 脚手架(developer 标识、tasks 目录、config),并用 `unittest.mock.patch` 固定 `task_store` 命名空间内的 `run_git`(返回 `(0, "main\n", "")`)、`resolve_default_branch`(返回 `"main"`)与 `datetime`(固定时刻),保证测试密闭、不依赖真实 git。覆盖三条行为:当日完整前缀 `MM-DD-HHmm-slug` → 剥离 + 警告 + 目录名正确;当日旧格式 `MM-DD-slug` → 剥离 + 警告;非当日 `01-05-slug` → 返回码 1、不创建目录。另覆盖:同分钟重复创建触发 exists 警告路径。
3. 排序契约:临时 tasks 目录下按新格式命名两个目录(固定时刻相差一分钟,`mock` 驱动两次 create),`sorted(tasks_dir.iterdir())` 顺序 == 创建顺序。

## Tradeoffs

- 目录名变长(+5 字符):换取零状态、自解释的时间排序。
- 本项目与模板格式分叉(本项目仍 MM-DD):用户明确决定;分叉只影响目录名形态,两侧代码各自独立、互不 import。
- 同一分钟创建两个任务:第二个触发现有 exists 警告并复用目录——概率极低,接受;不引入秒级精度以保持名称简短。

## Rollback

改动全部为模板文件的文本级修改,`git checkout -- templates/` 即可整体回滚;无数据迁移、无本项目状态变更。
