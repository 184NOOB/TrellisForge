# 模板 Step detail 平台提示串与 task.py 步骤文案修复：实施计划

## 实施前条件

- [ ] 已读取 `prd.md`、`design.md`、本文件、`implement.jsonl`、`check.jsonl` 及 jsonl 中列出的 Spec / 09-21 归档。
- [ ] 写入白名单只有 `design.md` §1 列出的模板路径 + 任务目录；Phase 3.3 才改根 `python.md` 送达入口条目。
- [ ] `git status --short` 已拍快照。快照内脏文件与并行窗口任务一律不得触碰或回滚。
- [ ] 已按 `workflow.md` Guardrail 用 `plan.py` 创建并批准 live `execution-plan.json`；本文件批次 1–5 映射为 plan 阶段。Phase 2 源码改动只在 plan 批准后发生，状态推进只走 `plan.py`。
- [ ] 开工前记录 `tests/test_overlay_tools.py` 失败集合（基线口径 48 例 / 26 失败），供 AC5 对照。

## 实施批次

### 1. 防漂移测试先行

- [ ] 新增 `templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py`，按 `design.md` §3.3 写四组断言。
- [ ] 路径：`REPO_ROOT = Path(__file__).resolve().parents[3]`，`SCRIPTS_DIR = Path(__file__).resolve().parents[1]`；子进程 `cwd=str(REPO_ROOT)`，`PYTHONIOENCODING=utf-8`，`encoding="utf-8", errors="replace"`，固定 `timeout`。不得硬编码 `templates/embedded-c-overlay`，不得真实 spawn / wait agent。
- [ ] `task.py` 的 `--step <id>` 解析用进程内 `get_step` 或真实 CLI，并在测试里写明选择；裸 `--step 1` 用边界正则 `--step 1(?![.\d])`。
- [ ] 先跑该测试，确认当前红基线：Claude / OpenCode 提示串缺 `--platform`，`task.py` 仍含裸 `--step 1`。把红结果记入任务目录（不必新建 research 文件以外的产品代码）。

### 2. 三平台提示串字面量

- [ ] 模板 `.claude/hooks/session-start.py` 的 Step detail 提示串补 `--platform claude`。内容锚点：`Full guide: .trellis/workflow.md. Step detail:`。只改该字符串，不改 `_build_workflow_overview` 逻辑。
- [ ] 模板 `.opencode/lib/session-utils.js` 的同句补 `--platform opencode`。只改该字符串，不改 `buildSessionContext` 逻辑。
- [ ] 不改 `.codex/hooks/session-start.py`（已含 `--platform codex`）。
- [ ] `git diff` 复核：两处都是纯字符串 diff，无函数签名或控制流变化。

### 3. `task.py` 求助命令

- [ ] 模板 `.trellis/scripts/task.py` 将 `--step 1` 改为 `--step 1.1`。内容锚点：`See .trellis/workflow.md planning artifact guidance or run:`。
- [ ] 不改其余 stderr 文案、流向、退出码 2。
- [ ] 模板根复核：`--mode phase --step 1.1` 退出码 0；`--mode phase --step 1` 仍退出码 2。

### 4. 登记新测试文件

- [ ] 在模板 `TEMPLATE-CONTENTS.md` 既有 1.3 测试行之后，按表格三列格式追加 `test_step_detail_platform_hints.py` 一行（覆盖后新增，1.3 新增），说明覆盖三平台 Step detail 提示串与 `task.py` `--step` 可解析性。

### 5. 全量验证与边界审计

- [ ] 新测试与 09-21 合约测试、模板全量、根套件、安装器套件：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_step_detail_platform_hints.py"
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_codex_native_wait_contract.py"
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_write_json_lf.py"
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  python -B -m unittest discover -s tests -p "test_overlay_tools.py"
  ```

- [ ] 模板全量应 ≥ 212 + 新增用例，且全绿；`test_codex_native_wait_contract.py` 23 例与 `test_write_json_lf.py` 1 例仍绿；根套件 154 例全绿。
- [ ] `test_overlay_tools.py` 失败集合与开工前快照完全一致，无新增红项。
- [ ] 语法检查：

  ```powershell
  python -m py_compile templates/embedded-c-overlay/.claude/hooks/session-start.py
  python -m py_compile templates/embedded-c-overlay/.trellis/scripts/task.py
  python -m py_compile templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py
  ```

- [ ] Node harness：随模板全量跑 `test_opencode_platform_contract.py`。Node 不可用则报告 `not run` 及原因，不得记假 pass。
- [ ] 模板根手工复核 `--step 1.1` / `--step 1`（见 `design.md` §5）。
- [ ] `git diff --check` 无输出。
- [ ] 边界：功能 diff 只在 `templates/embedded-c-overlay/`（外加任务目录）；根 `.trellis/`、`.claude/`、`.codex/`、`.opencode/`、`.agents/`、`tools/`、`docs/`、`README.md`、`VERSION`、`history/` 零功能 diff（R5 spec 条目留到 Phase 3.3）。用户脏改动与并行窗口任务未被触碰。
- [ ] 构建、部署、硬件验证报告 `not applicable`。

### 6. 审查（reinforced）

- [ ] 按 `reinforced` 派发独立 `trellis-check`，范围为 affected-scope：本任务完整 diff、三份提示串字面量、`task.py` 文案、新测试四组断言、`TEMPLATE-CONTENTS.md` 登记、三套件回归与 AC1–AC6。
- [ ] 每轮 blocking 修复后派发全新独立 `trellis-check` 完整复审，直到零 blocking。不得用主会话自审或只重跑失败项替代。
- [ ] 主会话在轮次之间只负责修复与重跑受影响验证命令。
- [ ] 零 blocking 后不追加 commit-ready 独立复审（`reinforced` 不要求）。

### 7. Spec 更新（Phase 3.3，对应 R5 / AC7）

- [ ] 根 `.trellis/spec/main/tooling/python.md`「送达入口约定」条目扩为三平台提示串口径（Claude / Codex / OpenCode）。只改该条目相关文字；70 行根未同步声明保持原样。
- [ ] 该文件其余部分零 diff。

## 回滚点

- 批次 1 失败：删除新测试文件，保留红基线记录。
- 批次 2 失败：还原两份提示串字面量；Codex hook 本就未改。
- 批次 3 失败：还原 `task.py` 一行；保留批次 2。
- 批次 4 失败：还原 `TEMPLATE-CONTENTS.md` 新增行。
- 批次 7 失败：还原 `python.md` 该条目。
- 全部为字面量 / 新文件 / 一行登记，`git checkout` 对应路径即可；无 manifest、canonical 或运行时状态影响。

## 发布边界

- 不更新 `VERSION`、canonical、manifest、结构链、README、接入指南（固定收尾子任务负责）。
- 不修改根目录自用 Trellis 实现（R5 spec 条目除外）。
- 不新增 Hook / 插件通道；不改模板 `workflow.md` / 提取器 / Codex hook。
