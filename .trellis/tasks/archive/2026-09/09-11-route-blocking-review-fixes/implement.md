# 审查阻塞问题修复责任实施计划

## 实施前条件

- [ ] 用户已审阅并明确批准包含 `prd.md`、`design.md` 和本文件的最新完整规划摘要；批准前不得运行 `task.py start` 或修改发布模板。
- [ ] 当前任务仍由本会话精确 `session:*` 指针绑定，任务状态为 `planning`；启动后才进入 `in_progress`。
- [ ] 完成 Phase 1.3 上下文配置：`implement.jsonl` 与 `check.jsonl` 均包含真实的 Spec/Research 条目，不再是 seed-only。
- [ ] 实施前读取 PRD、设计、本计划、上下文清单及其中列出的 Spec/Research。
- [ ] 审查调度读取并保留任务级例外：使用 strict full-scope implementation-loop 和阻塞修复后的 fresh re-review，但不追加 commit-ready final review。
- [ ] 使用 `git status --short` 记录已有改动；功能写入仅允许位于 `templates/embedded-c-overlay/`，任务规划文件除外。
- [ ] 确认 `09-10-optimize-channel-context-loading` 的已提交结果仍是当前模板基线，不覆盖其他用户改动。

## 实施批次

### 1. 建立所有权合约测试

- [ ] 新增 `templates/embedded-c-overlay/.trellis/scripts/tests/test_review_fix_ownership_contract.py`。
- [ ] 定义受管消费者：template workflow、权威 review Skill、Channel/Claude/Codex Check Agent、Claude/Codex context-injection Hook。
- [ ] 先用当前模板运行新测试，确认它能捕获无条件 self-fix、禁止所有 Implement Agent 续接和 fresh implementation 强制路由等现有漂移。
- [ ] 测试 Hook builder 的实际输出，而不只扫描 Python 源码，确保运行时注入不会覆盖 Agent 分级。

### 2. 更新权威 review Skill 与 workflow

- [ ] 重写 review Skill 的 `Blocking-Finding Ownership`：Check Agent 只直接修复局部、机械、小、确定且范围内的问题。
- [ ] 写明主会话先核实 finding 的真实性与任务归属，再处理非机械性实现阻塞。
- [ ] 写明 Implement Agent 路由顺序：Codex inline 由主会话处理；否则可靠续接原代理优先；无法续接时，小且边界明确由主会话处理，复杂实现修复派发新代理。
- [ ] 写明可靠续接条件和失败降级，不新增或猜测会话标识，不把句柄作为崩溃恢复事实源。
- [ ] 写明复杂实现修复的耦合、跨模块/接口/契约、回归风险和成组验证信号，并声明数量/严重度不单独决定路由。
- [ ] 更新 template workflow 的 Phase 2 finding triage 和必要的 in-progress breadcrumb，去除强制 fresh implementation pass 的歧义。
- [ ] 明确责任分流不触发额外审查轮次，后续审查只由五档 profile 与 evidence invalidation 决定；保留 fresh Check Agent 规则。

### 3. 对齐三个 Check Agent

- [ ] 更新 Channel `check.md` 的 Core Responsibilities 和 finding 分支，删除“不得续接已退出 Implement Agent”的越权判断。
- [ ] 更新 Claude `trellis-check.md` 的 description、Core Responsibilities、Important 和 Self-Fix 工作流，删除无条件 `Fix issues yourself`。
- [ ] 更新 Codex `trellis-check.toml` 的 description、角色说明和 review/fix 指令，将 clear in-scope 收紧为局部、机械、小且确定。
- [ ] 三个 Agent 都要求：规划/设计/验收问题、非机械性实现阻塞和越界问题进入 not-fixed 报告；Check Agent 不自行派发或续接 Implement Agent。
- [ ] 保留各 Agent 现有上下文读取、递归保护、Git/生命周期禁令、review profile 和报告字段。

### 4. 对齐 Claude/Codex Hook 提示

- [ ] 修改两个 `inject-subagent-context.py` 的 `build_check_prompt`，加入语义一致的 finding handling 段。
- [ ] 删除 Hook 中无条件 `Fix issues yourself`，替换为机械直修和其他类别只报告的边界。
- [ ] 明确 Hook 不决定实施责任方，也不决定复审轮次；主会话读取权威 review Skill 后执行路由。
- [ ] 保留两端已有上下文、生命周期、Git、安全和项目检查差异，不为追求字节相同而删除平台约束。

### 5. 完成跨文件一致性测试

