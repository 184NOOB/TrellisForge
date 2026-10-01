# Research: G — 重复造轮子检查（条目 8）

- **Query**: 模板内是否已有“单次派发覆盖整条计划 / 不得单 phase 返回 / 空返回-block 义务”的表述
- **Scope**: internal（全文关键词扫描）
- **Date**: 2026-09-26

## 扫描方法（可复现）

```powershell
$tpl='templates/embedded-c-overlay'
Select-String -Path "$tpl/.trellis/workflow.md","$tpl/.trellis/agents/implement.md",
  "$tpl/.claude/agents/trellis-implement.md","$tpl/.opencode/agents/trellis-implement.md",
  "$tpl/.codex/agents/trellis-implement.toml",
  "$tpl/.trellis/scripts/common/execution_plan.py",
  "$tpl/.trellis/scripts/common/subagent_prompt_policy.py" `
  -Pattern '一次派发|整条|单个 phase|单 phase|per phase|Per phase|每个 phase|逐 phase|phase 链|一条链|whole plan|single dispatch|empty return|silent|静默|空返回|between rounds|re-dispatch|until|stop when|terminal' -Encoding UTF8
```

另对全模板（*.py/*.md/*.js/*.toml/*.json）grep `dispatchable`（0 命中，见 `07-plan-cli-surface-F.md` §1）。

## 结论：目标语义现状

**“单次派发必须串行走完整条 phase 链 / 不得单 phase 返回 / 静默空返回属协议违规”在模板中不存在任何既有表述。**
`一次派发`、`整条`、`phase 链`、`一条链`、`whole plan`、`single dispatch`、`empty return`、`空返回`、`单 phase`、
`逐 phase` 全部 0 命中。新增 A/B/C/D 文本不会与既有句子重复。

## 但存在语义相邻的既有文本（新增时必须对齐、避免矛盾）

| 位置 | 既有文本要点 | 与新义务的关系 |
|---|---|---|
| `subagent_prompt_policy.py:196-203` | execution_contract 末句 “**stop when** scope, evidence, verification, and report are complete” | 现有“停止条件”以**任务范围**为粒度；新增“不得单 phase 返回”需与其衔接（完成 = 整个 plan 含 report phase，正是 D 项要补的定义），否则两句 stop 语义并存易被误读 |
| `.codex/agents/trellis-implement.toml:51` | “**Stop when** the declared scope, acceptance evidence, verification, and report are complete unless new evidence expands the scope.” | 同上 |
| 三份平台代理 + channel 卡的 “Stop on completion”（claude md 122-125 / opencode md 135-138 / toml 43 / channel 卡 134-138） | “once scope, acceptance evidence, required verification, and the report are complete, stop. Do not repeat unaffected scans…” | 该条现义是**防过度重扫**，不是派发链义务；D 项扩写 completion 定义落点就在这里 |
| `execution_plan.py:2153-2157`（protocol block 进行分支） | “**Per phase loop**: `start <id>` → batch read/edit/check → `record` → `done <id>`” | 描述单 phase 内循环，未说一轮派发要跑几个 phase；B 项新增句子的落点 |
| `execution_plan.py:2162-2165` | “A recorded fail is permanent … recover with `block <id> --reason "..."` … → `revise` → edit → `validate`” | **block 义务已有**，但触发条件是“record 了 fail”，不是“无法继续却不 block 就空返回”；A/B 新增“无法继续必须 block + 结构化失败报告”是对该链的派发层扩展，需引用同一命令形态（`block <id> --reason`） |
| `.trellis/workflow.md:246` | “between rounds run `plan.py status` to decide **re-dispatch** vs 2.2” | 现状把 round 粒度留给主会话逐轮判断（下游事故根源）；C 项重定义 round 时必须改写/兼容这句与 611 行 |
| `.trellis/workflow.md:611` | “Between implement rounds … runnable tasks → **re-dispatch** …” | 同上（轮间判定表现状） |
| `.trellis/workflow.md:605` | “**Round 1**: the implementer … writes the plan first” | Round 1 语义 = 建计划轮；C 项定义 “round = 一次 implement 派发” 时要与 Round 1 既有用法兼容（Round 1 也是一次派发） |
| `.trellis/agents/implement.md:148-159`（Channel Termination Contract） | 158-159：“无法继续:…在回复中声明失败并给出原因,以失败状态结束 turn,使 supervisor 记录 `error`;**不得静默挂起或未完成就结束**。” | **全模板唯一“不得静默”义务**，但只约束 channel worker（trellis channel runtime），不覆盖三平台原生派发；A/D 新增义务与其措辞方向一致，可对齐术语（“结构化失败报告” vs “声明失败并给出原因”） |
| 四份代理定义 + workflow.md:609 | “A failed phase is audited through `plan.py block <id> --reason "..."` — there is no separate task_failed event” | block 是既有失败审计通道，新义务应复用而非另造机制 |
| `.trellis/workflow.md:706-709`（2.1.2） | 等待期间主会话“不运行 `plan.py status`…读到的是半成品状态” | C 项“主会话不逐 phase 派发”与 Codex 静默等待合同方向一致；新句子放入组合块时不得引入 CODEX_ONLY_TERMS（见 `04-workflow-md-dispatch-text-C.md` §3.3） |

## 命名/术语建议依据（非建议，仅事实）

- “round” 一词在模板中已有两类既定义用法：implement 轮（workflow.md 246/605/611）与审查轮
  （workflow.md 244/272/756-767/824-835/871）。C 项重定义 implement 轮时，审查轮语义不受影响，
  但 `test_review_profile_contract.py` 与 `test_review_fix_ownership_contract.py:93`
  （`never schedules a review round`）锁定的是审查轮措辞，勿在改写中误伤。
- “terminal” 在模板中已有三义：terminal report phase（execution_plan.py:2086 等）、
  Channel 终态报告（implement.md:46、155-159）、Codex 终端 session（workflow.md:646-688）。
  新增“终端 report phase done”表述建议沿用 “terminal level=report phase” 既有拼写（execution_plan.py:2086、2158）。
