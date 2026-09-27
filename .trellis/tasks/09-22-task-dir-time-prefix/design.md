# Design: 任务目录前缀 MM-DD → MM-DD-HHmm(仅模板)

## 边界

只改 `templates/embedded-c-overlay/`;本项目 `.trellis/`、`.opencode/`、`.claude/`、`.codex/`、`tools/`、`history/` 零改动。下游项目在下次 overlay 安装/升级后获得新格式,安装器逻辑不感知前缀内部结构,无需改 `tools/`。

## 改动点与契约

### 1. `common/paths.py::generate_task_date_prefix()`

- `strftime("%m-%d")` → `strftime("%m-%d-%H%M")`(24 小时制,自然零填充,名称排序 == 时间排序)。
- docstring 示例更新为 `"01-21-1435"`。
- 契约:返回值匹配 `^\d{2}-\d{2}-\d{4}$`;月/日为当前本地日期,HHmm 为当前本地时间(分钟精度)。保持纯函数、不感知仓库状态(错峰分配放在 task_store,见 §1a)。

### 1a. 同分钟错峰分配(方案 B,用户决定)

新增 `task_store._allocate_task_prefix(tasks_dir: Path, base_prefix: str) -> str`:

- **调用点**:`cmd_create` 内 guard 之后、`dir_name` 组装之前,`date_prefix = _allocate_task_prefix(tasks_dir, date_prefix)`。guard 始终对比**真实时间 base 前缀**(错峰在其后发生,不影响 guard 语义)。
- **占用判定**:`tasks_dir` 直接子目录(排除 `archive/`)中存在名称以 `f"{candidate}-"` 开头者即占用。只看活跃区:归档后前缀复用无害(排序仅对活跃列表有意义)。
- **顺延算法**:`base_dt = datetime(now.year, MM, DD, HH, mm)`(MM/DD/HH/mm 解析自 base_prefix,年份取当前系统年,避免 strptime 无年份及 1900 非闰年 2/29 问题);候选 = `(base_dt + timedelta(minutes=n)).strftime("%m-%d-%H%M")`,n 从 0 递增取第一个空闲值。
- **跨日**:23:59 顺延 → 次日 `00:00`,日期段随 `%m-%d` 自然变化,排序单调不破坏。
- **防御上限**:n < 1440;理论不可达,耗尽时回退 base_prefix(由既有 exists 警告兜底)。
- **并发**:两个并行 create 可能算出同一空闲前缀;slug 不同则共享前缀(同分钟内退化字母序,与现状一致),slug 相同则后到者触发 exists 警告——均为现状级兜底,不加锁。

### 2. `common/task_store.py` guard(issue #377 防重复前缀)

现有 guard 只识别 `^(\d{2})-(\d{2})-(.+)$`。升级为兼容两种粘贴形态:

```python
m = re.match(r"^(\d{2})-(\d{2})-(?:(\d{4})-)?(.+)$", slug)
```

判定规则(月 1-12、日 1-31 校验保留;新增 HHmm 存在时校验 00-23/00-59,降低对普通 slug 的误伤):

- `MM-DD` ≠ 今日 → 报错退出(现行为不变,消息更新为提示新格式)。
- `MM-DD` == 今日且无 HHmm 组 → 剥离 `MM-DD-`,警告(用户按旧习惯带了日期)。
- `MM-DD` == 今日且 `MM-DD-HHmm` == 当前**真实时间 base 前缀**(错峰顺延前) → 剥离完整前缀,警告(粘贴了完整目录名;分钟不同则走下一条)。
- `MM-DD` == 今日但 HHmm ≠ 当前真实分钟 → 报错:这是今天另一个任务的目录名(可能是错峰顺延产生的),不是合法 slug 输入。

误伤分析:纯 slug 以两个合法数字组开头(如 `12-30-config`)会被误判——此为现有 guard 既有行为,不扩大;新增 HHmm 可选组只影响"三段数字前缀"形态,实际就是目录名粘贴。

