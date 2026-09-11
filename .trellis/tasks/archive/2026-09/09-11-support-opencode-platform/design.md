# OpenCode 平台接入技术设计

## 目标与架构边界

本设计在 `templates/embedded-c-overlay/` 内增加一个可独立安装的 `.opencode/`
平台闭包，使 OpenCode 主会话和原生 Research、Implement、Check 子代理消费当前
TrellisForge 模板已经建立的工作流合同。根目录自用 Trellis、上游 Trellis npm 包、
Channel provider、版本资产和安装器集成不属于本功能子任务的写入范围。

设计采用“共享状态机 + 平台适配层”结构：

```text
OpenCode chat.message / tool.execute.before / session.compacted
                         |
                         v
             .opencode/plugins/*.js
              |       |        |
              |       |        `-- 原生 Task 提示与上下文注入
              |       `----------- 逐轮 workflow-state
              `------------------- SessionStart 与 Shell 会话身份桥接
                         |
                         v
             .opencode/lib/*.js
          会话解析 / 上下文预算 / 材料化
                         |
                         v
       .trellis/scripts/*.py + .trellis/workflow.md
      任务指针 / 规划门禁 / schema 3 计划 / 审计事实源
                         |
                         v
       .opencode/agents/trellis-{research,implement,check}.md
```

JavaScript 插件不复制规划批准或执行计划状态机。即使插件关闭，`task.py start`
和 `plan.py` 仍必须 fail closed；插件只负责把当前会话身份、状态正文和已持久化
任务资料可靠地带入 OpenCode 原生交互。

## 平台资产闭包

OpenCode 作为第三个默认交付平台，不依赖目标仓库此前是否执行过
`trellis init --opencode`。模板新增以下受管资产：

| 路径 | 职责 | 来源策略 |
| --- | --- | --- |
| `.opencode/package.json` | 声明 `@opencode-ai/plugin` 运行依赖 | 以 Trellis 0.6.10 格式为起点 |
| `.opencode/lib/trellis-context.js` | 会话键、任务指针、JSONL/任务产物材料化、上下文预算 | 按模板会话隔离和上下文合同定制 |
| `.opencode/lib/session-utils.js` | 构造紧凑 SessionStart、任务状态和 Spec 索引 | 对齐模板当前 Phase Index 与 planning readiness |
| `.opencode/plugins/session-start.js` | 首轮持久注入、压缩后去重状态复位 | 保留 OpenCode 原生事件模型 |
| `.opencode/plugins/inject-workflow-state.js` | 每轮从 `workflow.md` 标签块注入状态 | 不维护第二份状态路由表 |
| `.opencode/plugins/inject-subagent-context.js` | Shell 身份桥接、Task 上下文解析和提示构造 | 对齐模板 Python Hook 合同 |
| `.opencode/agents/trellis-research.md` | 只读研究并仅写当前任务 `research/` | 使用 OpenCode `mode: subagent` 权限卡 |
| `.opencode/agents/trellis-implement.md` | schema 3 计划受管实施 | 使用模板 Implement Agent 合同重写 |
| `.opencode/agents/trellis-check.md` | 五级独立审查与有限机械修复 | 使用模板 review Skill/Check Agent 合同重写 |
| `.opencode/commands/trellis/{start,continue,finish-work}.md` | OpenCode 命令入口 | 路由到项目工作流和定制 Skill |
| `.opencode/skills/**` | OpenCode 直接发现的主工作流 Skills | 复制所需上游通用 Skill，并镜像模板定制 Skill |

`.opencode/` 的初始文件集合固定为 Trellis 0.6.10
`collectOpenCodeTemplates()` 返回的全部路径，而不是实施者按需挑选的子集；随后以
TrellisForge 当前合同重写相同路径，并补充项目定制资产。由此，通用 Skill 完整包含
`trellis-before-dev`、`trellis-brainstorm`、`trellis-break-loop`、
`trellis-check`、`trellis-update-spec`、`trellis-meta`、
`trellis-session-insight`、`trellis-spec-bootstrap` 和 `trellis-channel` 的全部引用文件。
项目定制层另外镜像 `grill-me`、
`__PROJECT_PREFIX__-trellis-grill-adapter`、
`__PROJECT_PREFIX__-trellis-review`、`trellis-finish-work` 和完整
`trellis-channel`；同名 `trellis-channel` 以模板定制版本覆盖上游版本。这个固定集合保证
主工作流、维护/Spec 辅助流程和命令引用都不依赖目标仓库旧 `.opencode/`。

Channel Skill 可在 OpenCode 中被发现，但其 worker provider 枚举仍准确保持
`claude|codex`；不得为了让 Skill 可见而声称支持 `--provider opencode`。

## 会话身份与任务隔离

### 统一键格式

OpenCode 插件从 Hook 输入的 `sessionID`/兼容字段生成
`opencode_<sanitized-session-id>`，与 Python
`active_task.resolve_context_key(..., platform="opencode")` 的结果一致。
若 OpenCode 直接导出 `OPENCODE_SESSION_ID`、`OPENCODE_SESSIONID` 或
`OPENCODE_RUN_ID`，Python CLI 也解析为同一键；`TRELLIS_CONTEXT_ID` 始终是
显式覆盖入口。

### Shell 桥接

OpenCode TUI 不保证把 session id 暴露给 Bash/Shell。`tool.execute.before`
只对 shell 工具命令前置当前 `TRELLIS_CONTEXT_ID`：Windows PowerShell 使用
`$env:TRELLIS_CONTEXT_ID = '<key>';`，POSIX/Git Bash 使用
`export TRELLIS_CONTEXT_ID='<key>';`。已经显式设置该变量的命令不重复注入。
这样 `task.py create|current|start|finish` 与 `plan.py` 都命中当前窗口的 session
文件，而不是依赖单会话猜测。

### Fail-closed 顺序

主会话状态读取只接受精确 session 指针；缺失指针时返回 `no_task`，存在其他
session 文件时返回歧义，不借用唯一旧文件。OpenCode Task 子代理解析任务的顺序为：

1. 父调用事件携带的精确 session 指针；
2. 派发提示首个有效 `Active task: <path>` 明示；
3. 仅对已确认的 pull-based 子代理，在运行目录中恰好只有一个 session 文件时兼容回退。

任何候选路径必须解析为当前工作区内存在的任务目录。Implement/Check 无法确定任务
时拒绝注入并要求报告；不得继续使用其他窗口的任务。Research 若无任务，只能进行
不落盘的通用查找或要求主会话补齐任务，不能猜测研究输出目录。

## 主会话工作流接入

`.trellis/workflow.md` 增加明确的 `[OpenCode]` 路由块，并把平台总述从
“仅 Claude/Codex”改为三平台原生路径。OpenCode 的 Phase 行为为：

- Phase 1 使用 OpenCode 可发现的 `trellis-brainstorm`、`grill-me` 和项目 grill
  adapter；复杂任务生成三份规划文档，原生子代理模式配置真实 JSONL 清单；
- `task.py start` 仍检查五级 `Review level`、Planning Convergence、
  `planning_ready`、`plan_approved` 和后续批准；
- Phase 2 主会话用 OpenCode 原生 Task 派发 Implement/Check，提示首行携带精确
  `Active task`，不经过 Trellis Channel worker；
- Phase 3 使用项目 review Skill、`trellis-update-spec`、用户批准的提交计划和
  定制 `trellis-finish-work`；Agent 永远无提交权限。

`get_context.py --mode phase --step <X.X> --platform opencode` 通过现有平台标签过滤
生成 OpenCode 专属步骤；无需修改 `workflow_phase.py` 的 Codex dispatch-mode 分支。

## 原生子代理与上下文合同

### 权限和递归防护

三个 Agent 都使用 OpenCode `mode: subagent`。Research 只能修改当前任务
`research/*.md`；Implement 可修改任务范围内交付文件但不得更改生命周期或执行 Git
提交类操作；Check 只可直接修复同时满足局部、机械、小型、确定和范围内的 finding。
所有角色都禁止再派发 `trellis-implement` 或 `trellis-check`，主会话是唯一调度者。

### 材料化顺序

Implement 上下文固定为：`implement.jsonl` 的 Spec/Research -> `prd.md` ->
可选 `design.md` -> 可选 `implement.md` -> 当前 `execution-plan.json` 状态和协议。
Check 使用相同顺序但读取 `check.jsonl`。每文件、每产物和总预算沿用模板
`context_injection` 配置；二进制、截断和预算耗尽都生成明确索引提示，Agent 必须按需
主动读取原文件。

自动注入以 `<!-- trellis-hook-injected -->` 标识。标识缺失、内容截断或状态过期时，
Agent 使用提示中的精确任务路径主动拉取，不将 Hook 可用性视为安全门禁。

### 提示规范化

OpenCode Implement 提示必须获得与 Python Hook 同一语义的保守规范化：保留目标、
范围、非目标、验收条件和显式验证命令；只在明确的 execution strategy 分区将逐项
扫描、逐处构建等碎片化编排改成批处理。为避免 Python/JavaScript 两套规则漂移，
OpenCode 插件通过子进程调用模板现有
`.trellis/scripts/common/subagent_prompt_policy.py --json`。该入口从 stdin 接收
`{"prompt": "...", "injected_context": "..."}`，在 stdout 返回
`normalized_prompt`、`execution_contract` 和 `policy_marker` 三个字符串；非对象输入、
字段类型错误或 JSON 无效时以非零状态退出并在 stderr 报告。JavaScript 不重新维护
规范化正则表。

规范化失败时使用原始业务提示加静态 `execution_contract()` 等价约束，显式记录降级，
不得丢失业务要求或静默把原始文本当作强制逐项工具顺序。

## 执行计划和验证合同

OpenCode Implement Agent 在任何产品/模板源文件写入前必须：

1. 读取或创建 schema 3 `execution-plan.json`；
2. 通过 `plan.py validate` 和批准；
3. 只用 `plan.py start|record|done|block|revise` 推进；
4. 每阶段按“批量读 -> 批量改 -> 批量检查 -> 记录全部声明检查 -> done”执行；
5. 唯一 `report` 阶段写 `final-report.md`，普通阶段只能使用 `minimal` 验证。

OpenCode 插件可以展示执行计划状态，但不代替 CLI 审计。静态检查、测试、目标构建、
实体硬件验证在报告中分别记为 `pass|fail|not run|not applicable`；只有真实执行的
声明检查可以 `plan.py record`，不为嵌入式 C 项目虚构 Web lint/typecheck。

## 五级审查与 finding 路由

OpenCode Check Agent 直接读取项目
`__PROJECT_PREFIX__-trellis-review` Skill，完整支持：

| Level | Scope | 独立轮次与结束条件 |
| --- | --- | --- |
| `light` | changed-scope | 主会话执行，不派 Check Agent |
| `standard` | affected-scope | 恰好一次独立审查；证据有效时不自动重派 |
| `reinforced` | affected-scope | 每批阻塞修复后 fresh reviewer，至最新报告零阻塞 |
| `comprehensive` | full-scope | 同上；零阻塞后无额外 commit-ready 轮次 |
| `strict` | full-scope | 实施闭环后，对稳定快照执行 fresh commit-ready 终审至零 |

报告包含 level、scope、round、stage、blocking count、fixed/not-fixed findings、
责任去向、验收证据、验证、未运行项和剩余风险。Check Agent 不派发或续接 Implement
Agent；规划缺陷返回 Phase 1，越界/环境问题只报告，其余非机械实现阻塞返回主会话。
修复所有权不改变 profile 决定的独立性、范围和轮次。

## 本任务审查执行配置

本任务自身使用 `Review level: strict`，但采用用户明确指定的任务级调度例外：

- 实施完成后派发独立 full-scope Check Agent，覆盖完整任务 diff、受影响工具层、适用
  Spec、跨平台合同、测试和全部验收条件；
- 每批阻塞 finding 修复后，新派 fresh Check Agent 重新执行完整 full-scope 审查，直到
  最新独立报告的阻塞数为零；
- 任务变更集、公共合同、验收条件或适用 Spec 实质变化时，既有证据失效并重新进入
  full-scope 审查闭环；
- 进入提交准备时不追加额外的 commit-ready final review，也不因省略该轮而降低前述
  implementation-loop 的范围、独立性或零阻塞要求。

该例外只控制当前任务的审查调度。交付给下游的五级 profile 仍必须保持标准
`strict` 合同，包括其 commit-ready fresh full-scope 终审；不得修改
`templates/embedded-c-overlay/` 中的 Review Skill、workflow、Agent 或测试来固化本任务
例外。每次审查派发提示和最终报告都必须显式记录该例外及未执行额外终审的依据。

## 文件修改面

| 文件或目录 | 设计改动 |
| --- | --- |
| `templates/embedded-c-overlay/.opencode/**` | 新增完整 OpenCode 原生平台闭包 |
| `templates/embedded-c-overlay/.trellis/workflow.md` | 增加 OpenCode 路由、原生 Task 调度和三平台表述 |
| `templates/embedded-c-overlay/.trellis/scripts/common/subagent_prompt_policy.py` | 增加 `--json` stdin/stdout 桥接入口，不改变现有 Python 调用语义 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_opencode_platform_contract.py` | 新增平台闭包、JS 行为、会话、上下文和工作流合同测试 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_active_task_session_isolation.py` | 增加 OpenCode 键一致性和多会话 fail-closed 用例 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_subagent_prompt_contract.py` | 将 OpenCode 纳入提示保真/批处理矩阵 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_profile_contract.py` | 将 OpenCode Check Agent 纳入五级审查矩阵 |
| `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_fix_ownership_contract.py` | 将 OpenCode finding 路由纳入矩阵 |
| `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` | 登记 `.opencode/` 交付内容和边界 |
| `templates/embedded-c-overlay/AGENTS.md.template` | 将 OpenCode 原生 Agent/Skill 位置写入下游说明 |

现有 `.claude/`、`.codex/` 和公共 Channel runtime 只在测试中作为对照，不为接入
OpenCode 而改写其行为。若合约测试暴露原有平台陈旧的“两平台”枚举，只修改真正拥有
跨平台公共表述的模板文件，不顺带重构平台实现。

## 测试设计

1. 平台闭包测试断言 `.opencode/` 的 package、lib、三个插件、三个 Agent、命令和
   必需 Skill 全部存在，且 Agent frontmatter/权限符合角色边界。
2. Node 语法检查对每个 `.opencode/**/*.js` 执行 `node --check`；JSON 使用结构化
   解析。运行时行为测试通过临时 Trellis 仓库和 Node 小型 harness 调用 lib/插件，
   不启动真实 OpenCode 网络会话。
3. 会话测试覆盖精确 session、两个并行 session、陈旧任务、歧义状态、PowerShell/
   POSIX Shell 前缀和已有 `TRELLIS_CONTEXT_ID` 不重复注入。
4. 状态测试覆盖 `no_task|planning|in_progress|completed|stale`，并证明正文只来自
   `workflow.md` 标签块。
5. 子代理测试覆盖 Task 类型识别、递归跳过、上下文顺序、预算/截断、任务提示明示、
   schema 3 协议和无 Hook 主动读取回退。
6. 提示测试用同一中英文样例比较 Python 与 OpenCode 路径：验收/命令逐字保留，
   execution strategy 中碎片化步骤被批处理。
7. review/ownership 测试把 OpenCode 与 Claude、Codex、Channel 一并断言五级集合、
   scope/轮次、fresh reviewer、strict 终审和 finding 路由。
8. 全量运行模板 Python 单测、根目录只读回归、Python 语法检查、OpenCode JS/JSON
   语法检查、旧三档/两平台残留扫描和 `git diff --check`。

## 兼容性、发布和回滚

- OpenCode 新增文件不会改变现有 Claude Code、Codex 或 Channel provider 选择；
  `.trellis/scripts/common/active_task.py` 已识别 OpenCode 环境键。
- `.opencode/package.json` 进入默认模板后，父任务收尾必须把它纳入安装冲突预检、
  Git 元数据备份、回滚清单、canonical 对象、1.2 manifest 和升级结构链。
- 本子任务完成到父任务收尾前，live 模板与 1.1 manifest 暂时不一致是已知开发态；
  不运行要求二者一致的发布资产生成作为本子任务验收。
- OpenCode 插件逐个独立，可按 SessionStart、workflow-state、Task/Shell 桥接三个批次
  定位回滚；回滚只撤销本任务新增/修改的模板文件，不重置用户工作树。
- `trellis channel spawn --provider opencode` 和 OpenCode `trellis mem` reader 保持延期，
  相关命令文档必须继续准确披露限制。

## 已决工程决策

- 复用上游 0.6.10 的 OpenCode 文件格式和事件 API，不复用其过时业务文案。
- 共享 Python 脚本承担可执行门禁，JavaScript 插件只做适配和上下文传递。
- `.opencode/` 作为默认完整闭包交付，不根据目标仓库已有目录条件裁剪。
- 通过现有 Python prompt policy 的受控入口复用规范化语义，不复制正则规则。
- 用合同/行为测试证明平台等价，不要求不同语言实现逐字节相同。
- OpenCode 原生 Task 是主工作流子代理路径；Channel 受管 OpenCode worker 不进入设计。
- 本任务的 strict 无 commit-ready 终审是一次性调度例外，不成为产品设计或 Spec。
