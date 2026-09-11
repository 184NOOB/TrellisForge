# OpenCode 平台接入实施计划

## 实施前条件

- [ ] 用户已在本轮最终规划摘要之后明确批准开始实施；批准前不得运行
  `task.py start` 或修改 `templates/embedded-c-overlay/` 产品模板。
- [ ] 当前会话仍以精确 `session:*` 指针绑定本任务，且状态为 `planning`；启动成功后
  才进入 `in_progress`。
- [ ] 读取 `prd.md`、`design.md`、本文件以及 `implement.jsonl` / `check.jsonl`
  中列出的 Spec；不得只读 Spec 索引便开始实施。
- [ ] 审查调度读取并保留任务级例外：使用 strict full-scope implementation-loop 和
  每批阻塞修复后的 fresh re-review，但不追加 commit-ready final review。
- [ ] 用 `git status --short` 记录父任务和用户现有改动，功能写入仅限
  `templates/embedded-c-overlay/` 与本任务资料。
- [ ] 确认根目录自用 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、README、
  `docs/`、`VERSION`、`history/`、`migrations/` 和安装/升级脚本不在本子任务写入范围。

## 实施批次

### 1. 固化 OpenCode 平台闭包和基线

- [ ] 从本机 `@mindfoldhq/trellis@0.6.10` 的 OpenCode collector 枚举并导入其返回的
  全部 package、lib、plugins、agents、commands 和 skills 路径；逐项记录直接复用的
  平台格式和必须用当前模板合同重写的正文。
- [ ] 在 `templates/embedded-c-overlay/.opencode/` 建立完整目录树；不得从目标仓库
  条件探测或假定已有 `trellis init --opencode` 产物。
- [ ] 保持插件模块只有一个 default factory export，避免 OpenCode 1.2.x 把额外命名
  export 当作插件 factory 调用；可测试的纯函数放入 `.opencode/lib/`。
- [ ] 添加 `.opencode/package.json`，锁定与上游 0.6.10 兼容的
  `@opencode-ai/plugin` 依赖声明，不引入仓库根 Node 构建系统。

### 2. 实现共享 OpenCode 上下文库

- [ ] 实现 `lib/trellis-context.js` 的 repo 发现、session key 规范化、任务 ref 规范化、
  精确 session 读取、受限子代理回退和工作区边界检查。
- [ ] 实现 JSONL 结构化解析和上下文材料化，保持 Spec/Research -> PRD -> design ->
  implement -> execution-plan 的顺序，并对二进制、单文件上限、产物上限和总预算输出
  可恢复提示。
- [ ] 实现 `lib/session-utils.js`，从真实 `.trellis/workflow.md`、task.json、Spec 索引和
 任务状态构造紧凑 SessionStart；planning 状态准确反映三份规划产物及 JSONL readiness。
- [ ] 在纯 lib 中提供 Shell 环境前缀和插件所需的可测试辅助函数；Windows PowerShell、
  POSIX/Git Bash 和已经显式设置变量的输入分别覆盖。

### 3. 接入 SessionStart 和逐轮状态

- [ ] 新增 `plugins/session-start.js`，在主会话首次 `chat.message` 持久注入紧凑上下文，
  通过 metadata 和会话历史去重，并在 `session.compacted` 后允许恢复注入。
- [ ] 子代理 turn 不注入主会话 SessionStart；`TRELLIS_HOOKS=0`、
  `TRELLIS_DISABLE_HOOKS=1` 和非交互模式沿用静默禁用合同。
- [ ] 新增 `plugins/inject-workflow-state.js`，每轮只从 workflow 标签块读取
  `no_task|planning|planning-inline|in_progress|completed` 正文，缺失标签时显式降级，
  不写硬编码业务路由表。
- [ ] 实现 `no-trellis` 独立词跳过规则，并确保子代理 turn 不收到主会话 breadcrumb。

### 4. 实现 Shell 身份桥接和原生 Task 上下文注入

- [ ] 新增 `plugins/inject-subagent-context.js`；对 shell 工具注入与当前 Hook
  `sessionID` 对应的 `TRELLIS_CONTEXT_ID`，不覆盖调用方已有显式值。
- [ ] 对 Task 工具只识别 `trellis-research|trellis-implement|trellis-check`，按“精确
  session -> Active task 明示 -> 受限唯一 session 回退”解析任务，并验证路径存在且
  位于工作区。
- [ ] Implement/Check 无法解析任务时 fail closed；Research 输出需要任务目录时同样
  不得猜测。插件异常不能伪造成功上下文。
- [ ] 注入 implement/check JSONL、规划产物、当前 schema 3 计划状态和 Agent 执行协议；
  保留主动读取 fallback，使插件关闭或上下文截断时仍可从任务文件恢复。