实施陷阱(必须注意):
- **捕获组序号变化**:新正则 group(1)=MM、group(2)=DD、group(3)=HHmm(可空)、group(4)=body。现有代码两处用 `m.group(3)` 作为 body(剥离赋值与报错提示 `Pass only the slug body, e.g. --slug {m.group(3)}`),改造后必须改用 group(4),否则剥离结果与提示文本错位。
- **回溯边界**:`--slug 09-22-1435`(前缀无 body)时,HHmm 组因 `(.+)` 无剩余而回溯跳过,落入"当日无 HHmm"分支剥离为 body="1435",产生 `09-22-<当前HHmm>-1435` 目录——无害,与旧代码对 `09-22`(不匹配、原样保留)同属极端输入,不做特殊处理。
- **HHmm 合法性**:存在 HHmm 组但小时>23 或分钟>59(如 `09-22-2461-foo`)→ 不视为目录名粘贴,按普通 slug 放行(不剥离不报错)。

### 3. 帮助文本与文档

- `task.py:485` `--slug` help:`MM-DD date prefix` → `MM-DD-HHmm date prefix`。
- `.trellis/workflow.md:42`(`{MM-DD-name}`)与 `:386`(前缀说明,现行文本"Do **not** include the `MM-DD-` date prefix")更新为 `MM-DD-HHmm`。
- `.opencode/skills/trellis-brainstorm/SKILL.md:42` 更新;实施时全模板 grep `MM-DD` 核查剩余表述(`YYYY-MM-DD` 日期占位、session-insight 的 `--since/--until`、归档 `archive/<YYYY-MM>` 不属于目录前缀格式,不改)。已核实模板内 `.claude/skills`、`.agents/skills` 无 brainstorm 副本、trellis-meta references 无 MM-DD 前缀表述。
- `TEMPLATE-CONTENTS.md`(模板内、仅供 Forge 维护者、不安装到下游):按其测试文件行惯例为新测试补一行(标注 1.3 新增)。分支先例:功能任务 7f01ce2 曾同步该文件。

### 3a. 既有测试影响面(已核实)

- 无任何测试引用 `generate_task_date_prefix` 或 `MM-DD`;`test_planning_gate.py` 仅从 task_store 导入 `_default_prd_content`,不受影响。
- 多个契约测试读取模板 `workflow.md`,但断言目标是 review 等级集合、workflow-state tag 块、small-patch 文案,与本任务改动段落不重叠。
- 基线:模板套件 212 tests OK、本项目套件 154 tests OK(2026-09-22 规划自审时实测)。

### 4. `task.json`

`createdAt` 保持 `%Y-%m-%d`。不新增字段:时间信息已由目录名承载,list/排序逻辑不读 createdAt。

### 5. 排序/归档/解析兼容性(已逐项取证,不修改)

- `common/tasks.py::iter_active_tasks` 按目录名排序 → 新前缀下同日即创建序;旧格式存量任务(字母开头 slug)同日混排时排在新格式(HHmm 数字)之后,已接受。
- `execution_plan.py::resolve_task_dir` 按完整目录名/相对路径精确匹配(bare-slug 回退只查 `tasks/<raw>` 与 `archive/*/<raw>`,不做后缀匹配),前缀格式无关。
- `_find_archived_task_by_dir_name` 按完整目录名匹配,前缀无关。
- `task_utils.py::archive_task_dir` 归档月份目录取 `datetime.now().strftime("%Y-%m")`(归档时刻,不解析目录名前缀),目录名原样移动 → 兼容。
- `task_utils.py::find_task_by_name` 精确 + 后缀匹配(`endswith(f"-{task_name}")`),bare slug 可命中 `MM-DD-HHmm-slug` → 兼容;slug 互为后缀的歧义为既有行为,不变。
- `.opencode/` JS(plugins/lib)与 `.claude/hooks`、`.codex/hooks` Python 均无日期前缀解析(全量 grep `\d{2}`/date-prefix 无命中);非 py/md 文件仅 `.codex/agents/trellis-research.toml` 的 `YYYY-MM-DD` 日期占位,与前缀无关。
- 跨年:MM-DD 不含年份,同名冲突由现有 `task_dir.exists()` / 归档检查兜底,行为不变。

