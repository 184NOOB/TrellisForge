# TrellisForge 1.1 首次接入与 1.0 升级设计

## 目标与边界

本设计提供两条明确分开的交付路径：新项目使用安装器安装 TrellisForge 1.1；已接入 1.0 的项目使用版本化升级器迁移到 1.1。两条路径共享安全基础设施，但不能互相替代。安装器仍可覆盖 `trellis init` 产生的上游基线；升级器只处理 1.0→1.1 的真实差异并保留可合并的用户定制。

本任务不升级上游 Trellis、不修改下游业务代码、不维护 1.0 之外的迁移路径，也不发布 Git tag 或远端 release。

## 交付结构

```text
VERSION
tools/
  lib/TrellisForgeOverlay.psm1
  install-embedded-c-overlay.ps1
  update-embedded-c-overlay.ps1
migrations/embedded-c-overlay/1.0-to-1.1/
  migration.json
  baseline/<仅迁移需要的 1.0 文件>
tests/
  test_overlay_tools.py
templates/embedded-c-overlay/
  ... 1.1 模板源
docs/接入指南.md
README.md
```

`VERSION` 是仓库内 TrellisForge 版本事实源，内容为 `1.1`。迁移清单保存 `from_version`、`to_version`、覆盖层类型、Trellis 基线、路径动作及旧/新内容 SHA-256。测试锁定 VERSION、迁移清单、README 和脚本输出的版本一致性。

## 共享 PowerShell 模块

`tools/lib/TrellisForgeOverlay.psm1` 承担安装器和升级器共同依赖的机制：

- 解析并验证目标 Git 根目录与真实 Git 元数据路径；
- 验证 `ProjectPrefix`、`ProjectName`、相对路径和模板根目录，拒绝路径逃逸、换行/空字符参数及目录冒充文件；
- 按统一顺序替换路径中的 `__PROJECT_PREFIX__` 以及正文中的 `PROJECT_PREFIX`、`PROJECT_NAME`；
- 以 UTF-8 无 BOM 读取和写入文本，识别目标文件 LF/CRLF 并在合并输出中保持原换行风格；
- 计算 SHA-256，创建 Git 元数据备份与清单；
- 通过临时目录准备写入集合，再执行写入、失败回滚和本次新增文件清理；
- 读取、校验和写入 `.trellis/trellisforge.json` 收据。

模块导出窄接口，脚本负责参数和用户输出，避免调用方依赖内部临时结构。模块不得修改 `.trellis/.version` 或 `.trellis/.template-hashes.json`。

## 安装收据

成功安装或升级后，目标项目包含可提交的 `.trellis/trellisforge.json`：

```json
{
  "schema_version": 1,
  "trellisforge_version": "1.1",
  "overlay": "embedded-c",
  "project_prefix": "example",
  "project_name": "Example Firmware",
  "files": [
    {
      "path": ".trellis/workflow.md",
      "template_sha256": "...",
      "installed_sha256": "..."
    }
  ]
}
```

`template_sha256` 表示渲染后的 1.1 模板内容，`installed_sha256` 表示实际安装/合并结果；两者不同表示安装时保留了用户定制。收据只描述 Forge 覆盖层，不接管上游 Trellis 哈希。收据在所有文件写入成功后作为事务最后一步落盘；失败回滚时恢复旧收据或删除新收据。

## 迁移清单与 1.0 基线

迁移资产自包含，不依赖运行机器的 Git 历史或网络。历史 `old` 基线从已标记 1.0 的提交 `e40a942` 直接提取，并在提交进迁移目录前做内容和哈希审核。提取必须忠实保留历史文件内容；当前工作树后续发生的空白规范化不得回写或重新生成 `old` 资产。

文件动作分为：

- `merge`：1.0 Forge 已管理且 1.1 修改的文件，例如模板 workflow 和 channel worker 卡；
- `adopt`：1.0 Forge 未发布、但 Trellis 0.6.10 已在下游生成的 `trellis-channel` Skill。`old` 取自同一 1.0 提交中的上游文件，`current` 是下游现有文件，`new` 取当前 1.1 模板；
- `add`：1.1 新增且 1.0/上游均无对应文件，例如新的模板契约测试。

