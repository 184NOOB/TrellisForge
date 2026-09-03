# 工具仓库开发规范

本包对应仓库根目录 `main`，涵盖 Python 工作流脚本、Windows PowerShell 安装器、发布模板和中文文档。仓库不包含后端服务、前端应用、数据库或固件产品源码。

## 规范索引

- [Python 工作流脚本](python.md)：脚本边界、编码和测试方式。
- [PowerShell 安装器](powershell.md)：Windows 兼容性、路径安全、冲突和回滚。
- [模板与文档](templates-and-docs.md)：发布内容、占位符和接入文档契约。

## 开发前检查

1. 阅读根目录 [AGENTS.md](../../../../AGENTS.md) 和相关 README/接入指南。
2. 用 `git status --short` 确认已有改动，不覆盖未授权文件。
3. 搜索将要修改的占位符、路径或配置键，确认所有消费者。
4. 修改模板、Hook、代理或脚本时，确认对应测试和语法检查命令。
5. 修改 Trellis 上游管理文件前，先运行 `trellis update --dry-run` 并逐项迁移。

## 质量检查

- Python 单测：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
- Python 语法：对 `.trellis/scripts/`、`.claude/hooks/`、`.codex/hooks/` 下的 Python 文件运行 `python -m py_compile`。
- 文档和模板：运行 `git diff --check`，并扫描 `.trellis/spec/` 与安装结果中的未替换占位符。
- 安装器：在临时 Git 仓库执行无 `-Force` 冲突检查和带备份的安装冒烟。
- 构建、部署、硬件验证：`not applicable`，本仓库没有可构建产品或硬件目标；下游仓库自行验证。

新增规范必须引用真实文件和可复现命令，不写泛化的前后端约定或未实施的理想方案。
