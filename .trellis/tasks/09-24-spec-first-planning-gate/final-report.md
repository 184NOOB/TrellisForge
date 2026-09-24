# Final Report — 09-24-spec-first-planning-gate

任务：模板规划门禁加固（spec 前置 + `task.py start` 机械校验，仅模板）
范围：全部改动位于 `templates/embedded-c-overlay/` 与任务目录；根目录零改动。

## Phase 结果

| Phase | 结果 |
|---|---|
| discover | completed（只读侦察） |
| gate-hard | completed |
| workflow-text | completed |
| skills-text | completed |
| hooks-text | completed |
| final-report | completed |

## 改动文件（全部位于 templates/embedded-c-overlay/）

| 文件 | 改动 |
|---|---|
| `.trellis/scripts/common/planning_gate.py` | `validate_planning_gate(task_dir, repo_root=None)`；校验 A（`## Spec References` 节 + ≥1 条列表项）与校验 B（子代理平台下 implement/check jsonl 各 ≥1 条含非空 `file` 的真实条目；文件缺失/解析失败 fail closed；未传 repo_root 跳过 B） |
| `.trellis/scripts/task.py` | `cmd_start` 门禁调用传入 `repo_root`（仅此行；弃用守卫 :449-474 未动） |
| `.trellis/scripts/common/task_store.py` | `_default_prd_content` 种子骨架补 `## Spec References` 节头 + 指引注释（无占位列表项，未填写必被校验 A 拦截） |
| `.trellis/scripts/tests/test_planning_gate.py` | READY_PRD 补节；新增 11 个用例（合计 18） |
| `.trellis/workflow.md` | 1.1 Spec discovery 段、Guardrails 条目、两个 `[workflow-state:*]` 块、1.4 门禁枚举 + 种子-only 拒绝、1.5 完成标准表行 |
| `.opencode/commands/trellis/start.md` | planning 分支穷举句补 Spec References + curated entry（--platform 示例与 triage 段未动） |
| `.opencode/skills/trellis-brainstorm/SKILL.md` | Evidence Rule 发现程序、Planning Flow step 2、Artifact Rules、Quality Bar、jsonl 句 `(enforced by the start gate)` |
| `.agents/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` | intro 门禁表述更新、step 1 发现程序、step 7 Spec References 前置 |
| `.opencode/skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` | 同上（与 .agents 副本字节零差异） |
| `.codex/hooks/session-start.py` | planning 状态两个 return 分支各补 Specs 句 |
| `.claude/hooks/session-start.py` | 同上 |
| `.opencode/lib/session-utils.js` | 同上（两个分支） |

任务目录工件：`execution-plan.json`、`execution-events.jsonl`、`research/verify_delivery.py`（可重放 CLI/文本/diff 矩阵）、`research/scope-baseline.txt`（实施前 git status 基线）、`final-report.md`。

## 检查结果（record 明细）

| check | 命令 | 结果 |
|---|---|---|
| template-suite | `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` | pass — 212 tests OK（201 基线 + 11 新增，零既有破坏） |
| root-suite | `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` | pass — 154 tests OK（与实测基线一致，根零改动无副作用） |
| compile-all | `python -m py_compile` × 6 个改动 .py（编译后清理 `__pycache__`） | pass — exit 0 |
| node-check-final | `node --check .opencode/lib/session-utils.js` | pass — exit 0 |
| delivery-cli-full | `python -B research/verify_delivery.py`（8 items 全量） | pass — 8/8 PASS |
| diff-check | `git diff --check` | pass — 干净（task.json 已 LF 归一后） |
| scope-status | `python -B research/verify_delivery.py scope-status` | pass — git status 仅允许集合；模板无 `__pycache__`/`.pyc` |

### delivery-cli-full 明细

