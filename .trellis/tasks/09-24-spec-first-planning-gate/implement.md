# Implement: 模板规划门禁加固（仅模板）

前置：任务状态 in_progress；父任务 `09-17-trellisforge-1-3-upgrade`。**改动仅限 `templates/embedded-c-overlay/`；根目录 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/`、`AGENTS.md` 全程只读。** 行号为规划期锚点，实施时以内容 grep 重锚。

## Checklist

1. [ ] **硬层（模板）**：
   - `templates/embedded-c-overlay/.trellis/scripts/common/planning_gate.py`：签名扩为 `validate_planning_gate(task_dir, repo_root=None)`；加 `from .task_store import _has_subagent_platform`（已核实无循环 import）；新增校验 A（`## Spec References` 节存在且含 ≥1 条 `^[ \t]*-[ \t]+` 列表项）与校验 B（repo_root 传入且平台探测为真时，implement/check jsonl 各 ≥1 条含非空 `file` 字段的 JSON 行；文件缺失或非空行解析失败 → 错误）；错误消息风格对齐现有条目；两项校验追加进 errors 累积列表，`status != "planning"` 直通语义不变。
   - `templates/embedded-c-overlay/.trellis/scripts/task.py` cmd_start（:99）：`validate_planning_gate(full_path, repo_root)`；**不碰 :449-474 弃用守卫（同胞任务目标 :466-469）**。
   - `templates/embedded-c-overlay/.trellis/scripts/common/task_store.py` `_default_prd_content`（:197-231）：种子骨架补 `## Spec References` 节头 + 一行指引注释，**不加 `- ` 列表项**（未填写的种子须被校验 A 如实拦截；与 Planning Convergence 种子 pending 值同模式）。
   - `templates/embedded-c-overlay/.trellis/scripts/tests/test_planning_gate.py`：**先给 `READY_PRD` fixture 补 `## Spec References` 节**（既有 7 用例断言不变；不补则校验 A 击穿 3 个期望通过用例）；再新增：缺节/空节 → 拒绝；≥1 条 → 通过；种子-only + 有平台目录 → 拒绝；无平台目录 → 不因 jsonl 拒绝；真实条目 → 通过；未传 repo_root → 跳过 B；损坏 JSON 行 → 拒绝；`_default_prd_content` 输出含节头且不含占位列表项（种子骨架合同）。测试写法遵循 python.md:111（TemporaryDirectory fixture、不依赖真实 git）。
   - 验证：`python -B templates/embedded-c-overlay/.trellis/scripts/tests/test_planning_gate.py`；`python -m py_compile` 改动的 .py（planning_gate、task.py、task_store.py、test）。
2. [ ] **模板 workflow.md**：
   - 1.1 节（:407 起）开头段后插入 "Spec discovery (mandatory first evidence step)" 段；Guardrails 加一条（锚在 "Planning must be persisted…" 条目后）。
   - `[workflow-state:planning]` 与 `[workflow-state:planning-inline]` 块：各加 spec 发现 + Spec References 一句；"blocks unless convergence and subsequent approval markers are present" 句补 Spec References 与策展后 jsonl；其余行不动。
   - 1.4 节：:562 "rejects planning tasks unless…" 枚举补 Spec References 节与策展后 jsonl；:560 尾句补 start 门禁拒绝种子-only 表述；1.5 完成标准表加一行 Spec References（自查二轮新增，防文本与门禁失真）。
   - `.opencode/commands/trellis/start.md` :55-60 planning 分支穷举句补 Spec References 与策展后 jsonl（自查三轮新增；不碰 --platform 示例行与 no-task triage 段；`continue.md:12` 非穷举措辞不改）。
   - **禁触区**：`[workflow-state:no_task]` 块、Guardrails "Phase 2 source edits" 条目、Loading Step Detail 段、2.1.x 合同段。
   - 验证：workdir=`templates/embedded-c-overlay` 运行**模板自己的** `python ./.trellis/scripts/get_context.py --mode phase --step 1.1`（python.md:74：cwd 必须是模板根），输出含新段（真实 CLI，不做纯文本断言——python.md:105）；grep 确认禁触区文本未变。
3. [ ] **模板 SKILL**：
   - `.opencode/skills/trellis-brainstorm/SKILL.md`：Evidence Rule 补显式发现程序；Planning Flow step 2 "existing specs" 具体化；Artifact Rules prd.md 清单加 `## Spec References`；Quality Bar 加一条；:170 jsonl 句补 "(enforced by the start gate)"。
   - `.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` 与 `.opencode/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md`：step 1 "relevant Specs" 具体化、step 7 收敛前置补 Spec References、**intro 段 "only verifies the persisted convergence and approval markers" 更新为新校验集**（保留 "cannot prove…" 告诫）；frontmatter 不动。
   - 验证：`git diff --no-index` 两份 adapter 零差异；brainstorm 改动不引入未渲染占位符以外的新尖括号标记。
