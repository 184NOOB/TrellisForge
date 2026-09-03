# 仓库布局

- `docs/`：README 之外的接入与维护文档。
- `tools/`：安装器等 PowerShell 工具。
- `templates/embedded-c-overlay/`：发布到下游嵌入式 C 项目的覆盖层模板。
- `templates/language-adaptation/`：迁移到其他语言时的替换指导。
- `.trellis/`、`.agents/`、`.claude/`、`.codex/`：当前仓库自身的 Trellis 工作流和运行配置。
- `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/`：本地运行状态，不复制进发布模板。
- `.git/trellisforge-backup/`：安装器的覆盖前备份，仅属于 Git 元数据。

本仓库没有产品源码、公共头文件、链接脚本、启动文件或生成目录。新增脚本和
模板文件时，必须更新 README 或接入指南中的目录说明（如目录契约发生变化）。
