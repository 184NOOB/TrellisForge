# 最终报告：细化任务创建询问的触发条件（仅示例模板）

- 任务：`.trellis/tasks/09-22-refine-task-triage-consent`
- 执行计划：revision 1（6 个阶段，p1-p6 全部完成）
- 提交状态：未提交（遵守禁 git commit 约束；改动留在工作树）

## 任务目标与结论

仅修改发布模板 `templates/embedded-c-overlay/` 的 5 个文件，把「无活动任务时是否询问创建
Trellis 任务」从「每轮先分类再询问」收紧为「默认直接干活；仅当用户明确要写代码 AND 实施
复杂时才询问」。**结论：完成**。5 个文件全部按 design.md/implement.md 的统一措辞逐字落地，
`[workflow-state:no_task]` 标签与其它状态块保持不变，根目录自用工作流文件与
VERSION/history/manifest/README/接入指南零改动。

## 改动文件

| 文件 | 改动点 |
|---|---|
| `templates/embedded-c-overlay/.trellis/workflow.md` | Phase Index 行 → `triage; ask task-creation consent only for complex coding work…`；`### Request Triage` 重写为四要点（默认直接干活/仅复杂编码询问/拒绝处理/审批≠实施）；`[workflow-state:no_task]` 块正文重写为两行（默认句 + 询问条件句与拒绝处理句），标签行与位置不变；Customizing Trellis 不变量行改为「triage first; ask… only for explicitly-requested complex code changes」 |
| `templates/embedded-c-overlay/.claude/hooks/session-start.py` | `_get_task_status` 的 NO ACTIVE TASK 分支：`Next-Action:` 改为默认句 + 询问条件句 |
| `templates/embedded-c-overlay/.codex/hooks/session-start.py` | 同分支（`Next:` 前缀）改为默认句 + 询问条件句 |
| `templates/embedded-c-overlay/.opencode/lib/session-utils.js` | `getTaskStatus` 的 `base` 常量改为 `Next-Action:` 默认句 + 询问条件句；`ambiguous` 追加段原样保留 |
| `templates/embedded-c-overlay/.opencode/commands/trellis/start.md` | 「No active task」款项改为 `→ triage.` 默认句 + 询问条件句 + `If the user says no, skip Trellis for this session.` |

任务工件（非交付文件）：

- `.trellis/tasks/09-22-refine-task-triage-consent/verify_triage.py` — 任务级审计脚本（pre/post 文案断言、snapshot/scope 作用域核对、report 小节校验）
- `.trellis/tasks/09-22-refine-task-triage-consent/baseline-git-status.txt` — 改动前 `git status --porcelain` 快照
- `.trellis/tasks/09-22-refine-task-triage-consent/execution-plan.json` / `execution-events.jsonl` — 执行计划与审计日志

## 阶段结果

| 阶段 | 结果 | 摘要 |
|---|---|---|
| p1-baseline-audit-harness | completed | 4/4 检查通过：改动前模板 201 例、根 154 例全绿；pre 审计 17 项全过（旧措辞在场、新措辞缺席）；快照 5 条既有条目 |
| p2-workflow-md | completed | workflow.md 4 处逐字改写；工作流审计 15/15（含标签对恰一次、其它 5 个 `[workflow-state:*]` 块与 HEAD 逐字一致） |
| p3-platform-hooks | completed | claude/codex 分支改写；hooks 审计 10/10（含分支以外代码与 HEAD 逐字一致）；两文件 py_compile 通过 |
| p4-opencode-entry | completed | `session-utils.js` base 段与 `start.md` 款项改写；opencode 审计 8/8（含 AMBIGUOUS 段保留、base 分支外一致）；`node --check` 通过 |
| p5-full-validation | completed | 模板 201 例、根 154 例全绿；全量审计 33/33；交付文件 diff-check 无输出；作用域审计确认新增改动仅 5 个模板文件 |
| p6-report | completed | 冻结修订复跑终态检查；本报告写入并注册 |

## 逐项检查结果

