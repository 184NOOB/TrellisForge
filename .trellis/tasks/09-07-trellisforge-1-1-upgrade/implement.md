# TrellisForge 1.1 首次接入与 1.0 升级实施计划

## 实施前门禁

- 确认当前任务为 `.trellis/tasks/09-07-trellisforge-1-1-upgrade`，分支为 `trellis-channel-dispatch-wait-and-upgrade`。
- 读取 PRD、design、交接说明和 implement/check JSONL 中的 Spec。
- 运行 `trellis update --dry-run`，记录根目录上游管理文件状态；不使用整体 `--force`。
- 固定 1.0 基线提交 `e40a942`，复核它的 README 版本、Trellis 基线和目标文件内容。若证据不一致，返回规划阶段。

## 实施顺序

1. **建立版本事实与迁移资产**
   - 新增根目录 `VERSION`，值为 `1.1`。
   - 创建 `migrations/embedded-c-overlay/1.0-to-1.1/migration.json` 和最小旧基线树。
   - 在修改当前根目录参考文件之前，从 `e40a942` 提取 1.0 Forge 已管理的旧文件，以及 Trellis 0.6.10 已生成、1.1 将接管的两套 `trellis-channel` Skill `old` 基线；逐项核对历史内容，保留 `command-reference.md` 原有的多余尾部空行。
   - 以当前 1.1 模板作为 `new`，确认其中包含子任务 1 新增的约 6 行公共规则且不含上述多余空行；随后只清理当前根目录对应参考文件的同一空白问题，禁止用清理后的根文件覆盖历史 `old`。
   - 清单逐项记录 `merge`、`adopt` 或 `add`、旧/新来源及 SHA-256；验证路径唯一且全部位于允许根。内容规范化仅统一 LF/CRLF，不得裁剪行尾空白或尾部空行。

2. **提取共享安全模块**
   - 新增 `tools/lib/TrellisForgeOverlay.psm1`，实现目标/Git 路径验证、模板渲染、换行处理、哈希、备份、收据和事务回滚。
   - 从现有安装器迁移公共逻辑时保持原有错误条件、参数兼容和备份格式可读性。
   - 模块只导出两个入口需要的稳定函数；外部命令失败必须显式检查退出码并保留 stderr 诊断。

3. **升级首次安装器到 1.1**
   - 重构 `tools/install-embedded-c-overlay.ps1` 使用共享模块。
   - 保持 `-TargetRoot`、`-ProjectPrefix`、`-ProjectName`、`-Force`，以及 Git 根、`trellis init`、缓存、冲突、路径、备份、占位符和回滚语义。
   - 安装当前完整模板和 AGENTS 合并模板，成功后写 `.trellis/trellisforge.json` 1.1 收据。
   - 保证收据失败触发整次安装回滚；不删除用户文件，不修改上游 Trellis 状态文件。

4. **实现 1.0→1.1 升级器**
   - 新增 `tools/update-embedded-c-overlay.ps1`，默认预检，`-Apply` 执行。
   - 无收据且省略 `-FromVersion` 时默认选择 1.0→1.1 迁移；仍要求显式 `ProjectPrefix`/`ProjectName`，并通过结构、基线和三方合并验证兼容性。
   - 实现已有收据读取/一致性校验、1.1 幂等、显式错误来源版本和无法验证 1.0 目标的拒绝。
   - 校验 migration schema、资产哈希和渲染后路径；用 `git merge-file --stdout` 计算 `merge`/`adopt` 结果，按设计分类状态。
   - 任一冲突时只在 Git 元数据目录写 report/candidate，工作树零写入。
   - 全部通过后执行完整备份、原子写入、收据更新和失败回滚；不提供部分应用或忽略冲突开关。

5. **增加工具级自动化测试**
   - 新增 `tests/test_overlay_tools.py` 和最小测试夹具/帮助函数。
   - 覆盖首次安装、1.0 干净迁移、用户定制合并、冲突零写入、candidate/report、新文件冲突、幂等、错误版本/参数/收据、LF/CRLF、路径拒绝、清单哈希和故障回滚。
   - 增加两套 `command-reference.md` 镜像的专项回归：以含历史尾部空行的 `old/current` 升级后，应得到包含新增规则且无多余空行的 `new`，不产生虚假冲突；另加真实用户修改用例，确认仍会合并或报告冲突。
   - 断言 `.trellis/.version`、`.trellis/.template-hashes.json`、无关脏文件和目标业务文件始终不被修改。

6. **重构 README 和接入文档**
   - 将 README 改为当前工程入口，更新 Forge 版本为 1.1，保留 Trellis 0.6.10 独立标识，加入首次安装/1.0 升级、能力、目录、安全和验证入口。
   - 更新 `docs/接入指南.md`，分开首次接入、Forge 升级和上游 Trellis 更新，写明预检、Apply、冲突重试、备份恢复、收据提交和升级后验证。
   - 更新 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 及直接受影响的说明，准确列出完整 Channel Skill 和脚本生成收据的边界。

7. **执行完整验证**
   - `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
   - `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`
   - `python -B -m unittest discover -s tests -p "test_*.py"`
   - 对仓库与模板涉及的 Python 文件运行 `python -m py_compile`，随后清理并扫描 `__pycache__`、`.pyc`、`.pyo`。
   - 使用 Windows PowerShell 5.1 `[scriptblock]::Create()` 解析模块和两个脚本，并运行临时 Git 仓库安装/升级冒烟。
   - 检查 migration/receipt JSON schema、版本一致性、未替换占位符和 `git diff --check`。
   - 构建、部署、硬件验证报告为 `not applicable`；记录下游需自行执行的验证，不伪造结果。

8. **执行 standard 独立审查**
   - 派发一次 affected-scope `trellis-check`，检查完整任务 diff、所有验收项、迁移事务、用户定制保护、路径安全、备份回滚、文档命令和测试证据。
   - 修复阻塞问题后由主会话重跑受影响检查；任务范围实质变化时才重新派发完整独立审查。

## 验收映射

| 验收主题 | 步骤 |
|---|---|
| 1.1 版本事实一致 | 1、6、7 |
| 首次安装 1.1 与收据 | 2、3、5 |
| 版本化 1.0 升级 | 1、2、4、5 |
| 三方合并与冲突零写入 | 4、5 |
| 备份、原子应用与回滚 | 2、3、4、5 |
| README、指南与模板清单 | 6、7 |
| 自动验证与 standard 审查 | 7、8 |

## 风险文件与回滚点

- `tools/lib/TrellisForgeOverlay.psm1` 与两个入口是同一安全边界，先通过工具测试再改文档命令。
- migration baseline/manifest 必须与 1.0/1.1 内容一起审查；任何后续模板改动都要同步更新新内容哈希和测试。
- 安装器重构不得丢失现有 `-Force` 备份与异常恢复；保留重构前行为测试作为回归门禁。
- README/指南最后修改，确保示例参数与最终 CLI 完全一致。
- 不提交、不打 tag、不推送，直到实施、验证、standard 审查完成且用户批准提交计划。
