# 模板 Step detail 平台提示串与 task.py 步骤文案修复：终态验收报告

- 任务：`09-24-template-platform-hint-and-step-text`（父任务 `09-17-trellisforge-1-3-upgrade`）
- 执行计划：`execution-plan.json` revision 1，6 个 phase（`discover` / `tests-red` / `hint-strings` / `register-test` / `full-validation` / `report`）
- 审查等级：`reinforced`（独立审查与 Phase 3.3 spec 更新由主会话后续执行，不在本实施轮次内）
- 日期：2026-10-01

## 任务目标与最终结论

让发布模板三平台的 SessionStart "Step detail" 提示串各自带上正确 `--platform`（Claude / OpenCode 此前缺失），修掉模板 `task.py` 打印的必然失败的 `--step 1` 求助命令（改为可解析的 `--step 1.1`），并新增防漂移测试锁定三份提示串、`task.py` 步骤 id 与 Loading Step Detail 三平台示例。**最终结论：AC1–AC7 全部通过；三处产品改动均为纯字符串 diff；模板全量 231 例、根套件 154 例全绿；09-21 合约测试 23+1 例全绿；安装器套件失败集合与开工前完全一致（48 例 / 26 失败 / set-diff 0）；`git diff --check` 无输出；功能改动只在模板白名单与 R5 的 `python.md` 条目内。reinforced 独立审查 round 1 / round 2 均为 0 blocking。**

## 交付清单

