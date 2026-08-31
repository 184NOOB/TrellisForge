# 非嵌入式 C 迁移替换表

TrellisForge 的规划收敛、用户审批、派发边界、批量探索、阶段验证、停止条件和
review profile 可保留。迁移到其他语言时，只按本表替换领域语义，不得让 AI
重新设计整套工作流。

| 文件 | 搜索的 C/固件语义 | 替换规则 |
| --- | --- | --- |
| `.trellis/workflow.md` | `embedded C project`、`firmware Specs`、`target builds`、`hardware validation` | 替换为目标语言的项目 Spec、构建/测试和部署验证；保留规划门禁、派发边界和效率规则 |
| `.trellis/agents/implement.md` | 嵌入式 C 检查、目标构建、硬件验证 | 改为项目定义的静态分析、测试、构建和运行时验证 |
| `.trellis/agents/check.md` | 嵌入式 C Spec、目标构建、硬件合同 | 改为目标语言的影响范围、依赖、接口和验证合同 |
| `.agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md` | ISR、DMA、Flash、寄存器、硬件验证 | 替换为目标语言的并发、依赖、迁移、兼容和发布风险 |
| `.claude/agents/trellis-*.md` | 不虚构 Web lint/typecheck、目标构建 | 改为只运行目标项目已定义的检查和构建命令 |
| `.codex/agents/trellis-*.toml` | 嵌入式 C 项目检查/目标构建 | 同步目标语言的验证类别和报告字段 |
| `.claude/hooks/inject-subagent-context.py`、`.codex/hooks/inject-subagent-context.py` | C 固件检查和硬件验证提示 | 同步替换完成提示中的领域类别，不改变上下文注入和停止逻辑 |
| `.trellis/spec/shared/*.md`、`AGENTS.md` | MCU、ISR、DMA、Flash、寄存器约束 | 用目标语言的真实仓库结构、工具链、并发和部署约束替换占位符 |

禁止只改命令名称而保留 C 固件风险术语；也禁止为了换语言删除规划收敛或
子代理批量操作规则。

