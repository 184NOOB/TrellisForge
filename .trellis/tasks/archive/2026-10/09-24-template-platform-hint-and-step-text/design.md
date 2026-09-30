# 模板 Step detail 平台提示串与 task.py 步骤文案修复：技术设计

## 1. 范围与边界

- 功能写入只落在 `templates/embedded-c-overlay/`：
  - `.claude/hooks/session-start.py`（Step detail 提示串补 `--platform claude`，一行字面量）
  - `.opencode/lib/session-utils.js`（Step detail 提示串补 `--platform opencode`，一行字面量）
  - `.trellis/scripts/task.py`（jsonl 为空时的求助命令 `--step 1` → `--step 1.1`，一行字面量）
  - `.trellis/scripts/tests/test_step_detail_platform_hints.py`（新增防漂移断言）
  - `TEMPLATE-CONTENTS.md`（按既有表格行格式登记新测试文件一行，标注 1.3 新增）
- 只读、禁止写入：模板 `.codex/hooks/session-start.py`（09-21 已交付 `--platform codex`，不得回退或重构）、模板 `workflow.md` / `workflow_phase.py` / `io.py` / `git_context.py`、根目录 `.trellis/`（唯一例外：Phase 3.3 的 R5 spec 条目）、`.claude/`、`.codex/`、`.opencode/`、`.agents/`、`VERSION`、`history/`、manifest、结构迁移链、README、接入指南。
- 根目录允许写入：本任务目录；Phase 3.3 仅改根 `.trellis/spec/main/tooling/python.md` 的「送达入口约定」条目（现 88 行），扩为三平台口径。
- 并行窗口与用户脏改动：开工前拍 `git status` 快照，快照内脏文件一律不得触碰或回滚。

## 2. 送达链路与两处根因

```text
workflow.md
  └── ### Loading Step Detail (Phase Index 内, 359-370)
        已含三平台 --platform 示例（09-21 交付，本任务不改）

SessionStart 紧凑上下文（Phase Index，不过滤）
  ├── .codex/hooks/session-start.py:_build_workflow_toc
  │     Step detail 提示串已带 --platform codex          ← 09-21 已修
  ├── .claude/hooks/session-start.py:_build_workflow_overview
  │     Step detail 提示串无 --platform                  ← 根因 A
  └── .opencode/lib/session-utils.js:buildSessionContext
        Step detail 提示串无 --platform                  ← 根因 A

get_context.py --mode phase --step <id> [--platform ...]
  └── git_context.py:92  仅当传了 --platform 才 filter_platform
        照提示串执行 → 未过滤（三平台块混排）
        照命令文档执行 → 已过滤（claude / opencode 命令文档已传旗标）

task.py 拒绝 init-context 时的求助命令
  └── --mode phase --step 1                              ← 根因 B
        get_step 不解析裸主版本号，CLI exit 2（09-21 已锁死）
```

修复后：三平台 SessionStart 提示串、命令文档、Loading Step Detail 示例都把模型送到同一条「带 `--platform` 的步骤上下文」路径；`task.py` 求助命令指向可解析的 `1.1`。

## 3. 合同设计

### 3.1 三平台 Step detail 提示串（R1）

内容锚点（行号漂移时用这句唯一字符串重定位）：

`Full guide: .trellis/workflow.md. Step detail:`

目标字面量（反引号内命令，其余结构不变）：

| 文件 | 宿主函数 | `--platform` |
| --- | --- | --- |
| `.claude/hooks/session-start.py` | `_build_workflow_overview` | `claude` |
| `.codex/hooks/session-start.py` | `_build_workflow_toc` | `codex`（只读，不回退） |
| `.opencode/lib/session-utils.js` | `buildSessionContext` | `opencode` |

- 只改字符串字面量。宿主函数、注入流程、开关判断、Phase Index 抽取零逻辑 diff。
- 平台名与命令文档口径一致：Claude 用 `claude`（模板 `_platform_matches` 的 `claude ↔ claude-code / Claude Code` 家族别名已由 09-21 交付，`claude` 能渲染 `[Claude Code]` 块）、OpenCode 用 `opencode`、Codex 用 `codex`。
- `collectOpenCodeTemplates` 是上游 npm 包 `@mindfoldhq/trellis` 的函数，不存在于模板源码，与本任务三个文件无关。
- 不改不带 `--step` 的 Phase Index 调用（`.claude/commands/trellis/continue.md`、`.opencode/commands/trellis/{start,continue}.md`）：平台过滤对 Phase Index 无意义，SessionStart 本就不过滤。

### 3.2 `task.py` 求助文案（R2）

- 位置：模板 `.trellis/scripts/task.py` 拒绝已删除的 `init-context` 时，stderr 打印的求助命令（内容锚点 `See .trellis/workflow.md planning artifact guidance or run:`）。
- 改 `--step 1` 为 `--step 1.1`。不改其余文案、stderr 流向、退出码 2、任何其他 `task.py` 行为。
- 选 `1.1` 而非退回 `--mode phase`：该提示出现在「jsonl 为空、需要规划指引」语境，语义上要步骤级详情；`1.1` 是 Phase 1 第一个实质步骤（Requirement exploration and Grill Me），与模板 `workflow.md` Loading Step Detail 既有示例一致。
- `1.1` 必须能被模板 `get_step("1.1")` 解析为非空，真实 CLI `--mode phase --step 1.1` 在模板根退出码 0。裸 `--step 1` 继续由 `test_bare_major_numbers_stay_unresolved` 锁死为 exit 2。

### 3.3 防漂移断言（R3）

新文件：`templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py`。

路径与写法沿用 09-21 合约测试（`python.md` Tests Required）：

