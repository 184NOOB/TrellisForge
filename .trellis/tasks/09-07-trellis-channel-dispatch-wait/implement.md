# Trellis Channel 派发与等待流程实施计划

## 实施前边界检查

- 当前任务必须仍为 `09-07-trellis-channel-dispatch-wait`，分支必须为 `trellis-channel-dispatch-wait-and-upgrade`。
- 只允许修改 `templates/embedded-c-overlay/` 中与 Trellis Channel 规则和契约测试直接相关的文件。
- 发现需要修改 `docs/接入指南.md`、README、`TEMPLATE-CONTENTS.md`、`tools/install-embedded-c-overlay.ps1`、版本号或升级逻辑时，记录为子任务 2 输入并停止跨范围修改。
- 不修改仓库根目录现用的 `.trellis/`、`.agents/`、`.claude/` 或 `.codex/` 产品文件；任务规划文件和状态元数据除外。

## 实施顺序

1. **建立模板 Skill 基线**
   - 以根目录当前 `.agents/skills/trellis-channel/` 与 `.claude/skills/trellis-channel/` 为只读参考，确认两套来源相同。
   - 将完整文件树加入模板对应目录，包括 `SKILL.md` 及全部 reference 文件；不得只复制本次修改涉及的段落。
   - 记录模板新增路径集合，供契约测试和子任务 2 的安装/升级规划使用。

2. **更新公共 Channel 规则**
   - 在模板两套 Skill 的对应公共文件中同步写入一次 spawn、一个 wait、终止事件、可调整 timeout 和 progress 诊断边界。
   - 为实施与审查分别给出 PowerShell 可解释的派发/等待示例。
   - 公共规则不使用 `exec_command`、`write_stdin` 或 `session_id` 描述 Claude Code 主会话。

3. **更新 Codex 主会话工作流**
   - 只在模板 `.trellis/workflow.md` 的 Codex 路由和 `[codex-inline]` 相关范围加入终端编排。
   - 写明首次短 yield、复用同一 `session_id`、单次窗口以运行时 schema 为准、运行中继续 `write_stdin`、终止后恢复处理。
   - 将“等待时保持安静”落实为可观察的工具动作约束：wait session 存活期间不运行新的 wait、额外 channel、progress/messages/list、`plan.py status` 或其他任务操作；用户中断和明确故障走异常路径。

4. **核对 worker 终止事件契约**
   - 检查模板 `.trellis/agents/implement.md` 和 `check.md` 是否已经明确完成发布 `done`、失败发布 `error`。
   - 只在契约缺失时补充；不把 dispatcher 的终端 session 管理复制到 worker 角色卡。

5. **扩展模板契约测试**
   - 在模板测试目录扩展现有测试或新增职责单一的测试，校验完整文件集合、两套公共 Skill 逐字节一致、Codex 专属术语的作用域和标准流程关键语义。
   - 增加反例断言，防止正常流程出现重复 `trellis channel wait`、`list --all`、progress 轮询、`messages --include-progress` 或 `plan.py status` 指导。
   - 测试只检查静态模板契约，不启动真实 worker，不依赖外部 provider。

6. **执行验证**
   - 运行 `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`。
   - 运行 `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`。
   - 按项目规则对相关 `.trellis/scripts/`、`.claude/hooks/`、`.codex/hooks/` Python 文件执行 `python -m py_compile`，并清理验证生成的缓存，确保模板不包含 `__pycache__`、`.pyc` 或 `.pyo`。
   - 运行 `git diff --check`。
   - 构建、部署和硬件验证报告为 `not applicable`；本仓库不产出可执行产品或硬件目标。

7. **执行 standard 审查**
   - 实施完成后派发一次独立 affected-scope `trellis-check`；提交前不执行 full-scope（全盘）审查。
   - 审查本任务完整 diff、全部验收项、Skill 完整性与镜像同步、Codex/Claude 平台边界、模板测试和子任务边界，不扫描无影响证据的仓库区域。
   - 修复阻塞问题后由主会话重跑受影响检查；只有修复导致任务范围发生实质变化时，才重新派发完整独立审查。

## 验收映射

| 验收主题 | 实施步骤 |
|---|---|
| 仅修改发布模板，不跨入安装/升级 | 实施前边界检查、步骤 7 |
| 完整 Skill 覆盖层与公共镜像一致 | 步骤 1、2、5 |
| Codex 专属 session 编排不影响 Claude Code | 步骤 2、3、5 |
| 实施/审查流程、唯一 wait 与 timeout 分层 | 步骤 2、3、5 |
| worker `done`/`error` 契约 | 步骤 4、5 |
| 自动验证与不含全盘提交前检查的 standard 审查 | 步骤 6、7 |

## 禁止修改清单

- `docs/接入指南.md`
- `README.md`
- `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md`
- `tools/install-embedded-c-overlay.ps1`
- 任何版本文件、升级补丁或 1.0 迁移实现
- 根目录现用 `.trellis/workflow.md`、`.agents/skills/trellis-channel/`、`.claude/skills/trellis-channel/`、`.codex/`、Hook 和代理文件

上述内容全部留给子任务 2 或不在父任务范围内。实施 agent 若发现它们是完成发布所必需的，只记录依赖，不得自行跨任务编辑。

## 回滚点

- 完整 Skill 模板导入、公共规则修改、Codex workflow 修改、worker 契约和测试分别形成可审查批次。
- 任一批次出现范围越界或平台语义混淆时，只回滚该批次的模板改动，保留用户已有文件和任务规划。