| 文件 | 说明 |
| --- | --- |
| `templates/embedded-c-overlay/.claude/hooks/session-start.py` | 第 731 行提示串补 `--platform claude`（纯字符串 diff，`_build_workflow_overview` 零逻辑改动） |
| `templates/embedded-c-overlay/.opencode/lib/session-utils.js` | 第 625 行提示串补 `--platform opencode`（纯字符串 diff，`buildSessionContext` 零逻辑改动） |
| `templates/embedded-c-overlay/.trellis/scripts/task.py` | 第 467 行求助命令 `--step 1` → `--step 1.1`（纯字符串 diff，stderr 流向与退出码 2 不变） |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_step_detail_platform_hints.py` | 新增：三份提示串旗标与互不串平台、`task.py` 每个 `--step` 可被 `get_step` 解析 + 裸 `--step 1` 边界正则 + 真实 CLI `--step 1.1`、Loading Step Detail 第二道锁（7 用例） |
| `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` | 1.3 测试行后登记新测试文件一行（覆盖后新增） |
| `.trellis/tasks/09-24-template-platform-hint-and-step-text/research/red-baseline.log` | 测试先行红基线（7 例 / 4 预期失败） |
| `.trellis/spec/main/tooling/python.md` | Phase 3.3：送达入口约定扩为三平台提示串；Tests Required 增补 `test_step_detail_platform_hints.py`；70 行根未同步声明保持原样 |

未触碰：模板 `.codex/hooks/session-start.py`（09-21 已交付 `--platform codex`，未回退）、模板 `workflow.md` / `workflow_phase.py` / `io.py` / `git_context.py`、根 `.claude/` / `.codex/` / `.opencode/` / `.agents/`、`VERSION` / `history/` / manifest / 结构链 / README / 接入指南。根 `.trellis/` 仅改 `python.md` 上述条目。用户既有脏改动 `.opencode/package.json` 与并行窗口任务均未触碰。

## 逐阶段结果

| Phase | 内容 | 声明检查（真实退出码） |
| --- | --- | --- |
| `discover` | 重锚三份提示串与 `task.py` 求助命令；拍 `git status` 快照（脏文件：`.opencode/package.json` + 本任务规划文件）；记录安装器红基线 48 例 / 26 失败 | 只读 phase，无声明检查（`no_check_reason`） |
| `tests-red` | 新增 `test_step_detail_platform_hints.py`；跑红确认 4 个预期失败（Claude/OpenCode 缺旗标、裸 `--step 1`、`get_step("1")` 空） | `py-compile-new-test`=0；`new-test-red-baseline`=0（artifact `research/red-baseline.log`） |
| `hint-strings` | 三处字符串字面量修改；`git diff` 复核为纯字符串 | `new-test-green`=0（7/7 OK）；`cli-step-1-1`=0（模板根 `--step 1.1` exit 0 非空；裸 `--step 1` 仍 exit 2 + `Step not found: 1`）；`py-compile-touched`=0 |
| `register-test` | `TEMPLATE-CONTENTS.md` 追加新测试行（`覆盖后新增（1.3 新增）`，格式与相邻 1.3 行一致） | `contents-registered`=0 |
| `full-validation` | 三套件回归 + 边界审计 | `unittest-template-all`=0（Ran 231 OK）；`unittest-root-all`=0（Ran 154 OK）；`unittest-overlay-same-red`=0（失败集合 set-diff 0）；`git-diff-check`=0（无输出） |
| `report` | 本报告 | `report-written`（见下方记录） |

## AC 验收结论

- [x] **AC1 pass**：三份提示串各自含正确旗标 —— `.claude/hooks/session-start.py` 含 `--mode phase --step <X.Y> --platform claude`、`.codex/hooks/session-start.py` 含 `... --platform codex`（未回退，全文唯一一处）、`.opencode/lib/session-utils.js` 含 `... --platform opencode`；三者互不串平台（整文件级断言，实测三文件除目标提示串外零其他 `--platform`）。证据：`TestStepDetailPlatformHints` 3/3 与 `test_codex_native_wait_contract.py::test_codex_session_start_hint_passes_platform`。
- [x] **AC2 pass**：三处改动均为纯字符串 diff（`git diff` 各 1 行增删，无函数签名 / 控制流变化；`_build_workflow_overview`、`buildSessionContext` 逻辑零 diff）。证据：`git diff --stat`（4 个模板文件 5 insertions / 4 deletions，含 TEMPLATE-CONTENTS 1 行）。
- [x] **AC3 pass**：模板 `task.py` 求助提示为 `--step 1.1`，边界正则 `--step 1(?![.\d])` 确认无裸 `--step 1`（全文 `--step` 仅此一处）；`get_step("1.1")` 非空（实测 2002 字符）；真实 CLI `--mode phase --step 1.1` 在模板根退出码 0 且非空。证据：`TestTaskPyStepHints` 3/3、`cli-step-1-1` 检查。
- [x] **AC4 pass**：新增 `test_step_detail_platform_hints.py` 覆盖 R3 四组断言并全绿（7/7）；`TEMPLATE-CONTENTS.md` 已按既有表格格式登记一行。证据：`new-test-green`=0、`contents-registered`=0。
- [x] **AC5 pass**：模板全量 231 例全绿（≥ 212 基线 + 7 新增；含 OpenCode Node harness，Node 22.16.0 可用，`test_opencode_platform_contract.py` 13/13 OK 无 skip）；`test_codex_native_wait_contract.py` 23 例与 `test_write_json_lf.py` 1 例仍绿；根套件 154 例全绿；`tests/test_overlay_tools.py` 48 例 / 26 失败与开工前失败集合完全一致（`Compare-Object` set-diff 0，原始 exit 1 为 1.3 漂移结构性红基线）；改动的 Python 文件 `py_compile` 通过。证据：`full-validation` 四项检查 + 定向复跑记录。
- [x] **AC6 pass**：`git diff --check` 无输出（output-len 0）；功能改动只在 `templates/embedded-c-overlay/`（4 个已跟踪文件 + 1 个新增测试文件）与任务目录；根 `.trellis/spec/main/tooling/python.md` 零 diff（R5 留 Phase 3.3）；`.opencode/package.json` 为开工前既有脏改动，未触碰或回滚。证据：`git status --short` / `git diff --stat` 边界审计。
- [x] **AC7 pass（Phase 3.3）**：根 `.trellis/spec/main/tooling/python.md`「送达入口约定」条目已扩为三平台提示串口径（Claude / Codex / OpenCode）；Tests Required 增补 `test_step_detail_platform_hints.py`（含 patch `common.workflow_phase.get_repo_root`）；70 行根未同步声明保持原样。

## 检查分类报告

| 类别 | 结果 |
| --- | --- |
| 静态检查（`py_compile`） | pass — `.claude/hooks/session-start.py`、`.trellis/scripts/task.py`、新测试文件 |
| 测试（模板） | pass — `Ran 231 tests ... OK`；定向：新测试 7/7、09-21 合约 23/23、`write_json_lf` 1/1、OpenCode 合同 13/13（Node 22.16.0 实际执行，无 skip） |
| 测试（根目录） | pass — `Ran 154 tests ... OK` |
| 安装器 / 升级套件 | 结构性红基线不变 — 48 例 / 26 失败，失败集合与开工前 set-diff 0（1.3 活模板 vs 1.2 manifest，归收尾子任务） |
| 模板 CLI 复核 | pass — 模板根 `--step 1.1` exit 0 非空；裸 `--step 1` exit 2 + `Step not found: 1` |
| `git diff --check` | pass — 无输出 |
| 构建 | not applicable — 本仓库不产出固件或可执行产品 |
| 部署 | not applicable — 无部署目标；模板由安装脚本分发，目标仓库验证属下游 |
| 硬件验证 | not applicable — 无硬件目标 |
| 下游验证 | not run — 由使用者在目标仓库执行 |

## 已知风险与取舍

1. 串平台断言为整文件级：若日后 `.claude` / `.opencode` 文件新增合法的其他 `--platform` 文案会变红；当前实测文件内除目标提示串外零其他 `--platform`，未来需要时可收窄到提示串行。
2. `task.py --step 1.1` 依赖模板 `workflow.md` 的 `#### 1.1` 标题存在（该标题由 workflow 步骤合同与既有测试覆盖）。
3. `unittest-overlay-same-red` 的原始 unittest 退出码为 1（26 个结构性失败不变），检查语义为"与开工前失败集合一致、无新增红项"，`plan.py` 记录的是对照脚本的 0；未通过触碰 manifest / history / VERSION 修绿。
4. 用户既有脏改动 `.opencode/package.json`（2 行 diff）为开工前快照内容，本任务未触碰。
5. 进程内 `get_step` 必须 patch `common.workflow_phase.get_repo_root`（模块内 `from .paths import get_repo_root` 绑定）；审查 round 1 指出的 cwd 误读已按此小修。

## 待主会话处理项

- 提交：按父任务流程提交；`.trellis/config.yaml` 保持 `session_auto_commit: false`。