- [ ] 为 Python `subagent_prompt_policy.py` 增加 `--json` stdin/stdout 入口，严格校验
  `prompt` / `injected_context` 并返回 normalized prompt、execution contract 和 marker；
  原有 import 调用行为保持不变。
- [ ] OpenCode 插件通过 `execFileSync` 调用该 JSON 入口；保留业务要求，只批量化
  execution strategy。进程失败、超时或返回无效时，保留原文并附加 lib 中固定的静态
  执行合同及降级说明。

### 5. 重写三个 OpenCode 原生 Agent

- [ ] `trellis-research.md`：限制写入当前任务 `research/`，禁止产品/Spec/平台文件修改
  和 Git 操作；无明确任务时停止落盘。
- [ ] `trellis-implement.md`：加入递归防护、上下文主动拉取、schema 3 计划创建/批准/
  推进、批量工具纪律、嵌入式 C 验证分类、变更范围和禁止提交边界。
- [ ] `trellis-check.md`：读取项目 review Skill，支持五级 scope/round/stage/fresh
  reviewer/证据失效合同，并使用统一审查报告字段。
- [ ] Check 只机械直修；规划缺陷返回 Phase 1，越界/环境阻塞只报告，非机械实现阻塞
  返回主会话。不得自行派发或续接 Implement Agent。
- [ ] 三个 Agent 的 OpenCode frontmatter 使用最小角色权限；权限声明不能反向放宽正文
  写入边界。

### 6. 交付 OpenCode 命令和 Skills

- [ ] 添加 `trellis/start`、`trellis/continue`、`trellis/finish-work` 命令；命令只做路由，
  分别指向 Phase Index/具体步骤和项目定制 finish Skill，不复制陈旧流程。
- [ ] 将 collector 返回的 `trellis-before-dev`、`trellis-brainstorm`、
  `trellis-break-loop`、`trellis-check`、`trellis-update-spec`、`trellis-meta`、
  `trellis-session-insight`、`trellis-spec-bootstrap`、`trellis-channel` 完整目录树落入
  `.opencode/skills/`。
- [ ] 将模板定制的 grill、grill adapter、review、finish-work、Channel Skill 镜像到
  OpenCode；同名 Channel Skill 使用模板定制内容覆盖上游内容。
- [ ] 检查 `__PROJECT_PREFIX__` 占位符在路径和正文中保持与安装器渲染约定一致；不得
  引入未经渲染的通用 `<PROJECT_...>` 标记。
- [ ] Channel 文档仍明确 provider 仅为 Claude/Codex；OpenCode 可以调用 Channel CLI
  通用功能，但没有受管 OpenCode worker。

### 7. 更新公共 workflow 和模板清单

- [ ] 在 `.trellis/workflow.md` 增加 `[OpenCode]` Phase 1/2/3 路由，规定主会话用原生
  Task 派发且首行包含 `Active task: <path>`。
- [ ] 把“子代理协议仅适用于 Claude/Codex”等陈旧公共断言改为包含 OpenCode；保持
  Codex inline、Codex Channel 唯一 wait 和 Claude 特有 Hook 规则的作用域不变。
- [ ] 确保 `--platform opencode` 的 1.1、2.1、2.2、3.3、3.4 输出包含正确平台步骤，
  不泄漏 Codex 终端编排或不存在的 OpenCode worker provider。
- [ ] 更新 `TEMPLATE-CONTENTS.md` 登记 OpenCode 资产闭包，更新
  `AGENTS.md.template` 的 OpenCode agents/skills 位置；不修改 README 或接入指南。

### 8. 增加 OpenCode 平台行为测试

- [ ] 新增 `test_opencode_platform_contract.py`，断言资产闭包、default-only 插件 export、
  package JSON、Agent frontmatter、命令路由、Skill 树和 Channel provider 限制。
- [ ] 使用临时仓库 + Node harness 验证精确/并行/陈旧/歧义 session、Shell 桥接、
  SessionStart 去重/compaction、逐轮状态来源和子代理上下文顺序。
- [ ] 扩展 `test_active_task_session_isolation.py`，证明 Python OpenCode session key 与 JS
  适配层一致，主会话不借用旧 session。
- [ ] 扩展 `test_subagent_prompt_contract.py`，使用相同中英文样例证明 OpenCode 路径与
  Python 路径均保留目标/验收/命令并批量化 execution strategy。
- [ ] 扩展 `test_review_profile_contract.py` 和
  `test_review_fix_ownership_contract.py`，将 OpenCode Check Agent/插件提示纳入
  五级审查和 finding 路由矩阵。
- [ ] 测试只模拟 OpenCode 事件对象，不启动真实网络模型；Node 不可用时相关运行时测试
  必须明确 skip，不能由 Python 测试伪装为已经执行 JavaScript。

