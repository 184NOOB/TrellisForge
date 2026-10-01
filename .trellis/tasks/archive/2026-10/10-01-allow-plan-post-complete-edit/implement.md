# 实施清单

## 顺序

1. 改模板 `execution_plan.py`：
   - `cmd_revise`：审计重导之后，若全部为 `completed` 且有唯一 report，把 report 置 `pending` 并清 managed 字段。
   - `cmd_validate`：仍生效完成集；JSON pending + 历史 completed = sanctioned 重开；新阶段或重开时 report 必须 pending；`plan_approved` 原子写追加 `task_reopened`。
   - `replay_statuses` / `_replay_start_index`：处理 `task_reopened`。
   - `plan_protocol_block`：全完成分支默认 `revise`；进行中分支「justifies a sequel」（约 2166-2169）改为大改走 `revise`（sequel 未完成时本就会被拒绝）。
2. 改模板 `plan.py` 模块说明：sequel 是兼容命令，不是完成后必经。
3. 改模板 `workflow.md:246,274,357,614-615`；604 只保留布局事实，不写成必经冻结。
4. 同步 implement 四平台「Same-task sequel」段与 check 四平台中会把 live 完成后大修导向 sequel 的句子；check 保留指针/冻结只读。
5. 改 Claude `plan-pretool-reminder.py` 全完成警告：指向 `revise`；指针文件仍禁止手改。
6. 更新模板测试：
   - `test_execution_plan.py`：补加阶段通过 validate；revise 全完成后 report 为 pending；重开非 report 步骤可改 fingerprint；completed 改 fingerprint 仍拒；report 改成普通阶段仍拒（错误信息改为形状规则，不再要求 `rewritten after completion`，因为此时 report 已 pending）。更新 `test_protocol_block_offers_small_patch_and_sequel_when_complete` 与 `test_revise_never_creates_a_sequel_and_report_stays_terminal`。保留 sequel 冻结/指针/只读测试。
   - `test_small_patch_and_sequel_contract.py`：所有「完成后必须 sequel / instead of revise / Same-task sequel / Hook sequel --reason」断言改为原地 `revise`；CLI `--help` 仍可出现 `sequel`。
7. 更新 `.trellis/spec/main/tooling/python.md`：Error Matrix「已完成 report 不可改写」改为「不可改成普通阶段，pending 后可改 depends_on」；Wrong/Correct 默认路径改为 `revise`；Tests Required 同步。
8. 回归：模板 `unittest discover`、改动 Python 的 `py_compile`、`git diff --check`。确认 diff 不含根目录 `.trellis/workflow.md` 与根目录 `execution_plan.py`。

## 验证命令

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py templates/embedded-c-overlay/.trellis/scripts/plan.py templates/embedded-c-overlay/.claude/hooks/plan-pretool-reminder.py
git diff --check
```

根目录 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` 只作只读回归，不改根测试来迁就模板。

构建/部署/硬件：`not applicable`。

## 风险文件

- `templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py`
- `templates/embedded-c-overlay/.trellis/scripts/plan.py`
- `templates/embedded-c-overlay/.trellis/workflow.md`
- `templates/embedded-c-overlay/.trellis/scripts/tests/test_execution_plan.py`
- `templates/embedded-c-overlay/.trellis/scripts/tests/test_small_patch_and_sequel_contract.py`
- implement/check：`.trellis/agents/`、`.claude/agents/`、`.codex/agents/`、`.opencode/agents/`
- `.claude/hooks/plan-pretool-reminder.py`
- `.trellis/spec/main/tooling/python.md`

## 回滚点

先落地引擎规则与单测，再改文案与契约字符串。文案测试红了只回文案；引擎测试红了不改契约字符串蒙混。

## `task.py start` 前

- `prd.md` / `design.md` / `implement.md` 已齐。
- jsonl 已有真实 spec 条目。
- 等待用户批准本规划摘要。
