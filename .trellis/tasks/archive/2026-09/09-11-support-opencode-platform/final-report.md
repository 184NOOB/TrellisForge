# Final Report — 支持 OpenCode 平台(09-11-support-opencode-platform)

审查调度说明:本任务按用户指定的一次性例外执行 `strict` 实施闭环 —— 实施后独立
full-scope Check 审查、每批阻塞修复后 fresh 重审至零阻塞,但**不追加额外
commit-ready final review**。该例外只影响本任务的调度,未写入下游模板:交付给
下游的 `strict` 合同(含 commit-ready fresh 终审)在模板 Review Skill、workflow
与测试中保持完整。构建/部署/实体硬件验证对 TrellisForge 仓库本身为
`not applicable`(本仓库不产出固件、可执行产品或硬件目标)。

## 变更文件清单

### 新增 — `templates/embedded-c-overlay/.opencode/`(59 个受管文件)

- `package.json` — 声明 `@opencode-ai/plugin ^1.14.39`(与上游 0.6.10 兼容的依赖声明)
- `lib/trellis-context.js` — 会话键(与 Python `active_task` 逐向量一致)、主会话
  fail-closed 精确解析(exact/none/ambiguous,绝不借用)、子代理三级解析
  (精确 session → `Active task:` 明示(允许含空格路径、限工作区内已存在目录)→
  受限唯一 session 回退)、工作区边界检查、JSONL 结构化解析与上下文材料化
  (per-file/per-artifact/total 预算、UTF-8 安全截断、与 Python hook 字节一致的
  notice 文案)、`isTrellisSubagent`
- `lib/session-utils.js` — 模板措辞的紧凑 SessionStart(current-state / Phase Index
  剥离 workflow-state 与平台标记 / guidelines / task-status,含 planning readiness
  与歧义显式报告)、`no-trellis` 跳过词解析、workflow.md 标签块面包屑构建、
  PowerShell 与 POSIX/Git-Bash 的 `TRELLIS_CONTEXT_ID` 前缀桥(已显式设置不重复注入)、
  `plan_breadcrumb`/`plan_protocol_block` Python 子进程桥(跨平台同文)、
  `normalizePromptViaPython`(`--json` 桥)、`STATIC_EXECUTION_CONTRACT`/
  `STATIC_POLICY_MARKER` 降级常量(与 Python 字面相等,由测试锁定)
- `plugins/session-start.js` — 首轮持久注入 + metadata/history 双去重、
  `session.compacted` 复位;子代理 turn、`TRELLIS_HOOKS=0`、`TRELLIS_DISABLE_HOOKS=1`、
  `OPENCODE_NON_INTERACTIVE=1`、非 Trellis 目录均静默跳过;仅一个 default export
- `plugins/inject-workflow-state.js` — 逐轮状态正文只来自 `[workflow-state:STATUS]`
  标签块(缺失显式降级,无第二路由表);stale → `stale_session`(与 Python hook 一致);
  歧义附 `<workflow-ambiguity>` 显式报告;追加展示用 `<execution-plan>`(Python 桥渲染)
- `plugins/inject-subagent-context.js` — shell 工具身份桥(bash/shell,command/cmd);
  Task 工具只识别三个 trellis-* 代理;按模板合同注入 implement/check/research 上下文
  (check 无计划协议块 = Python hook 平价);无法解析任务的 Implement/Check **阻断注入**
  并注入"停止并报告"说明(不伪造上下文);经 Python `--json` 桥做提示规范化,
  桥失败时保留业务原文 + 静态合同 + 显式降级说明
- `agents/trellis-{research,implement,check}.md` — `mode: subagent` + `task: deny`;
  递归防护、marker 主动拉取协议、blocked-note 处理;implement 含 schema 3 执行计划
  状态机与批量执行批次;check 含五级 profile、direct-fix 边界、finding 路由
  (OpenCode 无 resume 路径,非机械实现阻塞返回主会话)、统一报告字段、禁提交;
  research 只写当前任务 `research/`,无任务不落盘
