# 技术设计：细化任务创建询问的触发条件（仅示例模板）

## 范围与边界

只修改 `templates/embedded-c-overlay/` 下 5 个文件的"无活动任务（no_task）时是否询问建任务"
指引文案。**根目录自用工作流文件只读、禁改**（spec `templates-and-docs.md` L14-16/L22）。
**VERSION / manifest / canonical 对象 / 结构迁移链 / README / 接入指南禁改**（spec L18，
归发布收尾子任务）。不改解析逻辑、状态机、`task.py`/`plan.py` 行为或注入机制。
`[workflow-state:*]` 块仍由模板的 `inject-workflow-state` 原样注入；`<task-status>` 仍由模板
各平台 session 启动脚本生成。改动是纯文本/字符串替换，保持结构、缩进与标签不变。

## 统一判定标准（单一事实源）

- 默认直接干活：代码分析、问答/解释、单文件局部小改，直接执行，不插入任何 Trellis 询问。
- 仅当「用户明确要写代码」AND「实施复杂」时才询问是否建任务。
  复杂 = 满足任一：跨多文件 / 触及 workflow·Hook·契约等机制 / 需设计权衡或分步实施 / 影响发布模板。
- 询问后用户拒绝：不做宽泛内联实现；改为解释、澄清范围或建议更小拆分。
- 建任务同意 ≠ 实施同意；仍先规划。

## 改动清单（仅模板，5 个文件）

### 1. `templates/embedded-c-overlay/.trellis/workflow.md`
- Phase Index 行：`classify, get task-creation consent` → `triage; ask task-creation consent only for complex coding work`。
- `### Request Triage`：重写为"默认直接干活 + 仅复杂编码才询问"四要点。
- `[workflow-state:no_task]` 块正文：重写为默认直接干活、仅复杂编码才询问；保留标签行不变。
- 自定义不变量行：`No active task must triage first and ask for task-creation consent` →
  `No active task must triage first; ask for task-creation consent only for explicitly-requested complex code changes`。
- Phase 1 Goal 行（"when a task is needed" 已是条件式）保持不变。

### 2. `templates/embedded-c-overlay/.claude/hooks/session-start.py`
- `_get_task_status` 的 NO ACTIVE TASK 分支：`Next-Action:` 用 默认句 + 询问条件句。

### 3. `templates/embedded-c-overlay/.codex/hooks/session-start.py`
- 同分支（Codex 用 `Next:` 前缀）：默认句 + 询问条件句。

### 4. `templates/embedded-c-overlay/.opencode/lib/session-utils.js`
- `getTaskStatus` 的 `base` 常量：`Next-Action:` 用 默认句 + 询问条件句；保留 `ambiguous` 追加段不变。

### 5. `templates/embedded-c-overlay/.opencode/commands/trellis/start.md`
- "No active task" 款项：`triage. Default to doing the work …` + 询问条件句 + `If the user says no, skip Trellis for this session.`

> 模板不发布 `trellis-start` skill，无对应改动；不新增模板测试文件（见下"测试取舍"）。

## 兼容性与风险

- 模板套件（`templates/embedded-c-overlay/.trellis/scripts/tests`）：无测试断言被改 triage 文案；
  parity 测试仅校验同根内 skill 镜像字节一致，不涉及本次文件。改动后应仍全绿（同级子任务基线 201 例）。
- 根回归套件（`.trellis/scripts/tests`）：以项目根为校验目标，本次不动根文件，故不受影响、应仍全绿（基线 154 例）。
- 根级发布套件（`tests/test_overlay_tools.py`）：`test_live_template_matches_12_manifest`
  **当前已红**（live 模板早于 1.2 manifest 漂移，系同级 1.3 子任务既定中间态）。本改动只追加预期漂移，
  **不是本任务门禁**，且 spec L18 禁止本任务改 manifest 去修它。恢复由收尾任务 1.3 重生成负责。
- 注入机制不变：`[workflow-state:no_task]` 标签必须保留，否则模板 inject 解析失败。
- 占位符：新文案不含 `<...>` 尖括号 token，不触发安装器占位符替换/残留扫描问题。
- 回滚：纯文本改动，`git checkout -- templates/embedded-c-overlay/<file>` 可整体或单文件回退。

## 测试取舍

不新增模板契约测试。理由：triage 文案是面向 AI 的指引散文，无任何脚本/解析器消费它，
不像 review-level 枚举那样是程序化契约；用精确字符串测试锁定散文会在未来任何措辞微调时脆裂，
维护成本高于收益。质量保障改由：模板套件无回归 + grep 旧句缺席/新句在场 + `git diff --check`
+ standard 级独立 `trellis-check` 评审。

## 验证策略

- 模板套件：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`
- 根回归套件：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
- `python -m py_compile` 改动的模板 `.py`
- `node --check` 改动的模板 `.js`（若环境有 node）
- `git diff --check`
- 人工核对：模板内 grep `ask only whether|Classify the current turn|First classify` 无残留、新句在场；
  `[workflow-state:no_task]` 标签完整；`git status` 功能改动只在 templates/ 与任务工件，
  根文件与 VERSION/history/manifest/README/接入指南零改动。