迁移清单路径使用模板相对路径，可包含 `__PROJECT_PREFIX__`。每个 `merge`/`adopt` 项引用迁移目录内的旧基线和当前模板源，并记录两者规范化内容哈希；`add` 项只引用新模板及哈希。这里的内容规范化只统一 LF/CRLF 换行序列，不裁剪行尾空白、尾部空行或其他内容。执行前验证清单 schema、版本、路径唯一性、路径边界和资产哈希，任何异常均为 `unsupported` 并停止。

对子任务 1 交接的 `command-reference.md`，`old` 必须保留 `e40a942` 中的历史尾部空行；`new` 使用包含新增公共规则且没有该多余空行的 1.1 模板。这样，未定制的 1.0 下游文件与 `old` 相等，三方合并会把规则新增和空行删除视为 1.1 变化，而不是用户修改。当前根目录只读参考中的多余空行另行清理，且不能用于重建 `old`。该仓库维护变更实施前先运行 `trellis update --dry-run`，只做已知空白规范化，不修改根目录工作流语义。

## 升级入口与参数

`tools/update-embedded-c-overlay.ps1` 支持：

```powershell
# 1.0 没有收据；省略 FromVersion 时默认按 1.0 预检
& .\tools\update-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -ProjectPrefix example `
  -ProjectName "Example Firmware"

# 预检无冲突后应用
& .\tools\update-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -FromVersion 1.0 `
  -ProjectPrefix example `
  -ProjectName "Example Firmware" `
  -Apply
```

默认模式只预检。已有有效收据时，版本和项目参数从收据读取；调用方同时传参时必须一致。没有收据且未提供项目参数时拒绝执行。收据已为 1.1 时报告 `already-current` 并以成功状态退出。

无收据且省略 `-FromVersion` 时，来源版本默认为 `1.0`；这只是选择 1.0→1.1 迁移清单的默认值，不跳过兼容性验证。无收据时 `ProjectPrefix` 和 `ProjectName` 仍为必填，因为目标仓库中没有可靠的统一来源可还原原安装参数。显式传入其他来源版本、目标结构无法按 1.0 基线预检或三方合并无法成立时，以 `unsupported` 停止。

## 预检算法

1. 验证仓库、`.trellis/`、Git、版本文件、迁移清单和参数/收据。
2. 渲染清单中的旧基线、新模板路径和正文，校验资产哈希；统一换行序列时保留所有行尾空白和尾部空行。
3. 对 `merge`/`adopt` 文件构造 old/current/new 三方输入，调用 `git merge-file --stdout`：退出码 0 为可合并，1 为冲突，其他值为工具错误。
4. 对 `add` 文件：缺失为 `add`；内容已等于新模板为 `already-current`；其他既有内容为 `conflict`。
5. 将干净三方结果分为：current 等于结果则 `already-current`，无用户差异的替换为 `update`，保留用户差异的结果为 `user-merged`。
6. 汇总所有路径后再决定结果，不能遇到首个可写文件就开始修改。

预检每次从目标当前状态重新计算；`-Apply` 不复用旧报告，而是在同一进程内重新完成预检，防止预检后文件变化。

## 冲突处理

任一 `conflict` 或 `unsupported` 都阻止整次工作树写入。工具通过 `git rev-parse --path-format=absolute --git-path trellisforge-upgrade` 取得 Git 元数据根，在唯一运行目录中写入：

```text
trellisforge-upgrade/<时间戳>-<GUID>/
  report.json
  report.txt
  candidates/<目标相对路径>
```

三方冲突的 candidate 保存带清晰 old/current/new 标签的冲突结果；新增文件冲突的 candidate 保存 1.1 候选内容。报告记录版本、参数摘要、状态、相对路径和建议动作，不复制无关项目文件。生成这些诊断材料不算修改工作树，也不创建 1.1 收据。