- `commands/trellis/{start,continue,finish-work}.md` — 仅路由:`--platform opencode`
  步骤加载、五级 `Review level` 与 Planning Convergence/后续批准门禁提示、
  finish-work 指向项目定制 Skill(提交属 Phase 3.4)
- `skills/`(47 个文件)— 上游 collector 通用闭包:trellis-before-dev、
  trellis-brainstorm、trellis-break-loop、trellis-update-spec、trellis-meta、
  trellis-session-insight、trellis-spec-bootstrap(全部引用文件);
  重写 `trellis-check/SKILL.md` 为五级审查合同版本(路由到
  `PROJECT_PREFIX-trellis-review`,嵌入式 C 验证分类,无 Web-lint/宽泛自修复);
  镜像模板定制(与 `.agents/skills/` 源逐字节一致):`grill-me`、
  `__PROJECT_PREFIX__-trellis-grill-adapter`、`__PROJECT_PREFIX__-trellis-review`、
  `trellis-finish-work`、完整定制 `trellis-channel`(覆盖同名上游,provider 保持
  `claude|codex`)

### 修改 — 模板公共层

- `templates/embedded-c-overlay/.trellis/scripts/common/subagent_prompt_policy.py`
  — 新增 `--json` stdin/stdout 桥(严格校验输入,非法一律非零退出)与 direct-run
  时的 sys.path 防遮蔽引导;import 语义与既有 Python 调用方完全不变(测试锁定)
- `templates/embedded-c-overlay/.trellis/workflow.md` — 子代理派发协议改为
  Claude Code / Codex / OpenCode 三平台并声明 OpenCode 原生 Task 路径与
  `--provider opencode` 不支持;`[OpenCode]` Active Task Routing 块;1.3/1.5/2.1/2.2/
  1.2 平台标记扩为含 OpenCode;breadcrumb 合同注释、hooks/plugins 展示层表述同步
- `templates/embedded-c-overlay/.trellis/scripts/tests/test_opencode_platform_contract.py`(新增)
  — 闭包完整性(含与本机 collector 的路径奇偶校验)、default-only export、
  package.json、Agent frontmatter、命令仅路由、镜像逐字节一致、Channel provider 限制、
  全树旧语义扫描、Node 运行时合同(顺序/规范化平价/fail-closed/桥接/去重)
- `test_active_task_session_isolation.py` — OpenCode 键矩阵 + Python↔JS 固定向量
  跨语言一致 + 主会话 exact/none/ambiguous 与受限回退矩阵
- `test_subagent_prompt_contract.py` — `--json` 桥与 import API 逐字平价、非法输入拒绝、
  usage、JS 静态降级常量与 Python 字面相等、JS check prompt Finding-handling 与
  Claude/Codex hook 三方归一化逐字相等
- `test_review_profile_contract.py` — OpenCode Check Agent 与 review Skill 镜像加入
  LEVEL_CONSUMERS/CHECK_AGENTS;镜像逐字节一致;五级 profile 矩阵断言
- `test_review_fix_ownership_contract.py` — OpenCode Check Agent 与插件加入
  MANAGED_FILES 与 check-agent 矩阵(direct-fix/report-only/never-dispatch/
  never-schedules/旧措辞禁用)
- `TEMPLATE-CONTENTS.md`、`AGENTS.md.template` — 登记 `.opencode/` 闭包、新测试文件、
  三平台表述与 OpenCode 位置/provider 限制
- `.trellis/tasks/09-11-support-opencode-platform/task.json` — `status` 由
  `planning` → `in_progress`(task.py start 的状态迁移),`meta.plan_approved` 由
  `false` → `true`(计划后续批准),并归一 CRLF→LF + 恢复尾换行(此前 task.py 在
  Windows 以文本模式重写导致 `git diff --check` 全文件误报);
  执行计划状态文件 `execution-plan.json`/`execution-events.jsonl` 由 plan.py 推进

## 阶段执行结果