- [ ] 让新合约测试断言 workflow/review Skill 的主会话路由完整。
- [ ] 让新合约测试断言三个 Check Agent 的直接修复集合与只报告集合一致。
- [ ] 比较两个 Hook builder 生成的 finding handling 段，证明运行时语义一致。
- [ ] 断言受管文件不存在旧的无条件 self-fix 和 blanket no-resume 文案。
- [ ] 运行 `test_review_profile_contract.py`，证明五档 review scope、轮次、fresh reviewer 和证据失效契约没有被修复责任改写。

### 6. 定向与全量验证

- [ ] 运行新增所有权合约测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_review_fix_ownership_contract.py"
  ```

- [ ] 运行现有审查等级和子代理提示合约测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_review_profile_contract.py"
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_subagent_prompt_contract.py"
  ```

- [ ] 运行模板全量单元测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 运行仓库自用 Trellis 回归测试，只读验证根目录机制未受影响：

  ```powershell
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 使用临时 pycache 目录检查两个修改 Hook 的 Python 语法，避免在模板树写入 `__pycache__`：

  ```powershell
  $trellisPycache = Join-Path ([System.IO.Path]::GetTempPath()) "trellisforge-route-blocking-review-fixes-pycache"
  $env:PYTHONPYCACHEPREFIX = $trellisPycache
  python -m py_compile templates/embedded-c-overlay/.claude/hooks/inject-subagent-context.py templates/embedded-c-overlay/.codex/hooks/inject-subagent-context.py
  Remove-Item Env:PYTHONPYCACHEPREFIX
  ```

- [ ] 扫描旧策略残留，并人工区分 Implement Agent 续接和 fresh Check Agent：

  ```powershell
  rg --hidden -n -i "Fix issues yourself|Never resume an agent|fresh implementation pass|self-fix" templates/embedded-c-overlay/.trellis/workflow.md templates/embedded-c-overlay/.agents/skills/__PROJECT_PREFIX__-trellis-review templates/embedded-c-overlay/.trellis/agents/check.md templates/embedded-c-overlay/.claude/agents/trellis-check.md templates/embedded-c-overlay/.codex/agents/trellis-check.toml templates/embedded-c-overlay/.claude/hooks/inject-subagent-context.py templates/embedded-c-overlay/.codex/hooks/inject-subagent-context.py
  ```

- [ ] 核对根目录自用实现没有功能改动：

  ```powershell
  git status --short -- .trellis/workflow.md .trellis/agents .agents/skills .claude .codex
  ```

- [ ] 运行任务范围和全仓空白检查：

  ```powershell
  git diff --check -- templates/embedded-c-overlay
  git diff --check
  ```

- [ ] 构建、部署和硬件验证报告为 `not applicable`，原因是本仓库不产出固件、可执行产品或硬件目标。

### 7. 审查与交付

- [ ] 按本任务定制的 `Review level: strict` 执行独立 full-scope implementation-loop 审查；覆盖完整任务 diff、七个策略入口、新合约测试、现有 review profile 测试及全部验收条件。
- [ ] 每批阻塞 finding 修复完成后，新派 fresh Check Agent 重新执行完整 full-scope 审查，直到最新独立报告为零阻塞。
- [ ] 若任务范围、公共契约、验收条件或适用 Spec 实质变化，则按 evidence invalidation 重新执行 full-scope 审查。
- [ ] 当前任务不执行额外 commit-ready final review；在审查派发 prompt 和最终报告中明确这是用户指定的任务级例外，不修改或弱化发布模板中的 `strict` 契约。
- [ ] 逐项映射 AC1-AC8，记录修改文件、验证结果、未运行项和剩余风险。
- [ ] 不在本子任务更新版本号、升级资产、README、接入指南、manifest 或迁移链。
- [ ] 未经用户另行批准提交计划，不执行 `git add`、`git commit`、推送、合并或历史重写。

## 风险点与回滚点

- review Skill、workflow、三个 Agent 和两个 Hook 是同一协议的多个入口。任一入口保留更宽泛的 self-fix 文案都会重新引入漂移，以专用合约测试作为主要防线。
- “resume Implement Agent”和“fresh Check Agent”容易被字符串级规则混淆。测试和人工扫描必须按角色区分，不能删除 reviewer 独立性要求。
- Hook 与 Agent 有意重复安全边界，但 Hook 不应复制具体平台派发命令；否则后续宿主能力变化会造成新的漂移。
- 如果续接能力在运行时不可用，降级本身是正常路径，不应被测试视为失败；任务目录状态必须足以让主会话或新代理继续。
- 每批变更失败时，只撤销该批由本任务引入的模板改动并重新实现，不整体重置工作树，不覆盖用户已有变更。
