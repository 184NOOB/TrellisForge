# Design：审查模板主会话严重度复核规则（双侧）

## 1. 问题与目标

模板审查契约的循环退出以 Check Agent 报告的 `Blocking findings count` /
“newest independent report shows zero blocking findings” 为唯一事实来源。
当 Agent 把触碰安全/正确性/验收标准的问题错标为非 blocking，主会话看到
blocking=0 即放行。本设计在模板层建立双侧防线：

- 生产端（模板内 4 个 Check Agent）：绝对门槛定级，源头禁止降级。
- 消费端（审查 Skill 双镜像 + workflow.md）：主会话 Severity Adjudication；
  **真正驱动循环的 IF/until 句**以复核后的 adjudicated count 为主语。

不采用“只在 825/871 加两句声明、循环原句不动”：825-827 是 Codex inline 副本；
Claude/OpenCode/Codex 子代理走 756-772；逐轮注入走 244/272。远处声明无法覆盖
模型实际执行的最近退出句。既有测试不钉 `newest independent report`，改主语
不会仅因那一短语而红；须保留的是 `zero blocking` 等已列出的子串。

## 2. 边界

- 写入：仅 `templates/embedded-c-overlay/`。
- 禁改：根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/`；
  `history/`、`migrations/`、版本号、README、`docs/接入指南.md`。
- 不改变五级 profile 的范围、独立派发次数、commit-ready 门；只改定级与退出主语。
- 父任务：挂到 `09-17-trellisforge-1-3-upgrade`，收尾子任务保持末位。

## 3. 消费端（权威契约：`.agents` Skill + `.opencode` 镜像）

两份 SKILL.md 必须逐字节一致。先改 `.agents`，再复制到 `.opencode`。

### 3.1 新增 `## Severity Adjudication`（置于 `## Evidence Invalidation` 前）

语义（实施时定稿英文，须含测试锚点 `absolute gate`、`signals`、`escalate`、
`adjudicated`、`downgrade`）：

1. 绝对门槛：触碰安全、正确性或验收标准的失败都是 blocking；任何 profile、
   任何 Agent 标签都不能豁免。
2. Agent 的 severity 与 `Blocking findings count` 是信号，不是最终事实。
3. 主会话在 Verify before routing 确认真实且属于本任务后，对每条仍开放的
   finding 按绝对门槛独立重定级。
4. 升级：命中门槛但被标为非 blocking → 升为 blocking，计入 adjudicated
   blocking count。升级不得记 residual risk，不得豁免。
5. 降级：未命中门槛时，主会话可以把 Agent 标成 blocking 的项降为非 blocking，
   记 residual risk 与理由。命中门槛的项禁止降级。
6. 每条升级/降级必须留下可审计理由。
7. 再审：adjudicated blocking 走 **该 profile 既有** blocking-fix 路径
   （见 PRD R3）；本节目的是定级，不在 Ownership 节调度审查轮次。

### 3.2 既有段落修改

- **Verify before routing**：核实后按 `## Severity Adjudication` 重定级，再路由。
  禁止在 Ownership 节写 `dispatch a fresh Check Agent` 或 `an extra review round`
  （`test_review_fix_ownership_contract.py:227-232`）。
- Skill :213-214：signals only 扩展为不得单独决定 routing **或 loop exit**。
- Skill :220-222：non-blocking 不触发完整独立再审 —— 以 **复核后** 的标签为准；
  被升级的项按 blocking 进入该 profile 循环。
- `## Report Contract` 的 `Blocking findings count`：主会话对该计数独立复核；
  只有 adjudicated count 驱动循环退出。
- **Profile Matrix :50-52** 与 **Reinforced / Comprehensive / Strict 循环正文**：
  把 “until blocking findings are zero” / “until the newest independent report
  shows zero blocking findings” / “If the latest independent report has blocking
  findings” 的主语改为 adjudicated count。保留子串 `zero blocking`、
  `fresh independent`，以满足 `test_review_profile_contract.py:165-169`。
- Standard 节 :99-101 的 “do not start another complete independent review
  unless the task scope materially changes” **原句保留**（AC6）。

### 3.3 `templates/embedded-c-overlay/.trellis/workflow.md`

必须改写的循环/退出句（主语 → adjudicated count；保留 design §6 断言子串）：

| 位置 | 角色 |
|---|---|
| :244 `[workflow-state:in_progress]` | 逐轮注入，Claude/OpenCode/Codex 子代理主路径 |
| :272 `[workflow-state:in_progress-inline]` | 逐轮注入，Codex inline |
| :756-772 权威 profile 区 | 含 :758 “If the report has blocking findings”、:761 until 句、:766-772 comprehensive/strict |
| :825-827 `[codex-inline]` | inline 副本，与 756-772 语义对齐 |
| :835 Final pass | 提交前确认 |
| :871 Review-profile preamble | Phase 3.4；保留 `require no extra commit-ready review round` 且 preamble 内 `commit-ready final review` 恰好 1 次 |

