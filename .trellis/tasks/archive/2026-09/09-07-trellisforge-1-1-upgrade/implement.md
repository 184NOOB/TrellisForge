# TrellisForge 1.1 首次接入与 1.0 升级实施计划

## 实施前门禁

- 确认当前任务为 `.trellis/tasks/09-07-trellisforge-1-1-upgrade`，分支为 `trellis-channel-dispatch-wait-and-upgrade`。
- 读取 PRD、design、交接说明和 implement/check JSONL 中的 Spec。
- 运行 `trellis update --dry-run`，记录根目录上游管理文件状态；不使用整体 `--force`。
- 固定 1.0 基线提交 `e40a942`，复核它的 README 版本、Trellis 基线和目标文件内容。若证据不一致，返回规划阶段。

## 实施顺序

1. **建立版本事实与电梯模型资产**
   - 保持并核对根目录 `VERSION` 为 `1.1`。
   - 创建 `history/embedded-c-overlay/objects/` 和 `versions/1.0/manifest.json`、`versions/1.1/manifest.json`；对象按 SHA-256 去重，manifest 记录模板相对路径、对象引用、内容哈希、占位符渲染规则、路径所有权和 Trellis 基线。
   - 直接从 `e40a942` 提取 1.0 Forge 已管理文件和 1.1 将接管的两套 `trellis-channel` Skill canonical 对象；后者标记为 `adoption-baseline`。逐项核对历史内容，并用方案 A 已提交 baseline 交叉验证，确保 `command-reference.md` 保留原有多余尾部空行。
   - 以当前 1.1 模板生成完整目标 manifest 和 canonical 对象，确认其包含子任务 1 新增的约 6 行公共规则且不含上述多余空行；核对 `11b16b9` 已完成的根参考文件规范化，禁止用当前根文件覆盖 1.0 对象。
   - 创建 `migrations/embedded-c-overlay/structural/1.0-to-1.1.json`，以空 `actions` 声明首个连续结构步骤和收据 bootstrap；执行器验证链连续性与动作白名单。未来改名、目录、所有权和收据 schema 等正文合并无法表达的变化才加入相邻版本步骤；本次不删除目标文件。
   - 历史对象与两个版本 manifest 通过新的生成/验证工具确定性地产生；生成器不得依赖网络或当前 Git 分支之外的隐式状态，1.0 提取来源固定为 `e40a942`。
   - 完成等价性验证后删除方案 A 的 `migrations/embedded-c-overlay/1.0-to-1.1/migration.json`、`baseline/` 和 `new/`，并替换任务目录中的 `gen_migration.py`/`verify_assets.py`；最终工作树不得同时存在两套升级资产源。

2. **提取共享安全模块**
   - 重构现有 `tools/lib/TrellisForgeOverlay.psm1`，保留目标/Git 路径验证、模板渲染、换行处理、哈希、备份、收据和事务回滚基础。
   - 用版本 manifest/对象库加载和结构链预演替换 `Get-OverlayMigrationManifest` 及逐对 migration 数据结构；清理仅服务方案 A 的导出接口，避免双实现漂移。
   - 重构时保持现有错误条件、参数兼容和备份格式可读性。
   - 模块只导出两个入口需要的稳定函数；外部命令失败必须显式检查退出码并保留 stderr 诊断。

3. **升级首次安装器到 1.1**
   - 调整现有 `tools/install-embedded-c-overlay.ps1` 使用电梯模型 manifest 和收据契约。
   - 保持 `-TargetRoot`、`-ProjectPrefix`、`-ProjectName`、`-Force`，以及 Git 根、`trellis init`、缓存、冲突、路径、备份、占位符和回滚语义。
   - 安装前验证 live 模板与 1.1 manifest 一致；安装当前完整模板和 AGENTS 合并模板，成功后写 `.trellis/trellisforge.json` schema 1 收据，其中每个文件记录 `canonical_sha256`、`baseline_sha256` 和 `installed_sha256`。
   - 保证收据失败触发整次安装回滚；不删除用户文件，不修改上游 Trellis 状态文件。