### 9. 分层验证

- [ ] 先运行 OpenCode 聚焦测试：

  ```powershell
  @(
    "test_opencode_platform_contract.py",
    "test_active_task_session_isolation.py",
    "test_subagent_prompt_contract.py",
    "test_review_profile_contract.py",
    "test_review_fix_ownership_contract.py"
  ) | ForEach-Object {
    python -B (Join-Path "templates/embedded-c-overlay/.trellis/scripts/tests" $_)
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
  }
  ```

- [ ] 运行模板全部 Python 单测：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 运行根目录自用 Trellis 回归测试（只读验证）：

  ```powershell
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 检查模板 Python 文件语法：

  ```powershell
  Get-ChildItem templates/embedded-c-overlay/.trellis/scripts,templates/embedded-c-overlay/.claude/hooks,templates/embedded-c-overlay/.codex/hooks -Recurse -Filter *.py -File |
    ForEach-Object { python -m py_compile $_.FullName }
  ```

- [ ] 检查 OpenCode JavaScript 和 JSON 语法：

  ```powershell
  Get-ChildItem templates/embedded-c-overlay/.opencode -Recurse -Filter *.js -File |
    ForEach-Object { node --check $_.FullName }
  Get-Content -Raw templates/embedded-c-overlay/.opencode/package.json | ConvertFrom-Json | Out-Null
  ```

- [ ] 扫描三档/两平台陈旧断言、未知占位符和模板缓存：

  ```powershell
  rg --hidden -n -i "only.*claude.*codex|light.*standard.*strict" templates/embedded-c-overlay
  Get-ChildItem templates/embedded-c-overlay -Recurse -Force |
    Where-Object { $_.Name -match '(__pycache__|\.pyc$|\.pyo$)' }
  ```

- [ ] 确认禁止范围无功能改动，并执行补丁检查：

  ```powershell
  git status --short -- .trellis/workflow.md .agents .claude .codex VERSION README.md docs history migrations tools
  git diff --check
  ```

- [ ] 构建、部署和硬件验证记录为 `not applicable`：TrellisForge 仓库不产出固件、
  可执行产品或硬件目标；不得将模板中的示例命令报告为本仓库已执行验证。

### 10. 审查与父任务交接

- [ ] 按本任务定制的 `Review level: strict` 派发独立 full-scope implementation-loop
  Check Agent；覆盖完整任务 diff、OpenCode JS 行为、模板 Python 公共合同、五级审查、
  任务隔离、提示规范化、全部 AC 和适用 Spec。
- [ ] 批量处理机械 finding 和返回主会话的实施 finding；每批阻塞 finding 修复完成后，
  新派 fresh Check Agent 重新执行完整 full-scope 审查，直到最新独立报告为零阻塞。
- [ ] 若任务范围、公共合同、验收条件或适用 Spec 实质变化，则按 evidence invalidation
  重新执行 full-scope 审查。
- [ ] 当前任务不执行额外 commit-ready final review；每次审查派发提示和最终报告都明确
  这是用户指定的一次性任务例外，不修改或弱化发布模板中的 `strict` 契约。
- [ ] 最终 `final-report.md` 按 AC1-AC13 映射证据，分别列出测试、静态检查、JS/JSON
  语法、构建/部署/硬件不适用、未运行项和剩余风险。
- [ ] 向父任务固定收尾子任务提供新增/修改模板文件清单、`.opencode/package.json` 依赖、
  受管路径和结构新增说明，供 1.2 manifest、canonical、迁移、安装/升级、README 和
  接入指南统一集成；本任务不提前修改这些资产。
- [ ] 未经用户另行批准提交计划，不执行 `git add`、`git commit`、推送、合并或历史重写。

## 风险点与回滚点

- 插件 export 形状、OpenCode 事件字段和 shell 工具参数是平台兼容高风险点；每个插件
  独立落地并通过 Node harness 后再进入下一批。
- Python 与 JavaScript session key 必须完全一致，否则任务创建成功但后续 prompt/Task
  会显示 `no_task`；用跨语言固定向量测试作为门禁。
- 提示规范化不得在 JavaScript 复制正则表；若桥接不可行，先保留业务原文并显式降级，
  不以不完整重写换取表面一致。
- `.opencode/skills/` 同时包含上游通用内容和 TrellisForge 定制内容，最容易出现旧三档、
  通用 Web lint 或自动提交文案；导入后必须逐文件按当前模板合同审计。
- `.opencode/` 是 1.2 新目录，父任务收尾前 manifest 漂移是已知状态；不得为通过旧 1.1
  发布校验而删除或隐瞒新文件。
- 若某批失败，只撤销本任务在该批引入的文件并回到上一个已验证状态；禁止整体重置工作树，
  禁止覆盖父任务或用户已有改动。