| 检查 ID | 命令 | 退出码 | 结果 |
|---|---|---|---|
| baseline-template-suite (p1) | `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` | 0 | pass：201 tests OK（与改动前基线相同） |
| baseline-root-suite (p1) | `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` | 0 | pass：154 tests OK |
| pre-edit-audit (p1) | `python -B .trellis/tasks/09-22-refine-task-triage-consent/verify_triage.py --expect pre` | 0 | pass：17/17（旧句在场、新句缺席；REJECT/APPROVAL 属保留片段已排除） |
| baseline-snapshot (p1) | `python -B …/verify_triage.py --mode snapshot` | 0 | pass：快照写入 `baseline-git-status.txt`（5 条既有条目） |
| workflow-md-audit (p2) | `python -B …/verify_triage.py --expect post --group workflow` | 0 | pass：15/15（新措辞在场、旧句缺席、标签对完整、其它状态块与 HEAD 一致） |
| hooks-audit (p3) | `python -B …/verify_triage.py --expect post --group hooks` | 0 | pass：10/10 |
| py-compile-hooks (p3) | `python -m py_compile templates/embedded-c-overlay/.claude/hooks/session-start.py templates/embedded-c-overlay/.codex/hooks/session-start.py` | 0 | pass |
| opencode-audit (p4) | `python -B …/verify_triage.py --expect post --group opencode` | 0 | pass：8/8 |
| node-check-session-utils (p4) | `node --check templates/embedded-c-overlay/.opencode/lib/session-utils.js` | 0 | pass（node v22.16.0） |
| unittest-template-all (p5/p6) | `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` | 0 | pass：201 tests OK（p5 与 p6 各复跑一次） |
| unittest-root-all (p5/p6) | `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` | 0 | pass：154 tests OK（p5 与 p6 各复跑一次） |
| triage-full-audit (p5/p6) | `python -B …/verify_triage.py --expect post --group all` | 0 | pass：33/33（p5 与 p6 各复跑一次） |
| git-diff-check (p5/p6) | `git diff --check -- templates/embedded-c-overlay` | 0 | pass：交付文件无输出 |
| scope-audit (p5) | `python -B …/verify_triage.py --mode scope` | 0 | pass：新增改动仅 5 个模板文件（name-status 全为 `M`）；根目录与发布资产零新增 |
| report-written (p6) | `python -B …/verify_triage.py --mode report` | 0 | pass：本报告存在且含必备小节 |

补充证据（非声明门禁，供复核）：

- 全局 `git diff --check`：退出码 2，输出 36 行告警，全部指向 `.trellis/tasks/09-17-trellisforge-1-3-upgrade/task.json`（该文件在改动前的 baseline 快照中已是 modified，属父任务 CRLF 重写造成的既存状态，与本任务无关；见「已知风险」）。
- 逐文件 diff 复核：5 个模板文件的 `git diff` 只包含 design.md/implement.md 指定的 4+2+2+1 处文案替换，无其它行变更。

## 未运行 / 不适用项

- 构建（build）：not applicable — 本仓库不产出固件或可执行产品，无构建命令。
- 部署/硬件验证：not applicable — 无硬件目标；安装脚本的目标仓库验证由使用者在目标项目执行。
- lint / typecheck：not applicable — 仓库 AGENTS.md 未定义，且不虚构。
- 模板安装器冒烟：not applicable — 本任务不改安装器；`templates/embedded-c-overlay` 正文改动不改变安装路径与清单。
- 根级发布套件 `tests/test_overlay_tools.py`：not run — 其中 `test_live_template_matches_12_manifest` 在任务开始前已因 1.3 既定中间态为红，spec L18 禁止本任务改 manifest/VERSION 去修它；本任务只追加预期漂移，恢复归发布收尾子任务。

## 验收结论

- AC1：pass — 模板 no_task 文案与 Request Triage 改为「默认直接干活、仅复杂编码才询问」（workflow-md-audit 覆盖）。
- AC2：pass — 分析/问答/单文件小改指引为直接开展工作、无 Trellis 提示（三平台启动文案与命令同款默认句）。
- AC3：pass — claude/codex/opencode 三处 NO ACTIVE TASK 文案与 workflow.md 策略一致（同一默认句与询问条件句；审计逐文件断言）。
- AC4：pass — `/trellis:start` 命令款项与新策略一致（start-bullet-new 逐字在场）。
- AC5：pass — `[workflow-state:no_task]` 标签对行级恰一次、块体可解析；模板全量套件与改动前同为 201 例全绿。
- AC6：pass — 根回归 154 例全绿；改动模板 `.py` 过 `py_compile`，`.js` 过 `node --check`；交付文件 `git diff --check` 无输出。
- AC7：pass — scope-audit 证明新增改动仅 5 个模板文件；根自用工作流文件、VERSION、`history/`、manifest、README、接入指南相对快照零改动。
- AC8：pass — 旧句 `ask only whether` / `Classify the current turn` / `First classify` 在 5 文件全部缺席，统一新措辞在 5 文件全部在场（full-audit 33/33）。

## 已知风险与交接

1. **发布门禁交接**：根级 `tests/test_overlay_tools.py::test_live_template_matches_12_manifest` 当前为红（live 模板早于 1.2 manifest 漂移，系 1.3 功能子任务既定中间态），本任务按 spec L18 未触碰 manifest/VERSION；恢复由发布收尾子任务 `09-17-readme-integration-guide-upgrade-patch` 在 1.3 用 `gen_migration.py` 重生成时自然纳入本改动。
2. **全局 `git diff --check` 既存告警**：`.trellis/tasks/09-17-trellisforge-1-3-upgrade/task.json` 在任务开始前已是 CRLF 重写的 modified 状态（baseline 快照可证），非本任务引入；本任务未改动该文件。如需清零，应由拥有父任务收尾职责的会话规范化其换行为 LF。
3. **分叉影响（已知并接受）**：只改模板意味着 TrellisForge 仓库自身会话仍保留旧「总是询问」行为；如需本仓库也生效，需另起子任务同步根目录文件（spec L16 单向约束，本次不处理）。
4. **审查状态**：Review level=standard，待主会话派发独立 `trellis-check` 代理做受影响范围的独立复核；本报告仅为实施侧自证。