4. **实现电梯模型升级器与 1.0 入场适配**
   - 重构现有 `tools/update-embedded-c-overlay.ps1`，保持默认预检、`-Apply` 执行和当前 CLI 参数兼容。
   - 无收据且省略 `-FromVersion` 时默认进入 1.0 入场适配；仍要求显式 `ProjectPrefix`/`ProjectName`，并通过历史 manifest、canonical 对象、结构链和三方合并验证兼容性。
   - 实现 schema 1 收据读取/一致性校验、canonical baseline 定位、1.1 幂等、显式错误来源版本和无法验证来源的拒绝。
   - 校验来源/目标 manifest、历史对象哈希、live 模板一致性和渲染后路径；比较完整 manifest 后仅对 canonical 对象变化、`adoption-baseline`、`add` 和 `structural` 路径生成计划，相同对象路径保持工作树不变但进入新收据。
   - 同一版本模板与 manifest 不一致时以 `unsupported` 停止，禁止使用漂移后的 live 模板继续升级。
   - 任一冲突时只在 Git 元数据目录写 report/candidate，工作树零写入。
   - 全部通过后执行完整备份、原子写入、收据更新和失败回滚；不提供部分应用或忽略冲突开关。

5. **增加工具级自动化测试**
   - 重构现有 `tests/test_overlay_tools.py` 和测试夹具，移除对方案 A `baseline/new/migration.json` 的依赖。
   - 覆盖首次安装、1.0 无收据入场、schema 1 收据生成与续升契约、用户定制合并、冲突零写入、candidate/report、新文件冲突、幂等、错误版本/参数/收据、LF/CRLF、路径拒绝、manifest/对象哈希、同版本模板漂移和故障回滚。
   - 增加两套 `command-reference.md` 镜像的专项回归：以含历史尾部空行的 1.0 canonical 对象升级后，应得到包含新增规则且无多余空行的 1.1 内容，不产生虚假冲突；另加真实用户修改用例，确认仍会合并或报告冲突。
   - 增加结构迁移链顺序、失败回滚和历史对象缺失用例；验证修改 live 模板但不提升版本会 fail closed。
   - 断言 `.trellis/.version`、`.trellis/.template-hashes.json`、无关脏文件和目标业务文件始终不被修改。

6. **重构 README 和接入文档**
   - 修订 README 中已经存在的 1.1 内容，将方案 A 的逐对迁移资产说明替换为当前目标、历史对象库、版本 manifest、1.0 入场适配和结构迁移链；保留 Trellis 0.6.10 独立标识及首次安装/升级入口。
   - 修订 `docs/接入指南.md`，保持首次接入、Forge 升级和上游 Trellis 更新分节，更新维护契约、预检、Apply、冲突重试、备份恢复、收据提交和升级后验证。
   - 更新 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 及直接受影响的说明，移除 `baseline/new` 描述，准确说明历史对象、manifest、完整 Channel Skill 和脚本生成收据的边界。

7. **执行完整验证**
   - `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"`
   - `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"`
   - `python -B -m unittest discover -s tests -p "test_*.py"`
   - 对仓库与模板涉及的 Python 文件运行 `python -m py_compile`，随后清理并扫描 `__pycache__`、`.pyc`、`.pyo`。
   - 使用 Windows PowerShell 5.1 `[scriptblock]::Create()` 解析模块和两个脚本，并运行临时 Git 仓库安装/升级冒烟。
   - 检查 history manifest/object、structural migration 和 receipt JSON schema、版本一致性、未替换占位符和 `git diff --check`。
   - 构建、部署、硬件验证报告为 `not applicable`；记录下游需自行执行的验证，不伪造结果。

8. **执行 standard 独立审查**
   - 派发一次 affected-scope `trellis-check`，检查完整任务 diff、所有验收项、迁移事务、用户定制保护、路径安全、备份回滚、文档命令和测试证据。
   - 修复阻塞问题后由主会话重跑受影响检查；任务范围实质变化时才重新派发完整独立审查。

## 验收映射

| 验收主题 | 步骤 |
|---|---|
| 1.1 版本事实一致 | 1、6、7 |
| 首次安装 1.1 与收据 | 2、3、5 |
| 电梯模型与 1.0 入场升级 | 1、2、4、5 |
| 三方合并与冲突零写入 | 4、5 |
| 备份、原子应用与回滚 | 2、3、4、5 |
| README、指南与模板清单 | 6、7 |
| 自动验证与 standard 审查 | 7、8 |

## 风险文件与回滚点

- `tools/lib/TrellisForgeOverlay.psm1` 与两个入口是同一安全边界，先通过工具测试再改文档命令。
- 历史 manifest/对象库、1.0 入场结构链和当前 1.1 manifest 必须与模板内容一起审查；任何模板内容变化都必须提升 VERSION、生成新 manifest/对象并更新测试，不能改写已有历史对象。
- 安装器重构不得丢失现有 `-Force` 备份与异常恢复；保留重构前行为测试作为回归门禁。
- README/指南最后修改，确保示例参数与最终 CLI 完全一致。
- 不提交、不打 tag、不推送，直到实施、验证、standard 审查完成且用户批准提交计划。