4. [ ] **模板 hook 提示文本（3 文件 × 2 个 planning 分支）**：`.codex/hooks/session-start.py`（:~284 区域）、`.claude/hooks/session-start.py`（:~396 区域）、`.opencode/lib/session-utils.js`（:~256 区域）——planning 状态的**无 prd 分支与有 prd 分支**各追加一句 spec 发现 + Spec References 要求。**禁触**：Step detail 提示串（:725 / :625，同胞任务目标）、no-task 段、其他状态分支。验证：`python -m py_compile` 两份 session-start.py；`node --check` session-utils.js；grep 确认三文件不含 `validate_planning_gate`（test_review_profile_contract.py:285 红线）。
5. [ ] **全量验证 + 范围自查**：
   - 模板套件：`python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`（基线 201 OK，实测 2026-09-24；实施后 = 201 + 新增用例，零既有用例破坏）
   - 根套件只读回归：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`（基线 154 OK；须保持一致，证明根零改动无副作用）
   - `git diff --check`；`git status` 范围自查：改动仅位于步骤 1-4 所列模板文件 + 本任务目录；根目录、`history/`、`VERSION`、manifest、`migrations/`、README、接入指南零改动。
   - 报告按 validation.md 四态：构建/硬件验证 `not applicable`（本仓库无产品目标）。
6. [ ] **CRLF 处置**：根 io.py 缺陷（python.md:139）仍在——实施期 CLI 若改写**已跟踪**的根目录 task.json 产生全文件 CRLF diff，对该工件 LF 归一并用 `git diff --ignore-cr-at-eol` 核实内容差异；本任务自身 task.json 为未跟踪新文件，不受影响。

## 同胞任务协调

实施步骤 1/4 前先 `git log --oneline -5 -- templates/embedded-c-overlay/.claude/hooks/session-start.py templates/embedded-c-overlay/.opencode/lib/session-utils.js templates/embedded-c-overlay/.trellis/scripts/task.py` 确认 `09-24-template-platform-hint-and-step-text` 是否已合入：已合入 → 按最新文本重锚行号；未合入 → 只改本任务区域，不触碰其目标行（Step detail 提示串 :725/:625、task.py:466-469）。

## Validation

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -B templates/embedded-c-overlay/.trellis/scripts/tests/test_planning_gate.py
python -m py_compile templates/embedded-c-overlay/.trellis/scripts/common/planning_gate.py templates/embedded-c-overlay/.trellis/scripts/common/task_store.py templates/embedded-c-overlay/.trellis/scripts/task.py templates/embedded-c-overlay/.trellis/scripts/tests/test_planning_gate.py templates/embedded-c-overlay/.codex/hooks/session-start.py templates/embedded-c-overlay/.claude/hooks/session-start.py
node --check templates/embedded-c-overlay/.opencode/lib/session-utils.js
git diff --check
```

模板侧 1.1 送达验证（workdir=模板根）：

```powershell
python ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

全部通过后才可进入 review。构建/硬件验证：`not applicable`（validation.md:11）。

## Review Gate

- Review level: **reinforced**（用户明确选择）→ 实施后派发独立 `trellis-check`（affected-scope：完整任务 diff、受影响模块、公开接口、直接调用点、一跳依赖、全部验收项、check.jsonl 所列 spec 起步并按影响证据扩展）。
- 若最新一轮独立报告存在阻塞发现：按所有权规则批量修复本轮阻塞项后，**派发全新的独立 `trellis-check`** 对完整 affected-scope 重新审查（不是只复查上轮发现），循环直到最新报告零阻塞；每轮报告轮次与阶段。零阻塞后无额外 commit-ready 审查。
- 审查重点：门禁语义与全部行为描述文案一致（state 块、1.4 枚举、1.5 表、adapter intro、brainstorm :170、start.md :55-60——不得残留 "only verifies" 类失真）、种子骨架含节头且无占位列表项、禁触区零改动（no_task 块、Phase-2 Guardrail 条目、Step detail 提示串、task.py 弃用守卫、session-utils no-task 段、start.md --platform 示例与 triage 段）、adapter 两份正文零差异、hook 无 `validate_planning_gate` 字样、**根目录零改动**、manifest/VERSION 零改动。

## Rollback Points

- 步骤 1（硬层代码）与步骤 2-4（软层文本）相互独立，可分别 `git checkout -- templates/embedded-c-overlay/<paths>` 回滚重做。
- 任一步验证失败 → 回滚该步涉及路径，不影响已通过步骤；根目录零改动 → 无运行态回滚需求；无数据迁移、无状态机语义变更。
