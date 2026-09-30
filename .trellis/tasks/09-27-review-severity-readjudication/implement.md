# Implement：审查模板主会话严重度复核规则

## 前置

- 执行方式：主会话直接实施；禁止派发 Implement Agent。
- 禁改：根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/`；
  `history/`、`migrations/`、版本号、README、`docs/接入指南.md`。
- 所有写入仅限 `templates/embedded-c-overlay/`（下列路径均相对该根）。
- 实施前运行 `trellis-before-dev`；改退出句前 grep 全模板
  `newest independent report` / `until blocking findings are zero`。

## 有序清单

- [ ] 0. `task.py add-subtask 09-17-trellisforge-1-3-upgrade 09-27-review-severity-readjudication`（若尚未挂上）；确认收尾子任务仍在 children 末位。
- [ ] 1. 修改 `.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md`：
  - [ ] 1.1 新增 `## Severity Adjudication`（`## Evidence Invalidation` 前），design.md §3.1。
  - [ ] 1.2 Verify before routing 追加复核引用；Ownership 节不出现派发/加轮次禁词。
  - [ ] 1.3 扩展 signals-only 到 loop exit；:220-222 以复核后标签为准。
  - [ ] 1.4 Report Contract 的 `Blocking findings count` 追加 adjudicated 语义。
  - [ ] 1.5 改写 Profile Matrix :50-52 与 Reinforced/Comprehensive/Strict 循环
        IF/until（含 :110-113 “If the latest independent report has blocking
        findings”）；保留 `zero blocking` / `fresh independent`。
  - [ ] 1.6 Standard :99-101 原句不动。
- [ ] 2. 将 `.agents` 副本逐字节复制到
      `.opencode/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md`。
- [ ] 3. 修改 `.trellis/workflow.md`：按 design.md §3.3 表改写 :244、:272、
      :756-772（含 :758）、:825-827、:835、:871；改前确认 design.md §6 断言子串仍在。
- [ ] 4. 修改 4 个 Check Agent（design.md §4 统一文本 + until 句改指向 adjudicated）：
  - [ ] 4.1 `.claude/agents/trellis-check.md`
  - [ ] 4.2 `.opencode/agents/trellis-check.md`（保留 `use `standard` and must be reported`）
  - [ ] 4.3 `.codex/agents/trellis-check.toml`（字段行 `- Blocking findings count:` 不变）
  - [ ] 4.4 `.trellis/agents/check.md`（:123 字段、:126 枚举保持）
- [ ] 5. 新增 `.trellis/scripts/tests/test_review_severity_adjudication_contract.py`
      （design.md §5 共 9 组断言）。
- [ ] 6. 验证（见下）。
- [ ] 7. 按本任务 `reinforced` profile 派发独立 `trellis-check`；主会话按新规则
      复核定级；adjudicated blocking 修完后再派新一轮，直到复核后计数为零。

## 验证命令

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/tests/test_review_severity_adjudication_contract.py
git diff --check
git status --short
```

失败判据：任一测试失败、镜像不一致、`git diff --check` 报错、模板外改动、
Ownership 节出现禁词、Standard 独立审查次数语义被改。

## 风险文件 / 回滚点

- 高风险：两份 SKILL.md 逐字节一致（用复制）；workflow :244/:272 长行；
  Ownership 禁词；preamble `commit-ready final review` 计数。
- 回滚：`git checkout -- templates/embedded-c-overlay`；删除新测试；
  必要时 `task.py remove-subtask`。
- 清单 1-5 各为可回滚批次；步骤 6 失败回到对应步骤。

## start 前检查

- [ ] `implement.jsonl` / `check.jsonl` 均为含 `file` 的真实条目。
- [ ] `prd.md` 含非空 `## Spec References`；Planning Convergence = ready。
- [ ] 用户批准**本轮修正后的**最终规划摘要后，再 `set-meta plan_approved=true` → `task.py start`。
