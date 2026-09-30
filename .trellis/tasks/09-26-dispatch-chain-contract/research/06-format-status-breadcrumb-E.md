# Research: E — format_status / compute_status / plan_breadcrumb 与“本轮链”推导（条目 5）

- **Query**: 三函数当前输出与调用方；status 输出逐行断言；depends_on 拓扑可复用代码；E 两形态成本差
- **Scope**: internal
- **Date**: 2026-09-26

路径相对 `templates/embedded-c-overlay/`，核心文件 `.trellis/scripts/common/execution_plan.py`（共 2254 行）。

## 1. compute_status（1832-1853 行）

**已有所需全部状态列表**，返回 dict 键：

| 键 | 行号 | 语义 |
|---|---|---|
| `revision` / `plan_status` | 1846-1847 | 计划修订号 / proposed-approved |
| `in_progress` | 1840-1842 | status == "in_progress" 的 id 列表 |
| `runnable` | 1834-1839 | pending 且所有 depends_on 均 completed；**`sorted(runnable)`（1849 行）字典序，不是拓扑序** |
| `blocked` | 1843 | status == "blocked" |
| `completed` | 1844 | status == "completed" |
| `total` | 1852 | 任务总数 |

## 2. format_status（1884-1962 行）当前输出行

按输出顺序（verbose=True 全量；verbose=False 只到第 8 行前）：

1. 1897-1899：`execution plan{ (live N)}: revision=R status=S tasks=C/T completed | audit OK (N events)`（或 `AUDIT DAMAGED at lines ...`）
2. 1900：`goal: <goal>`
3. 1902-1904：`frozen plans: plan 1: x/y completed, status=... (frozen, read-only) | ...`（仅 live>1）
4. 1910-1918：`DRIFT (mutations will be refused until repaired via revise): ...`（仅有漂移时）
5. 1919-1920：`in_progress: a, b`（仅非空）
6. 1921-1922：`next runnable: c, d`（仅非空）
7. 1923-1924：`blocked: e`（仅非空）
8. 1925-1959（verbose only）：每任务一行 `  [<status右对齐12>] <id>  (missing checks: ...; checks pending/failed: ...; missing final-report.md file; final-report.md not registered via record --artifact)`
9. 1960-1961：`ALL TASKS COMPLETED — proceed to Phase 2.2 quality check`（全完成时）

## 3. plan_breadcrumb（2034-2045 行）

- 有计划时返回 `<execution-plan>\n{format_status(task_dir, repo_root, verbose=False)}\n</execution-plan>`（2042-2043 行）；
  无计划返回空串（2040-2041）；任何异常返回 `state: unreadable — run plan.py status for details`（2044-2045）。
- **breadcrumb 用 verbose=False** → 若“本轮链”行加在 format_status 的 verbose 无关区（1919-1924 附近），
  会自动进入每轮面包屑（E 形态一的传导机制）；若只加在 verbose 区（1925 之后）则不会。

### plan_breadcrumb 调用方（三平台）

| 平台 | 位置 | 事件 |
|---|---|---|
| Claude | `.claude/hooks/inject-workflow-state.py:365-378`（376 行 import，378 行调用） | UserPromptSubmit（`.claude/settings.json:70-80`） |
| Codex | `.codex/hooks/inject-workflow-state.py:378-380` | UserPromptSubmit（`.codex/hooks.json:3-13`） |
| OpenCode 逐轮 | `.opencode/plugins/inject-workflow-state.js:121-130`（126 行调用）→ `planBreadcrumb`（`.opencode/lib/session-utils.js:577-581`，经 540-547 行 `PLAN_BREADCRUMB_PY` 子进程片段） | 插件 `chat.message` 每轮 |
| OpenCode SessionStart | `.opencode/lib/session-utils.js:680-687`（`buildSessionContext` 内 683 行调用） | session-start 插件一次性注入 |

## 4. 锁定 status 输出的测试（新增一行的破坏面）

`.trellis/scripts/tests/test_execution_plan.py` 全部为 assertIn/assertNotIn 子串断言，**没有逐行全等断言**：

| 行号 | 断言 | 对新增行的敏感性 |
|---|---|---|
| 792-793 | `format_status` 含 `DRIFT` | 无冲突 |
| 800-801 | 含 `missing final-report.md file` | 无冲突 |
| 931 | 审计损坏时 `format_status` 仍含 `discover` | 无冲突 |
| 976-978 | legacy 布局：含 `execution plan:`；**assertNotIn `frozen plans:`** | **新行文本不得包含 “frozen plans:” 子串** |
| 1107-1112 | sequel 后：含 `(live 2)`、`frozen plans:`、`plan 1: 3/3 completed`、`discover-x`；**assertNotIn `[   completed] discover`**（1111 行，锁 verbose 任务行的状态列宽格式） | **新行若模仿 `  [<status>] <id>` 12 字符右对齐格式且含 completed+discover 组合会撞 1111 行**；普通措辞行无冲突 |
| 980-988 / 1113-1116 | protocol block 断言（末尾拼接 format_status verbose 输出） | 新行会随 verbose 输出进入 protocol block；988 行 assertNotIn `Per phase loop` 只约束完成分支 |

其余套件对 status 文本无逐行断言（tests 目录 grep `next runnable|in_progress:` 仅命中 test_execution_plan.py 注释与上述行）。
OpenCode Node harness 只锁 `## Trellis execution plan protocol` 标题排序（test_opencode_platform_contract.py:342-348），不锁 status 行。

