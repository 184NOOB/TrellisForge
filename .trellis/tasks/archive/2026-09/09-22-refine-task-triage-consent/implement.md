# 执行计划：细化任务创建询问的触发条件（仅示例模板）

> 纯文本/字符串替换，**仅改 `templates/embedded-c-overlay/` 下 5 个文件**。
> 禁改：根目录自用工作流文件、VERSION、`history/`、manifest、结构迁移链、README、接入指南（spec L15/L18）。
> 不新增/删除文件，不动注入逻辑与 `[workflow-state:*]` 标签。各处复用统一措辞，禁止分叉。

## 统一新措辞

- 默认句：`Default: do the work. Code analysis, Q&A, and single-file local edits proceed directly with no Trellis prompt.`
- 询问条件句：`Ask about creating a Trellis task only when the user explicitly wants code written AND it is complex (multi-file, workflow/Hook/contract mechanism, design tradeoffs or multi-step, or template-affecting).`
- 拒绝处理句：`If the user says no, do not do broad inline implementation; explain, clarify scope, or suggest a smaller split.`

## 有序清单（全部位于 templates/embedded-c-overlay/）

- [ ] 1. `.trellis/workflow.md` Phase Index 行 →
      `Phase 1: Plan    → triage; ask task-creation consent only for complex coding work, then run Grill Me and write planning artifacts`
- [ ] 2. `.trellis/workflow.md` `### Request Triage` 重写为四要点：
      默认句 / 询问条件句（完整版含 `spans multiple files, touches workflow/Hook/contract mechanisms, needs design tradeoffs or multi-step implementation, or affects the published template`）/ 拒绝处理句 / `User approval to create a task is not approval to start implementation. Planning still happens first.`
- [ ] 3. `.trellis/workflow.md` `[workflow-state:no_task]` 块正文重写（保留标签行）：
      第一行 `No active task. Default to doing the work: code analysis, Q&A, and single-file local edits proceed directly with no Trellis prompt.`
      第二行 询问条件句 + 拒绝处理句。
- [ ] 4. `.trellis/workflow.md` 自定义不变量行 →
      `- No active task must triage first; ask for task-creation consent only for explicitly-requested complex code changes before creating a Trellis task.`
- [ ] 5. `.claude/hooks/session-start.py` NO ACTIVE TASK 分支 → `Next-Action:` 用 默认句 + 询问条件句。
- [ ] 6. `.codex/hooks/session-start.py` 同分支 → `Next:` 用 默认句 + 询问条件句。
- [ ] 7. `.opencode/lib/session-utils.js` `base` 常量 → `Next-Action:` 用 默认句 + 询问条件句（保留 `ambiguous` 追加段）。
- [ ] 8. `.opencode/commands/trellis/start.md` "No active task" 项 →
      `- **No active task** → triage. Default to doing the work: code analysis, Q&A, and single-file local edits proceed directly with no Trellis prompt. Ask about creating a Trellis task only when the user explicitly wants code written AND it is complex (multi-file, workflow/Hook/contract mechanism, design tradeoffs or multi-step, or template-affecting). If the user says no, skip Trellis for this session.`

## 验证命令（按序）

- [ ] V1. 模板套件无回归：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`（基线 201 例，应仍全绿）
- [ ] V2. 根回归套件：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`（基线 154 例，不受影响应全绿）
- [ ] V3. `python -m py_compile templates/embedded-c-overlay/.claude/hooks/session-start.py templates/embedded-c-overlay/.codex/hooks/session-start.py`
- [ ] V4. `node --check templates/embedded-c-overlay/.opencode/lib/session-utils.js`（有 node 时）
- [ ] V5. `git diff --check`（无输出）
- [ ] V6. 人工核对：
      - 模板内 grep `ask only whether|Classify the current turn|First classify` 无残留；统一新措辞在 5 个文件均在场；
      - `[workflow-state:no_task]` / `[/workflow-state:no_task]` 标签完整；
      - `git status --short` 功能改动只在 `templates/embedded-c-overlay/`（5 文件）与本任务工件；
        根目录工作流文件、`VERSION`、`history/`、manifest、README、接入指南零改动。

> 注意：**不要**把根级 `tests/test_overlay_tools.py::test_live_template_matches_12_manifest`
> 当作本任务门禁——它当前已因 1.3 既定中间态为红，恢复属发布收尾子任务（spec L18）。
> 本任务只追加预期漂移，不得改 manifest/VERSION 去修它。

## 风险文件 / 回滚点

- 高风险：模板 `workflow.md`（标签块解析）、模板 `session-utils.js`（模板 parity 测试）。
- 回滚：`git checkout -- templates/embedded-c-overlay/<file>`；改动彼此独立，可单文件回退。

## 子代理派发模型（本机环境，非仓库交付物）

- `trellis-implement` → `aliyun-test/deepseek-v4.1-flash`
- `trellis-check` → `aliyun-test/qwen3.8-max-0902`
- 配置位置：全局 `~/.config/opencode/opencode.json` 的 `agent` 段（部分字段覆盖，仅 `model`）。
  **不写入项目 `.opencode/agents/*.md`**：这些是 git 跟踪且模板镜像发布的受管文件，
  写入本机专属 provider 会造成根目录改动、项目↔模板分叉，并使下游因无 `aliyun-test` provider 失效。
- 生效条件：opencode 配置不热重载，需重启会话后派发才使用上述模型。

## 评审

- Review level: standard → 实施后派发独立 `trellis-check` 代理复核，聚焦：模板范围正确、
  根目录与发布资产零改动、统一措辞一致、标签完整、验证口径符合本计划。
