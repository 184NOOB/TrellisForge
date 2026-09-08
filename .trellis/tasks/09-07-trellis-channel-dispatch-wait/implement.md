# Trellis Channel 派发与等待流程实施计划

## 实施顺序

1. **建立变更清单与基线**
   - 读取本任务 `prd.md`、`design.md`、相关 Spec 和现有 channel 参考文档。
   - 记录实际修改范围：`.trellis/workflow.md` 的 Codex 路由/inline 提示、`.agents/skills/trellis-channel/` 与 `.claude/skills/trellis-channel/` 中的 provider-neutral 规则，以及必要的文档契约测试文件。
   - 批量确认 `.agents` 与 `.claude` 两套 channel 文件当前正文一致，避免覆盖用户已有差异。

2. **更新 Codex 主会话工作流规则**
   - 仅在 `.trellis/workflow.md` 的 Codex 路由和 Codex inline 相关提示中补充唯一 wait 进程、同一 `session_id` 复用、等待期间暂停其他主会话活动、终止后恢复的明确规则。
   - 明确 Claude Code 作为 dispatcher 的流程不在本任务范围内，不能复用或推断 Codex 的 `exec_command`/`write_stdin` 规则。
   - 保留现有 implement/check 派发协议、执行计划门禁和 review profile 规则；不把 channel wait 与 native sub-agent dispatch 混写成同一机制。

3. **更新 provider-neutral channel 技能参考并同步 Claude 镜像**
   - 在 `references/workflows.md` 与 `references/workers.md` 增加实施和审查的统一 dispatcher 示例，明确一次 spawn、一次 wait 和终止事件；不把 Codex 的终端 API 当作 Claude Code 主会话的流程要求。
   - 在必要的 `SKILL.md`、`command-reference.md` 或 `progress-debugging.md` 处补充边界说明：`done/error` 是完成信号，progress 只用于故障诊断，正常等待不轮询；工具窗口和 CLI timeout 分离；Codex 专属条目加范围标记。
   - 将 provider-neutral 规则按批次同步到 `.claude/skills/trellis-channel/`，同步后做逐文件正文比较。

4. **增加文档契约验证**
   - 新增一个 Python 单元测试，批量读取两套 channel 文档，验证 provider-neutral 关键规则和命令示例存在、镜像文件一致、正常流程未引入禁止的重复 wait 或 progress 轮询指导，并验证 Codex 专属范围声明存在。
   - 测试只验证文档契约，不启动真实 provider、worker 或终端等待进程。

5. **按项目规则验证并形成报告**
   - 运行：
     - `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
     - 对 `.trellis/scripts/`、`.claude/hooks/`、`.codex/hooks/` 下 Python 文件运行 `python -m py_compile`。
     - `git diff --check`
   - 分别报告单元测试、语法检查、文档契约检查；构建、部署、硬件验证标记为 `not applicable`。

6. **strict 审查与收敛**
   - 在每个重要文档批次后检查实际 diff；完成全部修改后派发一次独立的 full-scope `trellis-check` 审查，使用本任务的 strict profile。
   - 审查范围包括完整任务 diff、`.trellis/workflow.md` 的 Codex 路由、两套 provider-neutral channel 技能镜像、文档契约测试、相关 Spec 和项目验证命令；确认没有把 Codex 规则扩展为 Claude Code 主会话要求。
   - 对所有阻塞性正确性、安全性或验收问题修复后重复相关审查，直到没有阻塞发现；审查未完成前不得提交。

## 验收映射

- 派发与等待示例、session 复用、完成后恢复：步骤 2–3，文档契约测试覆盖。
- 禁止重复 wait、额外 channel、progress/完整聊天轮询和等待期间其他主会话活动：步骤 2–4 覆盖。
- 实施与审查流程对称、timeout 分层：步骤 3–4 覆盖。
- 平台分层与镜像边界：步骤 2–4 覆盖；验证公共 `.agents/skills`/`.claude/skills` 文件一致，同时确认 Codex 专属终端编排没有扩展为 Claude Code 主会话流程。
- strict review：步骤 6，必须有独立审查结果及修复后的复审证据。

## 非目标

- 不修改 Trellis CLI、事件存储、provider adapter、worker role card 或任务状态机；不设计或实现 Claude Code 主会话的派发/等待流程。
- 不执行 `task.py start`、不生成执行计划、不提交 Git、不升级 TrellisForge 版本。
- 不把诊断场景的受限 `messages --raw` 读取写成正常等待流程。

## 回滚点

- 主会话规则批次与 channel 技能批次可分别回滚；镜像同步必须与共享文件保持同一批次。
- 若文档契约测试失败，先修正文档或测试契约，再继续 strict 审查；不得记录未执行或失败的检查为通过。
