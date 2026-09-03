# 验证策略

## 命令

- Python 单元测试：`python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
- Python 语法检查：`python -m py_compile` 作用于 `.trellis/scripts/`、`.claude/hooks/`、`.codex/hooks/` 下的 Python 文件。
- 模板/文档检查：`git diff --check`，并扫描安装结果中的 `<...>` 占位符。
- PowerShell 安装器验证：在临时 Git 仓库中执行一次无 `-Force` 冲突预览和一次带备份的安装冒烟。
- 构建与硬件验证：`not applicable`；本仓库不包含固件目标或硬件设备。

## 报告

测试、语法检查、模板检查和安装器冒烟分别报告 `pass`、`fail`、`not run` 或
`not applicable`，并附实际命令或原因。下游项目的构建和硬件验证只能在下游
仓库中执行，不能由本仓库的文档测试代替。