- `REPO_ROOT = Path(__file__).resolve().parents[3]`
- `SCRIPTS_DIR = Path(__file__).resolve().parents[1]`
- 子进程 `[sys.executable, "-B", ...]`，`cwd=str(REPO_ROOT)`，`env` 补 `PYTHONIOENCODING=utf-8`，`encoding="utf-8", errors="replace"`，固定 `timeout`
- 不得硬编码 `templates/embedded-c-overlay`
- 不得真实 spawn / wait agent

四组断言：

1. **三份提示串旗标与互不串平台**  
   各自含 `--mode phase --step <X.Y> --platform <claude|codex|opencode>`，且保留 `Full guide: .trellis/workflow.md` 与 `Step detail:` 结构。串平台按整文件级断言：Claude 文件不含 `--platform codex` / `--platform opencode`，其余同理。当前全文除待改提示串外，`.claude` hook 与 `session-utils.js` 零其他 `--platform`；`.codex` hook 仅提示串一处。
2. **`task.py` 每个 `--step <id>` 提示可解析**  
   源码中出现的每个 `--step <id>` 都能被模板 `get_step(<id>)` 解析为非空。用进程内导入 `common.workflow_phase.get_step` 或真实 CLI 子进程，二者择一并在测试里写明。另用边界正则 `--step 1(?![.\d])` 断言不再出现裸 `--step 1`（朴素子串检查会被 `--step 1.1` 恒真误报）。当前模板 `task.py` 全文 `--step` 仅此一处。
3. **Loading Step Detail 三平台示例**  
   模板 `workflow.md` 的 `### Loading Step Detail` 仍含 `--platform claude` / `codex` / `opencode`。这是刻意冗余的第二道锁（第一道是 `test_codex_native_wait_contract.py` 的 `test_loading_step_detail_names_all_three_platforms`），避免 09-21 合约测试被重构时丢锁。
4. **登记与形状**  
   提示串结构不断言「只有旗标」；`TEMPLATE-CONTENTS.md` 登记由本任务实施步骤完成，本测试可不重复钉死登记行（09-21 的 `test_template_contents_registers_new_tests` 只钉自己的两个文件，本任务按表格格式新增一行即可，不必改那条断言）。

独立成文件，不塞进 `test_opencode_platform_contract.py`：断言跨 Claude / Codex / OpenCode 与 `task.py`，超出「OpenCode 平台合同」职责。

`TEMPLATE-CONTENTS.md` 在既有 1.3 测试行之后追加一行，安装策略与相邻 1.3 测试文件一致（覆盖后新增）。

### 3.4 Spec 送达入口（R5，Phase 3.3）

根 `.trellis/spec/main/tooling/python.md` 现 88 行只要求 Codex hook 提示串带 `--platform codex`。交付后事实变为三平台各自带正确旗标，该条目扩为：

- Loading Step Detail 三行平台中立示例（已有，保持）
- `.claude/hooks/session-start.py` 带 `--platform claude`
- `.codex/hooks/session-start.py` 带 `--platform codex`
- `.opencode/lib/session-utils.js` 带 `--platform opencode`

只改该条目相关文字。70 行「不得把模板行为写成根目录已经具备的事实」保持原样。本任务 spec 文字只描述模板合同。

## 4. 兼容性、风险与回滚

- 兼容：SessionStart 仍注入 Phase Index，不做平台过滤；提示串只多一个旗标，不改变抽取范围。命令文档路径行为不变。`get_step` / `filter_platform` / 别名矩阵零改动。
- 行为变化（有意）：下游 Claude / OpenCode 主会话若照 SessionStart 提示串执行 `--mode phase --step <X.Y>`，将从「未过滤混排」变为「本平台过滤后输出」，与各自命令文档对齐。
- 风险 1：串平台断言按整文件级——若日后同文件新增合法的其他 `--platform` 用法会红。当前实测安全；若未来需要，再收窄到提示串行。
- 风险 2：`task.py` 的 `--step 1.1` 依赖 `#### 1.1` 标题存在。该标题是 workflow 固定步骤，被 `get_step` 合同覆盖。
- 风险 3：`tests/test_overlay_tools.py` 处于 1.3 活模板 vs 1.2 manifest 的结构性红基线。本任务改的 3 个已跟踪模板文件在漂移清单内；新测试文件与 `TEMPLATE-CONTENTS.md` 不在 1.2 manifest（151 项）中，不扩大漂移面。禁止为修绿触碰 manifest / history / VERSION。
- 风险 4：改 `session-utils.js` 后必须跑既有 Node harness；Node 不可用则报告 `not run`，不得记假 pass。
- 回滚：全部为字面量 / 新测试文件 / 一行登记。`git checkout` 对应模板路径即可；无运行时状态、无 manifest、无 canonical 影响。分批回滚点见 `implement.md`。

## 5. 验证命令

从仓库根运行。模板 CLI（`--mode phase`）必须在模板根执行，否则会误读仓库根 `workflow.md`。

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_step_detail_platform_hints.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_codex_native_wait_contract.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_write_json_lf.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s tests -p "test_overlay_tools.py"
python -m py_compile templates/embedded-c-overlay/.claude/hooks/session-start.py
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/task.py
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py
git diff --check
```

模板根（workdir = `templates/embedded-c-overlay`）手工复核：

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -B .trellis/scripts/get_context.py --mode phase --step 1.1
python -B .trellis/scripts/get_context.py --mode phase --step 1
```

前者退出码 0 且非空；后者退出码 2，stderr 含 `Step not found: 1`。

`tests/test_overlay_tools.py`：开工前记录失败集合（基线口径：48 例、26 失败），提交前再跑，失败集合必须完全一致。

构建 / 部署 / 硬件验证：`not applicable`（本仓库不产出固件或可执行产品）。