权威声明可落在 756-772 区首条与 871 各一句，**不能代替**上表原句改写。

## 4. 生产端（模板内 4 个 Check Agent）

统一规则文本（各文件按其格式落位；路径均相对 `templates/embedded-c-overlay/`）：

> Any failure that touches safety, correctness, or an acceptance criterion must
> be classified as blocking severity and counted in `Blocking findings count`;
> never downgrade it to high/medium/low (or major/minor). The main session
> independently re-grades every finding against this absolute gate; loop exit
> uses the main session's adjudicated blocking count, not this report's count
> alone.

落位：

- `.claude/agents/trellis-check.md`：Step 3 新增定级条；Review Profile 段追加；
  :77/:79 “until blocking findings are zero” 改为指向主会话 adjudicated count。
- `.opencode/agents/trellis-check.md`：同上；保留
  “use `standard` and must be reported”（:98）。
- `.codex/agents/trellis-check.toml`：developer_instructions 的 Fix-only 段追加
  定级规则；:26-28 until 句改指向 adjudicated count；
  `- Blocking findings count:` 字段行不变。
- `.trellis/agents/check.md`：Workflow 步骤 5 新增定级条；Report Format 前追加
  一句；:123 字段与 :126 severity 枚举保持；:106 until 句改指向 adjudicated count。

术语：模板枚举 `blocking|high|medium|low`；下游 “major/minor” 并列点名。

不改 `.opencode/skills/trellis-check/SKILL.md`：它声明审查 Skill 为权威契约，
只做通用核对步骤；定级/退出以审查 Skill + Agent 定义为准。Hook/plugin 的
Finding handling 属修复归属，不调度退出，本任务不改。

## 5. 契约测试

新增
`templates/embedded-c-overlay/.trellis/scripts/tests/test_review_severity_adjudication_contract.py`
（静态解析，复用 `_read`/`_section`）：

1. Skill 含 `## Severity Adjudication`，节内含 absolute gate / signals /
   escalate / adjudicated / downgrade。
2. `.opencode` 镜像与 `.agents` 逐字节一致。
3. Verify before routing 引用 Severity Adjudication。
4. Report Contract 含 adjudicated count 驱动退出。
5. Skill `## Reinforced`（及 Comprehensive/Strict 或全文）循环 IF/until 不再把
   `newest independent report` 当作唯一退出主语；须出现 adjudicated。
6. workflow.md：`:244` 与 `:272` 所在 state 块、权威 profile 区（含
   “If the report has” 那句）均含 adjudicated / Severity Adjudication 退出主语。
7. 4 个 Check Agent 含 `must be classified as blocking`、`never downgrade`、
   `acceptance criterion`。
8. 负面：不引入 `test_review_profile_contract.py` 的 STALE_ENUMERATIONS。
9. Standard 节仍含不因非 Evidence-Invalidation 而再开一轮完整独立审查的既有语义。

独立新文件，不扩写 profile 合同测试。

## 6. 兼容性与风险

保留的既有断言子串：

- `` `reinforced`: dispatch an independent affected-scope ``
- `invalidate prior evidence`、`re-trigger the current profile's review`
- `require no extra commit-ready review round`；preamble 中
  `commit-ready final review` 恰好 1 次
- `otherwise default to `standard``
- canonical `light|standard|reinforced|comprehensive|strict`
- Reinforced 节：`affected-scope`、`fresh independent`、`zero blocking`
- Comprehensive：`does NOT\n  add an extra commit-ready review round`
- Strict：`unconditional`、`fresh independent`
- OpenCode check：`use `standard` and must be reported`（及 claude 对应短句）
- Ownership：`mechanical, small, and determinate`、`never schedules a review round`；
  节内不得出现 `dispatch a fresh Check Agent`、`an extra review round`

风险：改 244/272 长行时破坏 dispatch 自我豁免句 → 改前拷贝整行，只替换
until-blocking 片段。先改 Skill 再复制镜像。无运行时脚本改动。

## 7. 回滚

`git checkout -- templates/embedded-c-overlay`；删除新增测试文件。
父任务 children 链接若需撤回：`task.py remove-subtask`。

## 8. 执行方式

散文 + 静态测试，主会话直接实施，不派发 Implement Agent。完成后按本任务
`reinforced` profile：派发独立 affected-scope `trellis-check`；主会话按本规则
复核定级；adjudicated blocking 走 blocking-fix 后再派新一轮，直到复核后计数为零。