**结论（E 形态一）**：在 format_status 的 1919-1924 条件行区域追加一行（如 `dispatch chain: a → b → report`）
属**零断言冲突的纯新增**，只需避开 `frozen plans:` 字样与 verbose 任务行格式；且因 breadcrumb 用 verbose=False，
新行须放在 verbose 分支之外才能进面包屑。

## 5. “本轮链”拓扑推导可复用代码

- **没有现成的通用拓扑排序函数**（全文件无 topo/topological 命中）。可复用的最接近构件：
  1. `_find_cycle`（844-866 行）：三色 DFS 环检测，`visit(node, stack)` 结构可直接改造成后序拓扑输出；
  2. `validate_plan_shape` 内 report 传递闭包步行（816-829 行）：显式 stack 的可达性 DFS
     （从 report 的 depends_on 出发遍历全图），是“沿 depends_on 遍历”的现成范式；
  3. `compute_status` runnable 判定（1836-1839 行）：`all(by_id.get(d,{}).get("status")=="completed" ...)`。
- 推导“从 in_progress + runnable 出发沿 depends_on 正向可达的剩余链”需要**反向邻接**
  （谁依赖我），现成范式在 805-807 行：`dependents = sorted(tid for tid,t in by_id.items() if rid in (t.get("depends_on") or []))`。
- validate 已保证无环（cmd_validate 调用 `_find_cycle`，见 877 行起）与 report 终端性（798-835 行），
  因此链推导可假设 DAG 成立。

## 6. E 两形态成本差（事实清单，不替用户选择）

### 形态一：format_status 加一行（由 plan_breadcrumb 自动带出）

需同步改动的文件（实测依赖链）：

| # | 文件 | 原因 |
|---|---|---|
| 1 | `.trellis/scripts/common/execution_plan.py` | format_status 加行（+链推导辅助函数） |
| 2 | `.trellis/scripts/tests/test_execution_plan.py` | 为新行加断言（既有断言零破坏，见 §4） |

自动传导（无需改代码）：Claude/Codex 每轮面包屑（inject-workflow-state.py）、OpenCode 逐轮与 SessionStart
（planBreadcrumb/plan_breadcrumb bridge）、`plan.py status` CLI（plan.py:145 直接 print format_status）、
plan_protocol_block 末尾状态区（execution_plan.py:2145、2173）——**三平台 hook/plugin 均零改动**。
文档面：workflow.md 246 行有 “The `<execution-plan>` breadcrumb is display-only” 一句，新行天然被覆盖，无需改。
合计：**2 个文件**（1 实现 + 1 测试），无文本合同联动。

### 形态二：新增只读子命令 `plan.py dispatchable`

需同步改动的文件：

| # | 文件 | 原因 |
|---|---|---|
| 1 | `.trellis/scripts/plan.py` | build_parser 加 `sub.add_parser("dispatchable", ...)`（90-124 行区域）+ main() 分派（131-162 行区域） |
| 2 | `.trellis/scripts/common/execution_plan.py` | 新 cmd 函数（链推导逻辑同形态一） |
| 3 | `.trellis/scripts/tests/test_execution_plan.py` | 新命令行为断言 |
| 4 | `.trellis/scripts/common/execution_plan.py:2083-2084` | protocol block 命令清单 `(validate/status/start/record/done/block/revise/sequel)` 需补 `dispatchable`（否则子代理看不到该命令；无测试锁这个括号清单——tests grep `revise/sequel|validate/status/start` 0 命中——但文本一致性要求补） |
| 5 | `.trellis/workflow.md` | 611 行“Between implement rounds … runs plan.py status”与 246 行 in_progress 块如需引用新命令则要改；若主会话继续用 status 也可不改（改动可选） |
| 6 | 四份 implement 代理定义（claude md / opencode md / codex toml / channel 卡） | 若要求子代理自跑 `dispatchable` 则各需一句；若仅主会话用则不改（改动可选） |
| 7 | `TEMPLATE-CONTENTS.md` | 无独立行需求（`.trellis/scripts/` 已有总行，第 9 行）；仅当新增测试文件时按 13-14 行格式登记 |
| 8 | 命令文档 `.opencode/commands/trellis/*.md`、`.claude/commands/trellis/*.md` | **实测无 plan.py 引用**（两目录 grep `plan\.py` 0 命中），无需改 |
| 9 | `.opencode/skills/trellis-check/SKILL.md:77`、`.trellis/agents/check.md:66` | 仅引用 status 语义，check 侧无需感知新命令（不改） |

合计：**必改 3 个文件**（plan.py、execution_plan.py、测试）+ **强烈建议 1 处文本**（protocol block 2084 行命令清单）
+ **可选 5-9 处文档**（workflow.md、四份代理定义），并且新命令名会进入下游主会话的操作面
（相对形态一多出跨文件文本同步与文档一致性维护）。

两形态共同点：链推导逻辑本身相同（§5）；都不触碰 A/B 的 parity 锁；都不受
`test_small_patch_and_sequel_contract.py:168-179`（`plan.py --help` 含 `sequel`）影响——该断言只查子串，新增子命令不破坏。

## Caveats

- `sorted(runnable)`（1849 行）意味着现有 “next runnable” 行是字典序；若新“链”行想表达执行顺序，需要独立推导，不能复用 runnable 列表顺序。
- OpenCode `runPythonFragment` 超时 8000ms（session-utils.js:560）；链推导为 O(V+E) 纯内存计算，无超时风险。
- 形态一新行若希望**不进** SessionStart 而只进逐轮面包屑：无法区分——两处共用 `planBreadcrumb`（session-utils.js:683 与 inject-workflow-state.js:126 调同一函数）。