| 阶段 | 检查 | 结果 |
|---|---|---|
| closure-lib | js-syntax-lib; lib-node-harness(42 断言:键向量、fail-closed、Shell 桥、预算 notice、面包屑、任务状态) | pass / pass |
| plugins-policy-bridge | js-syntax-plugins(含 default-only export 探针); policy-json-roundtrip(24 项插件行为 + 桥 4 路); py-compile-policy | pass ×3 |
| agents | agents-contract-scan(三代理 frontmatter/合同断言) | pass |
| commands-skills | closure-completeness(55 collector 路径 0 缺失 + 镜像逐字节); skills-stale-scan(0 旧语义命中) | pass ×2 |
| workflow-manifests | phase-opencode-output(1.1–3.4 三平台对照、Codex 终端编排不泄漏、provider-opencode 不出现); two-platform-residual-scan | pass ×2 |
| tests | focused-opencode-tests:opencode 13/13(0 skip,Node 真实执行)、isolation 6/6、prompt 22/22、profile 15/15、ownership 11/11 | pass |
| verify | template-unittests 154/154 OK; root-regression 99/99 OK(只读); py-syntax; js-json-syntax; residual-scan; forbidden-paths-clean(禁止路径为空); git-diff-check(tree+cached 干净) | pass ×7 |

## AC 证据映射

- **AC1 pass** — `git status --short -- .trellis/workflow.md .agents .claude .codex
  VERSION README.md docs history migrations tools` 为空;全部功能改动位于
  `templates/embedded-c-overlay/` 与本任务资料。
- **AC2 pass** — `.opencode/` 59 文件闭包(package/lib/plugins/agents/commands/skills)
  全部在模板内自包含;collector 路径奇偶测试 + 必备根断言;不依赖目标仓库已有
  `.opencode/`。
- **AC3 pass** — workflow-state 插件从标签块读取 no_task/planning/in_progress/
  completed(运行时 harness 以唯一 fixture 正文证明来源);start/continue 命令与
  workflow `[OpenCode]` 路由保留 task.py start 的收敛+后续批准门禁;执行计划门禁由
  plan.py 承担且代理合同强制。
- **AC4 pass** — 全树旧枚举扫描 0 命中;check 代理/插件/命令/bundled check Skill
  均完整枚举五级;`reinforced`/`comprehensive` 语义与 review Skill 镜像逐字一致。
- **AC5 pass** — 并行双 session:主会话 exact 命中各自指针、无指针精确键 → no_task、
  无身份 → ambiguous 借用禁止;子代理 hint 优先、越界 hint 拒绝、双文件禁回退;
  Shell 桥 PowerShell/POSIX/已显式设置三态覆盖(全部由 Node 真实执行)。
- **AC6 pass** — 三代理职责/上下文/递归/写入与提交边界/计划与报告语义与模板
  Claude/Codex 合同对齐;Finding-handling 三方(Claude/Codex hook 与 JS 插件)归一化
  后逐字相等;上下文顺序 jsonl→prd→design→implement→plan-protocol 由运行时断言。
- **AC7 pass** — check 代理与 review Skill 镜像锁定 changed/affected/full scope、
  独立轮次、fresh reviewer、证据失效、strict commit-ready 终审文本;OpenCode 检查项
  加入 CHECK_AGENTS 矩阵(test_review_profile_contract 15 项)。
- **AC8 pass** — direct-fix/report-only/never-dispatch/ownership-不排审查轮锚点
  在 OpenCode 代理、插件、workflow、review Skill 镜像全部通过
  test_review_fix_ownership_contract(11 项);插件 fail-closed 阻断不新增轮次。
- **AC9 pass** — Implement 提示经 Python 桥规范化(中英文样例与 import API 输出逐字
  相等,碎片化执行策略被批量化、验收/命令逐字保留);代理含批量执行批次合同;
  桥失败显式降级不丢业务要求。
- **AC10 pass** — 计划协议块注入 implement 上下文(与 hook 同源 Python 渲染);
  两级验证与 report/final-report.md 合同写入代理;报告分类 pass/fail/not run/
  not applicable 且无 Web 检查假设;提交授权与定制 finish-work 路由在命令与
  workflow 中保持;插件文档明确"非门禁"。
- **AC11 pass** — 平台矩阵扩展至 OpenCode 后,模板全部 154 项单测(含 Claude/Codex/
  Channel 合同与执行计划/规划门禁)与根目录 99 项回归全部通过,无回归。
