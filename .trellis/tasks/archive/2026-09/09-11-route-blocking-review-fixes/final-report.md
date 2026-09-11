# 最终验收报告 — 明确审查阻塞问题修复责任

任务：`.trellis/tasks/09-11-route-blocking-review-fixes`
执行方式：`trellis-implement` 子代理按 execution plan schema 3（revision 2）推进。

## 阶段结果

| 阶段 | 状态 | 检查 |
| --- | --- | --- |
| add-ownership-contract-test | completed | ownership-test-syntax：pass（py_compile 通过；改动前红色基线 9/11 断言按预期捕获漂移） |
| align-review-skill-workflow | completed | skill-workflow-routing-scan：pass；no-blanket-no-resume：pass |
| align-three-check-agents | completed | agents-boundaries-scan：pass；agents-no-unconditional-selffix：pass |
| align-hook-prompts | completed | hook-finding-handling-scan：pass；hooks-py-compile：pass |
| cross-file-consistency-tests | completed | ownership-contract-tests：pass（11/11）；review-profile-tests：pass（13/13）；subagent-prompt-tests：pass（15/15） |
| full-validation | completed | template-full-tests：pass（129/129）；root-regression：pass（99/99）；hooks-pycompile-final：pass；stale-policy-scan：pass（0 残留）；forbidden-dirs-clean：pass；diff-check-final：pass |
| report | completed | changed-files-audit：pass |

计划中途 revision 1 → 2：`test_trellis_channel_contract.py:264` 既有锚点 `self-fixing`
锁定在 Channel check card 中被本任务移除的措辞上，按协议 `block` + `revise` 将其改为
新的 precheck 锚点 `directly fixing a finding`，模板全量单测回绿。

## 修改文件（全部位于 `templates/embedded-c-overlay/`）

| 文件 | 改动 |
| --- | --- |
| `.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` | 重写 `Blocking-Finding Ownership`：主会话核实、机械直修边界、Phase 1/越界路由、Codex inline 由主会话实施、可靠续接原 Implement Agent 优先、不可续接时主会话/新 Implement Agent 分流、复杂度信号与可靠续接契约；修复责任不安排额外审查轮次 |
| `.trellis/workflow.md` | Phase 2.2 finding triage 改写为所有权路由；Check Agent 派发描述与职责段同步为机械直修边界 + 只报告集合；删除 fresh implementation pass 强制路由；`dispatch a new Implement Agent`/`reliably resume the original Implement Agent`/`never schedules a review round` 锚点就位 |
| `.trellis/agents/check.md` | description、Core Responsibilities、Workflow step 5 分类分支改为机械/小/确定/范围内直修 + 其余只报告；删除 `do not resume an exited agent` blanket 禁令；precheck 措辞 `self-fixing` → `directly fixing a finding` |
| `.claude/agents/trellis-check.md` | 删除无条件 `Fix issues yourself`；description/Important/Step 3/报告标题改为机械直修边界 + 只报告集合 + 不派发不续接 Implement Agent + 修复路由不安排审查轮次 |
| `.codex/agents/trellis-check.toml` | description 与 developer_instructions 将 `self-fix clear in-scope findings` 收紧为机械/小/确定直修 + 只报告集合 + 不派发不续接 Implement Agent |
| `.claude/hooks/inject-subagent-context.py` | `build_check_prompt` 注入 `## Finding handling` 段（与 Codex 端字节级一致），删除 `Fix issues yourself`；保留平台生命周期约束；内部注释 `self-fix loop` → `fix loop` |
| `.codex/hooks/inject-subagent-context.py` | 同上，保持 Codex 生命周期/Git/安全边界 |
| `.trellis/scripts/tests/test_review_fix_ownership_contract.py` | 新增：锁定 R1-R4 责任边界在各受管入口的一致性与旧文案漂移（11 项断言） |
| `.trellis/scripts/tests/test_trellis_channel_contract.py` | 既有 precheck 锚点 `self-fixing` → `directly fixing a finding`（保留测试意图） |

未修改任何根目录自用实现（`.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 的
运行工作流，除任务目录外的状态文件无改动，`forbidden-dirs-clean` 审计为空）。

## 验收条件映射（AC1-AC8）

- **AC1**：权威 review Skill 显式写出机械直修边界、Phase 1/越界路由与 Implement Agent
  选择顺序（可靠续接优先 → 主会话直接处理或新 Implement Agent），并在 workflow 同步。通过。
- **AC2**：Channel/Claude/Codex 三个 Check Agent 对机械、设计/判断、较大实现阻塞、
  规划缺陷、越界问题给出语义一致的处理方式（合约测试断言三端直修集合与只报告集合一致）。通过。
- **AC3**：Claude/Codex Hook `build_check_prompt` 不再要求无条件 self-fix，注入的
  `## Finding handling` 段与 Agent/authoritative review Skill 分级一致，未覆盖分级
  （Hook 输出含 `review profile` 与边界内容、无 `Fix issues yourself`）。通过。
- **AC4**：Codex inline 明确由主会话承担实现修复；不可靠续接宿主降级到主会话修复或
  新 Implement Agent，而非假定续接能力存在（Skill 与 workflow 均写明，测试断言锚点存在）。通过。
- **AC5**：修复责任条款未新增重复审查标准；`test_review_profile_contract.py` 13/13 通过，
  五档范围、轮次、fresh reviewer 与证据失效契约未被改写。通过。
- **AC6**：新增合约测试覆盖失败情形——Claude 无条件 self-fix 文案回归、Hook 绕过分级、
  禁止所有 Implement Agent 续接、修复责任触发额外审查轮次、平台间语义不一致；从改动前
  红色基线 9/11 断言失败证明这些情形可被捕获。通过。
- **AC7**：模板单测 129/129、根目录自用回归 99/99、两 Hook `py_compile`、`git diff --check`
  全绿；构建、部署、硬件验证为 `not applicable`（本仓库无固件/可执行产品/硬件目标）。通过。
- **AC8**：功能改动全部落在 `templates/embedded-c-overlay/`；根目录自用范围只读，未作为
  同步修改目标。通过。

## 跳过项与理由

- 构建、部署、硬件验证：`not applicable`，本仓库产出下游发布模板，无固件或可执行产品。
- 新增续接基础设施或会话标识持久化：`not run · 明确非目标`，职责路由只改变主会话选择实施
  责任方的顺序，不新增运行时能力。
- README、接入指南、升级补丁、VERSION、manifest、迁移链：`not applicable`，由固定收尾
  子任务 `09-10-readme-integration-guide-upgrade-patch` 统一处理。

## 任务级审查例外记录

本任务使用 `Review level: strict` 但采用用户指定的任务级例外：实施后执行独立 full-scope
审查；每批阻塞修复后 fresh Check Agent 完整重审至零阻塞；**不追加额外 commit-ready final
review**。该例外只影响本任务审查调度，未写入发布模板中的五档 profile 定义（模板 `strict`
的 commit-ready fresh 终审规则未被修改，相关 profile 合约测试仍通过）。

## 剩余风险

- 同一责任政策存在于 review Skill、workflow、三个 Agent、两个 Hook 与新增合约测试多个入口；
  后续任何入口被单独改宽都可能再次漂移。主要防线为 `test_review_fix_ownership_contract.py`，
  对 `module load` 的 Hook 提示做运行时断言而非只扫描源码。
- `resume Implement Agent` 与 `fresh Check Agent` 在字符串层容易混淆；模板与测试按角色区分，
  后续人工编辑需避免删除 reviewer 独立性要求。