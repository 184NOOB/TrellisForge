# PowerShell 安装器

## 适用范围

唯一发布安装器是 `tools/install-embedded-c-overlay.ps1`。它把 `templates/embedded-c-overlay/` 的清单文件安装到已运行 `trellis init` 的下游 Git 仓库。

## 安全契约

- 先解析模板根和目标 Git 工作树根，拒绝不存在、非 Git 根目录或未执行 `trellis init` 的目标。
- 默认只预览冲突并拒绝覆盖；`-Force` 前将实际覆盖的文件复制到 `.git/trellisforge-backup/<时间戳>-<GUID>/`，同时写入带 SHA-256 的 `backup-manifest.json`。
- 只覆盖模板清单中的文件，不删除目标仓库其他文件；根 `AGENTS.md` 通过 `AGENTS.md.trellisforge-template` 供人工合并。
- 写入失败时恢复本次已覆盖文件，并清理本次新写入且未备份的文件。
- 拒绝模板中的 Python 缓存文件，避免把运行时产物发布到下游。

## 占位符与兼容性

路径中的 `__PROJECT_PREFIX__`、正文中的 `PROJECT_PREFIX` 和 `PROJECT_NAME` 必须完整替换。脚本保持 Windows PowerShell 兼容语法，使用 `-LiteralPath` 处理文件路径。

## 验证

修改安装器时，检查目标路径校验、冲突检测、备份清单、异常回滚和占位符替换，并在临时 Git 仓库运行一次无 `-Force` 冲突预览和一次带备份安装冒烟。
