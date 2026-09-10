# 五档审查等级实施计划

## 实施前条件

- [ ] 用户已明确批准最新规划摘要；批准前不得运行 `task.py start` 或修改模板产品文件。
- [ ] 当前任务仍由本会话的精确 `session:*` 指针绑定，状态为 `planning`；启动后才进入 `in_progress`。
- [ ] 读取 `prd.md`、`design.md`、本文件、`implement.jsonl`、`check.jsonl` 和其中列出的 Spec。
- [ ] 用 `git status --short` 记录现有用户改动；功能写入仅允许位于 `templates/embedded-c-overlay/`。
- [ ] 确认根目录自用 `.trellis/workflow.md`、`.trellis/agents/`、`.trellis/scripts/common/planning_gate.py`、`.agents/skills/`、`.claude/` 和 `.codex/` 不在写入范围。

## 实施批次

### 1. 扩展规划门禁

- [ ] 在模板 `planning_gate.py` 中把合法 `Review level` 扩展为五档；门禁保持只读校验和 fail-closed，`standard` 默认值由 workflow/review Skill 持久化。
- [ ] 参数化更新 `test_planning_gate.py`，分别证明五个合法值可通过，并更新非法值错误信息断言。
- [ ] 运行模板 planning gate 单测，确认旧任务三档值不回归。

### 2. 更新规划与 Review Skill 契约

- [ ] 更新 `__PROJECT_PREFIX__-trellis-review/SKILL.md`：增加 `reinforced`、`comprehensive`，明确五档矩阵、证据失效、复审循环、fresh 终审和报告字段。
- [ ] 更新 review Skill 的 `agents/openai.yaml` 五档描述。
- [ ] 更新 `__PROJECT_PREFIX__-trellis-grill-adapter/SKILL.md` 的五值允许集合，默认仍为 `standard`，不因 AI 风险判断擅自升档。
- [ ] 保留 review Skill 为 profile 语义权威来源，不为文档/Agent 文本新增不可共享的运行时常量。

### 3. 更新 workflow 路由与门禁

- [ ] 搜索并更新 workflow 的 Phase Index、Phase 1 规划提示、Guardrails 和合法值说明。
- [ ] 重写 Phase 2.2 的 sub-agent 与 Codex inline 路由，分别定义 `standard`、`reinforced`、`comprehensive`、`strict` 的范围和复审策略。
- [ ] 明确每轮复审新派 Check Agent、阻塞项批量修复、非阻塞项不触发完整复审以及证据失效规则。
- [ ] 更新 final pass 与 Phase 3.4 preamble：只有 `strict` 无条件执行额外 commit-ready fresh full-scope 终审。
- [ ] 检查 `light` 和 `standard` 既有语义未被隐式增强或削弱。

### 4. 对齐三个 Check Agent

- [ ] 更新 Channel `check.md` 的权威 Skill 引用、五档路由、修复所有权和报告格式。
- [ ] 更新 Claude `trellis-check.md`，显式要求读取五档 profile、记录 round/stage/blocking count，并保持递归与生命周期边界。
- [ ] 更新 Codex `trellis-check.toml` 的描述、五档执行规则和相同报告字段。
- [ ] 确保 Check Agent 只直接修复清晰的小型范围内问题；较大实现问题返回实施环节，规划缺陷返回 Phase 1，越界项只报告。

### 5. 更新 Codex Hook 提示

- [ ] 将 `inject-workflow-state.py` 中两处三档 profile 文案更新为五档。
- [ ] 保持 Hook 仅注入提示，不在 Hook 中复制审查路由或承担门禁执行职责。

### 6. 增加跨文件合约测试

- [ ] 新增 `test_review_profile_contract.py`，以模板根目录为基准读取所有等级消费者。
- [ ] 断言五档名称、固定强度顺序、范围映射、复审策略、strict fresh 终审和报告字段在各层一致。
- [ ] 断言受管文件不存在已知旧三档枚举文案；测试失败信息需指出漂移文件和缺失契约。
- [ ] 测试只做静态解析/文本契约校验，不实际启动外部 Agent，也不依赖网络或硬件。

### 7. 全量验证与边界审计

- [ ] 运行模板单元测试：

  ```powershell
  python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 运行仓库自用 Trellis 回归测试，只读验证根目录机制未受影响：

  ```powershell
  python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
  ```

- [ ] 检查模板 Python 文件语法：

  ```powershell
  Get-ChildItem templates/embedded-c-overlay/.trellis/scripts,templates/embedded-c-overlay/.claude/hooks,templates/embedded-c-overlay/.codex/hooks -Recurse -Filter *.py -File |
    ForEach-Object { python -m py_compile $_.FullName }
  ```

- [ ] 扫描模板内旧三档枚举与所有等级消费者，逐项确认没有遗漏：

  ```powershell
  rg --hidden -n -i "light.*standard.*strict|standard.*strict" templates/embedded-c-overlay
  ```

- [ ] 检查禁止修改的根目录自用实现没有任务功能改动：

  ```powershell
  git status --short -- .trellis/workflow.md .trellis/agents .trellis/scripts/common/planning_gate.py .agents/skills .claude .codex
  ```

- [ ] 运行空白与补丁完整性检查：

  ```powershell
  git diff --check
  ```

- [ ] 报告构建、部署、硬件验证为 `not applicable`，原因是本仓库不产出固件、可执行产品或硬件目标。

### 8. 审查与交付

- [ ] 按本任务 `Review level: standard` 派发一次 affected-scope 独立审查；审查范围包含完整模板 diff、相关测试、任务验收条件及适用 Spec。
- [ ] 批量处理审查发现并运行直接受影响的检查；若范围、公共契约、验收条件或适用 Spec 实质变化，则使旧证据失效并重新审查。
- [ ] 汇总修改文件、验证结果、未运行项与剩余风险；不在本子任务更新版本号、升级资产、README 或接入指南。
- [ ] 未经用户另行批准提交计划，不执行 `git add`、`git commit`、推送、合并或历史重写。

## 风险点与回滚点

- workflow、review Skill 与三个 Agent 的文本属于同一跨层协议；任何一层漏改都会导致等级被错误回退或执行错误范围。以合约测试和残留字符串扫描作为主要防漂移措施。
- `comprehensive` 与 `strict` 都使用 full-scope，最容易混淆；只允许 `strict` 具有无条件 commit-ready fresh 终审门禁。
- 新复审轮次必须新派 Check Agent；“返回实施环节”表示开启新的实施 pass，不依赖已退出 Agent 的生命周期。
- 若某批出现回归，只撤销该批由本任务引入的模板改动并重新实现；不得整体重置工作树或覆盖用户已有修改。
