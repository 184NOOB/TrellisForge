# TrellisForge 工程规则

始终使用简体中文回复。

## 仓库事实

- Git 根目录：`C:\Users\10671\Desktop\Study\TrellisForge`。
- 项目内容：`tools/` 下的 PowerShell 安装器、`templates/` 下的 TrellisForge 覆盖层模板、`docs/` 下的中文接入文档。
- 真实构建命令：无；本仓库不产出固件或可执行产品。
- 静态检查/测试命令：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`、`python -m py_compile` 检查 `.trellis/scripts/` 与 `.claude/hooks/`、`.codex/hooks/` 下的 Python 文件、`git diff --check`。
- 部署/硬件验证：无硬件目标；安装脚本的目标仓库验证由使用者在目标项目中执行。

## 工具与模板约束

- `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 是项目级 Trellis 工作流实现，修改时必须同步相关模板文件。
- `templates/embedded-c-overlay/` 是面向下游嵌入式 C 项目的发布模板；其中的 C/硬件术语属于模板示例，不代表本仓库自身存在固件或硬件事实。
- `tools/install-embedded-c-overlay.ps1` 只覆盖清单中的目标文件，并在 `-Force` 前写入 Git 元数据备份；不要扩大覆盖范围或删除目标仓库文件。
- 不把 `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 或 `.trellis/.template-hashes.json` 当作可发布模板内容。
- Python 文件使用 UTF-8；PowerShell 脚本保持 Windows PowerShell 兼容语法。文档中的命令必须能在 Windows PowerShell 中解释。

## 质量与变更边界

- 不虚构 `lint`、`typecheck`、固件构建或硬件验证命令；未适用的类别报告为 `not applicable` 并说明原因。
- 修改模板正文、占位符替换、Hook 或代理时，必须运行对应 Python 单测、语法解析和 `git diff --check`。
- 修改安装脚本时，必须检查目标路径校验、冲突检测、备份清单和异常回滚路径；不得静默覆盖用户文件。
- 变更上游 Trellis 文件前先运行 `trellis update --dry-run`，使用逐项迁移，不使用整体 `--force` 覆盖项目定制。

## Git

- 保留用户已有改动；不执行未经授权的提交、推送、合并或重写历史。
- 提交标题使用简体中文并遵守 Conventional Commits，例如 `feat: 添加模板校验`。
- `.trellis/config.yaml` 保持 `session_auto_commit: false`。

<!-- TRELLIS:START -->
# Trellis Instructions

本项目使用 Trellis。工作流、Spec、任务和会话记录位于 `.trellis/`；项目级
Skills 位于 `.agents/skills/`；Codex/Claude 子代理定义位于 `.codex/agents/`
与 `.claude/agents/`。

优先遵循 `.trellis/workflow.md`。任务在 `planning` 或 `planning-inline` 时，
必须使用 `trellis-brainstorm`、`grill-me` 和
`trellisforge-trellis-grill-adapter`；实施前必须完成收敛并获得后续用户批准。

<!-- TRELLIS:END -->