用户根据报告手工解决目标文件后重新运行默认预检。升级器不提供忽略冲突或部分应用参数。

## 应用事务与回滚

全部路径预检通过后，`-Apply` 才进入事务：

1. 生成完整写入计划并再次确认所有目标路径仍在仓库根内。
2. 在 `.git/trellisforge-backup/<时间戳>-<GUID>/` 备份每个将修改的既有文件和旧收据。
3. 写 `backup-manifest.json`，包含 schema、from/to、动作、旧 SHA-256、新增路径和收据状态。
4. 从临时输出原子替换目标文件，新增缺失文件。
5. 重新计算实际结果哈希并写 1.1 收据。
6. 验证写入结果与计划一致后报告成功。

任何步骤失败都按备份恢复既有文件与旧收据，删除本次新增文件和新收据，并以非零状态退出。回滚错误与原始错误分别报告；不能把不完整状态宣告为成功。

升级器不要求整个 Git 工作树干净，也不触碰无关脏文件；报告会提示用户先提交或保存现有改动。所有将修改的受管文件无论是否已提交都纳入备份和三方合并。

## 首次安装流程

现有安装器保留参数和无 `-Force` 冲突预览行为，内部改用共享模块。`-Force` 应继续备份所有将覆盖的既有文件，再安装当前完整模板、生成 `AGENTS.md.trellisforge-template` 并写 1.1 收据。收据也进入冲突检测和事务回滚；已有不兼容收据时拒绝把首次安装伪装成升级。

安装器不自动合并用户 `AGENTS.md`，不删除目标文件，不复制 `TEMPLATE-CONTENTS.md`、任务、workspace、runtime 或上游模板哈希。

## 文档设计

README 改为稳定的项目入口：

1. 项目定位、当前 Forge 1.1 与 Trellis 0.6.10 基线；
2. 首次接入和 1.0→1.1 两个最短命令；
3. 当前能力摘要，包括规划门禁、代理上下文、执行计划、审查合同和 Channel 唯一等待；
4. 仓库目录与安装/迁移/模板交付物；
5. 安全边界、验证入口和详细指南链接。

接入指南拆成“首次接入 1.1”“Forge 1.0→1.1”“上游 Trellis 更新”三个章节。升级章节解释预检状态、冲突材料、手工解决后重试、`-Apply`、备份位置、收据和升级后验证。`TEMPLATE-CONTENTS.md` 精确列出完整 Channel Skill，并说明收据由脚本生成而非静态模板复制。

## 验证设计

新增 `tests/test_overlay_tools.py`，用 Python `unittest` 创建隔离临时 Git 仓库并调用 Windows PowerShell 5.1。测试夹具从 1.0 migration baseline 和 1.1 template 构建目标，不依赖开发者真实项目。

核心场景：

- 首次安装预览、`-Force` 备份、完整 1.1 文件、占位符与收据；
- 干净 1.0 预检/应用和二次运行幂等；
- 非重叠用户定制三方合并；
- `command-reference.md` 的历史 1.0 尾部空行与 1.1 新增规则/空行删除可无冲突迁移，并能区分真实用户修改；
- 同行/同段冲突时工作树零写入及 candidate/report；
- 新增路径已存在且不同；
- 参数/收据/版本/清单/哈希不一致；
- LF 与 CRLF；
- 路径逃逸、目录冲突、模板缓存；
- 注入式写入失败后的覆盖恢复、新增清理和收据恢复。

验证命令同时包含现有 `.trellis/scripts/tests`、模板内测试、`tests/` 工具测试、Python 语法、PowerShell 解析、缓存/占位符扫描和 `git diff --check`。本仓库没有构建、部署或硬件目标。

## 审查策略

Review level 为 `standard`。实施完成后派发一次独立 affected-scope 审查，覆盖完整任务 diff、工具模块、两个入口、迁移资产、文档、测试、直接调用关系和全部验收项。修复后由主会话重跑受影响检查；只有任务范围实质变化时才重新派发完整独立审查。
