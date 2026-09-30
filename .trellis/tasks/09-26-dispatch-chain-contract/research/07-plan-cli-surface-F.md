# Research: F — plan.py 子命令表面积（条目 6）

- **Query**: 现有子命令清单、argparse 结构、是否存在 dispatchable、新增只读子命令的文本合同同步清单
- **Scope**: internal
- **Date**: 2026-09-26

## 1. 现有子命令清单与 argparse 结构

文件：`templates/embedded-c-overlay/.trellis/scripts/plan.py`（共 175 行）。

- `build_parser()`：72-124 行。`--task` 双份声明（全局 85-89 行 + `task_parent` SUPPRESS 75-80 行，
  注释 73-74 行说明原因）；`sub = parser.add_subparsers(dest="subcommand", required=True)`（90 行）。
- 子命令注册（92-123 行）与 main() 分派（127-171 行）一一对应：

| 子命令 | 注册行 | 分派行 | 性质 |
|---|---|---|---|
| `template` | 92-93 | 132-134 | 只读（打印骨架；唯一不需要 --task 的命令） |
| `validate` | 94-95 | 138-139 | 写（批准计划） |
| `status` | 96-98（含 `--quiet`） | 140-145 | **只读**（print format_status；无计划时打印提示语并 return 0） |
| `start` | 99-101 | 146-147 | 写 |
| `record` | 102-110 | 148-152 | 写 |
| `done` | 111-113 | 153-154 | 写 |
| `block` | 114-117 | 155-156 | 写 |
| `revise` | 118-120 | 157-158 | 写 |
| `sequel` | 121-123 | 159-160 | 写 |

- 错误处理：PlanError → stderr + hint + return 1（163-167 行）；OSError/JSONDecodeError → return 1（168-170 行）。
- **`dispatchable` 不存在**：全模板（*.py/*.md/*.js/*.toml/*.json）grep `dispatchable` 实测 **0 命中**。
  同类只读命令仅 `status`（与 `template`）。

## 2. 命令清单在文本合同中的出现点（新增子命令需同步的正文）

| 位置 | 现有文本 | 说明 |
|---|---|---|
| `.trellis/scripts/common/execution_plan.py:2083-2084` | `Advance with: \`{cli} --task "<task-path>" <command>\` (validate/status/start/record/done/block/revise/sequel).` | protocol block base 段的命令枚举；无测试锁定该括号清单（tests grep 0 命中），但它是子代理看到的权威命令表 |
| `.trellis/workflow.md:246` | `advances only through plan.py start/record/done/block/revise` | in_progress 块内枚举（写路径） |
| `.trellis/workflow.md:274` | inline 块同款枚举 | |
| `.trellis/workflow.md:608` | `State advances only through plan.py (start / record / done / block / revise)` | Phase 2 gate |
| `.trellis/workflow.md:611` | `runs plan.py --task "<task-path>" status` | 轮间只读命令引用 |
| 四份 implement 代理定义 | claude md 99-102 / opencode md 112-115 / codex toml 33 / channel 卡 107-110：`block … revise … edit → validate` 枚举 | 写路径枚举 |
| `test_small_patch_and_sequel_contract.py:168-179` | `plan.py --help` 输出 assertIn `sequel` | 先例：新子命令可仿此加 `--help` 暴露断言 |

## 3. 新增只读子命令的完整同步清单（评估 E 形态二用）

**必改（代码）**：

1. `.trellis/scripts/plan.py`：92-123 行区域 `sub.add_parser("dispatchable", parents=[task_parent], help=...)`；131-162 行区域加分派分支。
2. `.trellis/scripts/common/execution_plan.py`：新 `cmd_dispatchable`（链推导构件见 `06-format-status-breadcrumb-E.md` §5）。
3. `.trellis/scripts/tests/test_execution_plan.py`（或新测试文件）：行为断言；若建新测试文件，按
   `TEMPLATE-CONTENTS.md:13-14` 行格式（`覆盖后新增（1.3 新增）`）登记，先例断言
   `test_codex_native_wait_contract.py:306-309`。

**文本合同（强烈建议同步）**：

4. `execution_plan.py:2083-2084` 命令枚举补 `dispatchable`。

**可选（取决于主会话/子会话谁使用该命令）**：

5. `.trellis/workflow.md`：611 行轮间判定（若主会话改跑 dispatchable）与/或 246 行 in_progress 块。
6. 四份 implement 代理定义各一句（若子代理需自跑）。

**无需改（实测确认）**：

- `.opencode/commands/trellis/*.md`、`.claude/commands/trellis/*.md`：grep `plan\.py` 0 命中（路由命令不含 plan.py 引用）。
- `.opencode/skills/trellis-check/SKILL.md:77`、`.trellis/agents/check.md:66`：只引用 status 语义，与新命令无关。
- `.trellis/spec/shared/`（5 个文件：hardware-contracts、index、repository-layout、trellis-maintenance、validation）：
  模板内 spec 无 plan.py 子命令枚举（trellis-maintenance.md 讲上游更新边界，不锁命令表）。
- 三平台 hook/plugin：不解析子命令名（inject 侧只调 `plan_protocol_block`/`plan_breadcrumb` 函数）。
- 仓库级 `tests/test_overlay_tools.py` / `history/embedded-c-overlay/versions/1.2` manifest：模板文件正文变化
  本来就处于 1.3 红基线（见 `01-baseline-regression.md`）；manifest/版本号更新按
  `.trellis/spec/main/tooling/templates-and-docs.md:18` 归发布收尾任务，不属于本功能子任务。

## Caveats

- `plan.py status --quiet`（98 行）已存在“compact summary”形态；若 dispatchable 只想输出链，可参照 `--quiet` 的实现位置（145 行 verbose 开关）。
- `template` 子命令不需要 --task（132-134 行在 resolve_task_dir 之前返回）；新只读命令需要 task 上下文，应放在 136 行 `resolve_task_dir` 之后分派。