- **AC12 pass** — 聚焦测试、模板全量、根回归、py_compile、node --check、JSON 解析、
  残留/缓存扫描、`git diff --check`(含换行归一说明)全部通过;构建/部署/硬件
  验证:not applicable(TrellisForge 无产品构建目标)。
- **AC13 交接材料见下节** — 发布资产(VERSION、README、接入指南、canonical 对象、
  1.2 manifest、结构迁移链、安装/升级补丁)未由本任务改动,符合边界。

## 未运行项 / 已知风险

- 真实 OpenCode CLI/TUI 端到端会话:不在本环境能力内(测试以事件对象模拟 +
  Node 真实执行 lib/插件,未启动网络模型会话;Python 未伪装执行 JS)。
- `trellis channel spawn --provider opencode` 与 OpenCode `trellis mem` 读取器:
  明确延后,文档保持 `claude|codex` 准确枚举。
- live 模板新增 `.opencode/` 与 1.1 manifest 暂时漂移:1.2 版本开发期已知状态,
  由父任务固定收尾子任务恢复一致性。
- 上游通用 Skill(如 trellis-meta/break-loop)保留上游描述性文案(含泛化示例);
  已确认不含可执行的旧三档/lint 假设;若收尾审查认为需要进一步本地化,属新范围。

## 父任务收尾子任务交接清单(09-10-readme-integration-guide-upgrade-patch)

1. **新增受管路径(全部 `managed`,需进入 1.2 manifest + canonical 对象)**:
   `templates/embedded-c-overlay/.opencode/` 下 59 个文件(清单:`git status
   --porcelain` 的 `?? templates/embedded-c-overlay/.opencode/` 展开;55 个与上游
   collector 路径同名,另 4 个为定制镜像:`skills/grill-me/SKILL.md`、
   `skills/__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md`、
   `skills/__PROJECT_PREFIX__-trellis-review/SKILL.md`、
   `skills/trellis-finish-work/SKILL.md`)。路径含 `__PROJECT_PREFIX__` token 的
   目录名(仅 `__PROJECT_PREFIX__-trellis-grill-adapter/` 与
   `__PROJECT_PREFIX__-trellis-review/`)需要安装器按 path-token 规则渲染。
2. **修改的既有受管路径(三方合并 old 来自 1.1 canonical)**:
   `.trellis/workflow.md`、`.trellis/scripts/common/subagent_prompt_policy.py`、
   `.trellis/scripts/tests/test_{active_task_session_isolation,subagent_prompt_contract,review_profile_contract,review_fix_ownership_contract}.py`、
   `TEMPLATE-CONTENTS.md`、`AGENTS.md.template`。
3. **新增测试文件(1.2 `add`)**:`.trellis/scripts/tests/test_opencode_platform_contract.py`。
4. **结构迁移**:`.opencode/` 为 1.2 新增目录,建议在
   `migrations/embedded-c-overlay/structural/1.1-to-1.2.json` 中以目录级新增动作
   表达(与现有 add 动作白名单一致);安装冲突预检需覆盖已有 `.opencode/` 的
   目标仓库(可能来自用户自行 `trellis init --opencode`),按既有备份/合并规则处理。
5. **运行时依赖**:`.opencode/package.json` 要求目标机器可解析
   `@opencode-ai/plugin ^1.14.39`;插件同时依赖模板 Python(桥接
   `subagent_prompt_policy.py --json`、`execution_plan` 展示、`get_context.py
   --mode packages --json`)——接入指南需说明 OpenCode 会话要求 `node` 可用
   (插件)与 `python`(门禁与桥),缺失时插件按合同静默降级、CLI 门禁仍 fail closed。
6. **文档要点**:OpenCode 为第三默认平台、原生子代理闭包完整;`trellis channel`
   worker provider 仍仅 `claude|codex`;OpenCode `trellis mem` 会话读取器受上游
   限制保持降级,不承诺。
7. 本任务未触碰 `VERSION`、README、`docs/接入指南.md`、`history/`、`migrations/`、
   `tools/` 与根目录自用工作流文件。
