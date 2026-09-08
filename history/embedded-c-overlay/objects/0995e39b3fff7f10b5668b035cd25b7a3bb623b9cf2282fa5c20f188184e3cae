# 两级验证改造 — 低风险发现处理记录

第一轮审查（2026-09-02）：高风险 0 / 低风险 15。
第二轮（2026-09-03）：用户要求全部修复。以下逐项记录处置结果。
PRD 来源：`the Trellis two-level verification PRD`。

## 已修复（代码/文档）

- **F1** ✅ schema 拒绝消息补「不迁移、用 template 重新生成、勿手改 schema 字段」警告；顶层 legacy 字段（risk/required_evidence/…）与任务级同样拒绝。测试 `test_validate_rejects_top_level_legacy_fields`。
- **F2** ✅ workflow.md 与两份 check agent 文档明确：声明式 `required_checks` 的改名/删除/降级由 2.2 独立审查对照 prd.md 复核（plan.py 只能保证存在与 pass）。
- **F3** ✅ validate 新增规则：report 阶段必须传递依赖计划中的每一个其它阶段（终态 + 全覆盖双重检查）。测试 `test_report_phase_must_depend_on_all_work` / `test_report_phase_transitive_coverage_counts`；协议注入文本与三份 implement 提示词同步。
- **F6** ✅ revise 崩溃自愈：proposed + revision==expected+1 + 上一 revision 有 approval 时，再跑一次 `revise --reason` 补记缺失的 `plan_revised` 事件（事件带 `recovered: true`）；validate 的 revision 互斥消息改为指向该出路，不再要求手改 revision。approved 分支同时补「无匹配 plan_approved 事件」检测（覆盖 approve 崩溃窗）。测试 `test_revise_self_heals_crashed_revise_event`。
- **F7** ✅ `--task` 现在子命令前后均可（parent parser + SUPPRESS 默认）；docstring 明示 argparse 用法错误退出码为 2。测试 `test_task_flag_accepted_after_subcommand`。
- **F9** ✅（第一轮尾批）`_require_mutable` 的 managed_drift hint 补崩溃恢复出路。
- **F10** ✅（第一轮尾批）清除 hint 中已删除的 `plan.py check` 残留字样。
- **F11** ✅ validate 拒绝「proposed + 当前 revision 已有 plan_approved」的静默手翻重批准，指引：改回 approved → 走 revise（revise 会回滚未授权守卫编辑）。测试 `test_hand_flip_to_proposed_cannot_reapprove`。
- **F12** ✅（第一轮尾批）workflow.md 派发文案不再暗示可 record「unavailable/inapplicable」（record 仅 pass|fail）；4 处改为最终消息报告 + block/revise 出路。
- **F14** ✅ `mutate_with_audit` 支持事件列表；`plan_completed` 与末个 `task_completed` 同一原子写路径（失败同回滚），消除裸 append。
- **F15** ✅ `scope.write` 拒绝无界模式 `*` / `**`（整仓库匹配）。测试 `test_validate_rejects_unbounded_write_scope`。

## 判定为误报/有意偏差（不改代码）

- **F4** `--summary` 必填：PRD §7 标可选，但 §5.2 第 4 条与 §8.1 要求每条记录含简短摘要，取更严解释。**有意偏差，保留。**
- **F5** `status --quiet` 为 PRD 外纯增量显示项；`phase-result` 兼容按 §11「不迁移」彻底删除。**保留现状。**
- **F8** 复核为**误报**：`compute_status` 的 runnable 仅收 `pending`（blocked 被排除并单列），`format_status`/注入文本对 blocked 有独立行；`start` 允许从 blocked 恢复是 cmd_block 明示的设计（失败审计载体），无互相拉扯的缺口。
- **F13** 本就是残留排查结论（无行动项）。

---

# 第二轮审查（2026-09-03）：高风险 0 / 低风险 8（R2-1~R2-8）

第二轮修复本身经受住攻击（自愈无旁路、崩溃矩阵可达、argparse 正确、闭包正确）。其中 R2-1~R2-6
属本轮修复自身的缺陷/消息错误或口径分裂，已全部处置；R2-7/R2-8 登记为偏差。