## 测试设计(新增 `templates/.../scripts/tests/test_task_dir_time_prefix.py`)

沿用 `test_write_json_lf.py` 的 sys.path 注入模式与 `test_execution_plan.py` 的 TemporaryDirectory 假仓库根模式:

1. 前缀格式:`generate_task_date_prefix()` 匹配 `^\d{2}-\d{2}-\d{4}$` 且与 `datetime.now()` 的 `%m-%d-%H%M` 一致(容忍跨分钟:两次采样断言其一)。
2. guard 行为:guard 逻辑保持 inline 不提取;测试直接驱动 `task_store.cmd_create(args)`(已核实签名:仅收 args,内部 `get_repo_root()` 定位仓库根)。临时 TemporaryDirectory 假仓库根,`unittest.mock.patch` 固定 `task_store` 命名空间内的 `get_repo_root`(返回临时根)、`run_git`(返回 `(0, "main\n", "")`)、`resolve_default_branch`(返回 `"main"`)、`generate_task_date_prefix`(直接返回固定前缀,避免 patch datetime 连带面);args 显式给 `assignee` 与 `no_start=True`,免除 developer 脚手架与会话激活,即使测试进程带 `TRELLIS_CONTEXT_ID` 也密闭;临时根无 config/平台目录 → `is_monorepo`、jsonl 种子路径自然短路。覆盖 guard 四分支:当日完整前缀(HHmm == 固定 base)→ 剥离 + 警告 + 目录名正确;当日旧格式 `MM-DD-slug` → 剥离 + 警告;非当日 `01-05-slug` → 返回码 1、不创建目录;非法 HHmm(`09-22-2461-foo`)→ 按普通 slug 放行不剥离。createdAt 用格式断言不冻结日期。
3. 错峰分配(`_allocate_task_prefix` 及 create 集成):固定 base 前缀下连续 create 3 个任务 → 前缀依次 base、base+1、base+2;预置占用目录(手工 mkdir `base+1-slug`)→ 新任务跳到 base+2;base `09-22-2359` 第二次 create → 前缀 `09-23-0000`(跨日);防御上限与 exists 兜底分支:patch `_allocate_task_prefix` 返回已占用前缀 → 触发 exists 警告路径(该分支错峰后近乎不可达,保留为防御)。
4. 排序契约:上述连续 create 后 `sorted(tasks_dir.iterdir())` 顺序 == 创建顺序(即父任务 children 挂接顺序)。

## Tradeoffs

- 目录名变长(+5 字符):换取零状态、自解释的时间排序。
- 本项目与模板格式分叉(本项目仍 MM-DD):用户明确决定;分叉只影响目录名形态,两侧代码各自独立、互不 import。
- 错峰语义(方案 B 代价,用户已接受):顺延后的目录名分钟可超前真实时间,目录名成为"排序记号"而非精确时钟;真实创建日期以 `task.json.createdAt` 为准。同分钟同 slug 重复 create 由"exists 警告复用目录"变为"顺延创建新任务"——与 create 语义一致,归档重复仍被 archived 检查拦截。
- 跨年边界:MM-DD 无年份,1 月任务(`01-xx`)会排在活跃目录里 12 月任务(`12-xx`)之前——现状 MM-DD 已如此,本任务不改变也不修复(活跃任务通常短期内归档);如需根治属于另立任务的范围。

## Rollback

改动全部为模板文件的文本级修改,`git checkout -- templates/` 即可整体回滚;无数据迁移、无本项目状态变更。