- `step-1-1-cli`：workdir=模板根运行模板自己的 `python ./.trellis/scripts/get_context.py --mode phase --step 1.1`，输出含 "Spec discovery (mandatory first evidence step)" 与 "## Spec References"（真实 CLI 送达，非纯文本断言）。
- `gate-text-sync`：两个 state 块的 Spec References + curated entry 句、1.4 拒绝枚举、1.5 表行、start.md planning 分支穷举句。
- `forbidden-zones`：`git diff -U0` 中无任何禁触字面量（no_task 块、Phase-2 Guardrail 条目、Loading Step Detail、Step detail 提示串、`--step 1` 弃用守卫文案、2.1.x 合同、`--platform opencode` 示例行）。
- `adapter-parity`：两份 adapter SKILL 字节相等（frontmatter 亦未动）。
- `skill-gate-text`：brainstorm + adapters 均含发现程序与 Spec References；无 "only verifies the persisted convergence and approval markers" 残留；五级枚举保留。
- `hook-redline`：3 处 hook 文件均不含 `validate_planning_gate`；Specs 句各片段每文件恰 2 次（对应两个 planning 分支）。
- `gate-cli-smoke`：临时仓库端到端 `task.py start` —— 种子-only jsonl → 拒绝并报 `implement.jsonl`；缺 `## Spec References` → 拒绝并报 Spec References；就绪任务 → exit 0 且 status=in_progress（证明 cmd_start 的 repo_root 接线生效）。
- `scope-status`：实施后 git status ⊆ 基线 ∪ 模板清单 ∪ 任务目录；模板树无字节码缓存。

## 验收项映射（prd Acceptance Criteria）

1. 门禁 A：缺节/空节拒绝、≥1 条通过、既有 7 用例全绿 → `gate-module-tests`、`template-suite`。
2. 门禁 B：种子-only 拒绝、真实条目通过、无平台目录不因 jsonl 拒绝、未传 repo_root 跳过、损坏 JSON 行拒绝 → 同上（11 个新用例覆盖）。
3. step 1.1 真实 CLI 送达 → `step-1-1-cli`。
4. adapter 零差异、3 hook 双分支语义一致、门禁行为描述全部同步（state 块、1.4、1.5、adapter intro、brainstorm :170、start.md）→ `adapter-parity`、`hook-redline`、`gate-text-sync`、`skill-gate-text`。
5. 种子骨架：含 `## Spec References` 节头且无占位列表项 → `test_default_prd_skeleton_declares_empty_spec_references_section`。
6. 禁触区零改动 → `forbidden-zones`。
7. 模板套件全绿、根套件 154 OK、py_compile、node --check、git diff --check → `template-suite`、`root-suite`、`compile-all`、`node-check-final`、`diff-check`。
8. git status 范围自查 → `scope-status`（根目录零改动证明见下）。

## 根目录零改动证明

```text
git diff --name-only -- .trellis/scripts .agents .claude .codex .opencode AGENTS.md history VERSION migrations README.md docs
→ .opencode/package.json
```

唯一命中文件 `.opencode/package.json` 在实施前的 `research/scope-baseline.txt` 基线中（用户既有的依赖版本改动，非本任务产生）。除此之外，模板外改动仅为任务目录本身。

## 跳过项与未运行项

- `VERSION` / `history/` / manifest / `migrations/` / README / `docs/接入指南.md`：按 `templates-and-docs.md:18`、`overlay-upgrade.md:133` 归 v1.3 发布收尾任务，本任务有意未动（`not run`，非缺口）。
- 构建/硬件验证：`not applicable`（`validation.md:11`，本仓库无固件或硬件目标）。
- 模板 `__pycache__`（实施前即存在、被 `.gitignore` 忽略）：随 compile 检查一并清理为 0；若后续不带 `-B` 运行模板脚本会重新生成，安装器会拒绝缓存文件。

## 已知风险

- 根↔模板分叉扩大（planning_gate、gate 测试、workflow.md 三处、SKILL 两类、hook 3 处）：live 模板相对 manifest 漂移，安装/升级在 v1.3 发布收尾重生成资产前 fail closed（分支既有模式，prd Risks 已接受）。
- 本仓库自身工作流仍无校验 A/B（用户明确模板-only），根目录同类"规划不读 spec"事故仍可能重演；根侧回移需另开授权任务。
- 门禁只做结构校验，内容真实性由 review 兜底（与 adapter "门禁不能证明判断正确"哲学一致）。
- 任务目录 CRLF 处置：tracked 的 `task.json` 已 LF 归一（`git diff --check` 干净）；未跟踪的 `execution-plan.json` / `execution-events.jsonl` 由 CLI 生成，交付前已对任务目录全部 JSON/JSONL 做 LF 归一，避免后续提交引入 CRLF 尾随空白。