- **R2-1** ✅ F15 泛化：`scope.write` 拒绝所有「纯通配段」组合（`*`、`**`、`**/*`、`*/**`、`*/*`…），含固定段的 glob（`src/**`）仍合法。测试覆盖 6 种变体。
- **R2-2** ✅ 不可哈希 `depends_on` 元素（模型手误写 `[{...}]`）不再触发 TypeError traceback：shape 检查、`_find_cycle`、report 闭包全部加 `isinstance(dep, str)` 守卫，返回干净验证失败。测试 `test_validate_rejects_unhashable_dependency_cleanly`。
- **R2-3** ✅ heal 措辞诚实化：事件 reason 与返回消息明示「heal 仅补记事件、不校验内容，2.2 审查应把该 revision 当作正常计划变更」，防止按 `recovered` 标记盲信。
- **R2-4** ✅ hint 拆台修复：approved+revision 不符（手改特征，approve 从不改 revision）改为「改回 N 保持 approved → revise」，不再诱导翻 proposed 撞 F11；proposed+revision>expected+1 时不再错误承诺 heal（heal 仅接受恰好 +1），给出两条明确出路。测试 `test_revise_heals_only_the_exact_crash_window`。
- **R2-5** ✅ 口径统一为 PRD §8.2 字面（至多一个 + 末端 + 全覆盖），validate 行为不变；注入文本、三份 implement 提示词、代码注释从「exactly one」改为「以 report 阶段收尾（校验允许至多一个；真实任务应配备）」，无 report 计划的兜底由 2.2 review 承担。
- **R2-6** ✅ 部分：`plan_revised` 的 reset 列表/输出消息只列真正落回 pending 的任务（审计 completed 而 JSON 误标 in_progress 的被重导为 completed，不再虚报 reset）。测试 `test_revise_reset_note_only_lists_real_resets`。剩余（done 列表事件半途失败后该 revision 永久缺 `plan_completed`）确认无功能影响（无消费方、状态可重导），仅审计观感，不处理。
- **R2-7** 登记为有意偏差：任务级 `objective` 必填系 schema-2 沿承，PRD §5 示例未含该字段；逐字复制 PRD 示例需补 objective 才能过 validate（template 已含）。
- **R2-8** 登记为有意超集：`cmd_block` 允许 `pending→blocked`（PRD §6 图仅画 `in_progress→blocked`），语义为「预先放弃并留审计」，不影响验证下限。

## 回归状态

`python .trellis/scripts/tests/test_execution_plan.py` 66 项全过（2026-09-03 第二轮后）；
test_planning_gate / test_subagent_prompt_contract / test_active_task_session_isolation 均 OK；
旧 token（risk/raw/phase-result/record/check/reject_report/edits_over_limit）在运行协议中已清除；代码中仅保留 schema 3 对 legacy 字段的拒绝提示和测试样例。

---

# 本轮独立审查（2026-09-03）：高风险 1（已修复）/ 低风险 1

- **R3-1** ✅ `workflow.md` Phase 2 核心执行计划段仍是 schema 2 文案
  （`risk`、`plan.py check`、`phase-result`、旧 `record` 语法），会误导实施代理
  使用已删除的命令。已同步 schema 3 两级验证、`required_checks`、报告阶段、失败
  不可覆盖、崩溃恢复和批处理协议；并清理顶部状态块与 inline/dispatch 文案残留。
- **R3-2** 低风险：`format_status(task_dir)` 未传 `repo_root` 时，以 task 目录而非
  仓库根目录计算 artifact key，可能把已经通过 `record --artifact final-report.md`
  注册的报告显示为“未注册”。CLI 与 hook 当前均传入 `repo_root`，正常工作流不受影响；
  后续可为该无参调用补一个仓库根目录参数/专门测试。

---

# 第二轮独立审查（2026-09-03）：高风险 0 / 低风险 1

- **R4-1** 低风险：`README.md` 将
  `.trellis/scripts/tests/test_subagent_prompt_contract.py` 描述为“23 项”测试，
  当前模板实际为 15 项。仅影响维护文档的数量描述，不影响安装或运行；后续可在
  测试增删时同步更新该统计。
