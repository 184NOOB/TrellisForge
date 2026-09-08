# TrellisForge 1.1 首次接入与 1.0 升级设计

## 目标与边界

本设计提供两条明确分开的交付路径：新项目使用安装器安装 TrellisForge 1.1；已接入 1.0 的项目使用一次性入场适配进入电梯模型并迁移到 1.1。两条路径共享安全基础设施，但不能互相替代。安装器仍可覆盖 `trellis init` 产生的上游基线；升级器使用当前 1.1 模板作为唯一目标，历史版本正文从 Forge 侧 canonical 内容库取得。

本任务不升级上游 Trellis、不修改下游业务代码、不维护 1.0 之外的迁移路径，也不发布 Git tag 或远端 release。

## 交付结构

```text
VERSION
tools/
  lib/TrellisForgeOverlay.psm1
  install-embedded-c-overlay.ps1
  update-embedded-c-overlay.ps1
history/embedded-c-overlay/
  objects/<sha256>
  versions/1.0/manifest.json
  versions/1.1/manifest.json
migrations/embedded-c-overlay/
  structural/1.0-to-1.1.json
tests/
  test_overlay_tools.py
templates/embedded-c-overlay/
  ... 1.1 模板源
docs/接入指南.md
README.md
```

`VERSION` 是仓库内 TrellisForge 版本事实源，内容为 `1.1`。每个版本 manifest 保存覆盖层类型、上游 Trellis 基线、完整受管路径、路径所有权、canonical 对象引用和内容 SHA-256；其受管清单必须使用与安装器相同的包含/排除规则，不能把 `TEMPLATE-CONTENTS.md` 或运行时状态误列为下游文件。当前 1.1 manifest 还用于验证 live 模板没有在同一版本内漂移。结构迁移清单只保存需要按顺序执行的结构动作。测试锁定 VERSION、manifest、README 和脚本输出的版本一致性。

版本 manifest 使用以下核心结构；`canonical_sha256` 同时是对象标识，对象路径固定推导为 `objects/<canonical_sha256>`，不再保存重复路径字段：

```json
{
  "schema_version": 1,
  "overlay": "embedded-c",
  "trellisforge_version": "1.0",
  "trellis_version": "0.6.10",
  "render_tokens": ["PROJECT_PREFIX", "PROJECT_NAME", "__PROJECT_PREFIX__"],
  "files": [
    {
      "path": ".trellis/workflow.md",
      "ownership": "managed",
      "canonical_sha256": "..."
    },
    {
      "path": ".agents/skills/trellis-channel/SKILL.md",
      "ownership": "adoption-baseline",
      "canonical_sha256": "..."
    }
  ]
}
```

1.1 manifest 只使用 `managed`；`adoption-baseline` 只出现在尚未由 Forge 管理、但后续版本需要安全接管的来源版本中。manifest 文件数组按规范化相对路径排序，生成器对路径重复、大小写碰撞、缺失对象、未知所有权和未声明占位符 fail closed。

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
      "canonical_sha256": "...",
      "baseline_sha256": "...",
      "installed_sha256": "..."
    }
  ]
}
```

`canonical_sha256` 是渲染前对象的稳定标识，`baseline_sha256` 是按项目参数渲染后的 canonical 内容哈希，`installed_sha256` 是实际安装或合并结果哈希；后二者不同表示结果保留了用户定制或目标本来存在差异。升级器通过版本 manifest、路径和 `canonical_sha256` 定位 old，不把对象目录路径固化进收据。三方合并始终使用 canonical baseline 作为 old，不能使用包含用户定制的 installed 内容作为祖先。收据只描述 Forge 覆盖层，不接管上游 Trellis 哈希。收据在所有文件写入成功后作为事务最后一步落盘；失败回滚时恢复旧收据或删除新收据。

## 电梯模型与历史内容库

升级资产自包含，不依赖运行机器的 Git 历史或网络。`history/embedded-c-overlay/objects/` 按正文 SHA-256 去重保存 canonical 模板对象，`versions/<version>/manifest.json` 记录路径、所有权、对象引用、渲染规则和上游基线。1.0 对象直接从已标记提交 `e40a942` 提取；提取必须忠实保留历史文件内容，当前工作树后续发生的空白规范化不得回写 1.0 对象。

manifest 条目和升级动作分为：

- `managed`：来源和目标版本都由 Forge 管理的文件，按 canonical old/current/new 做三方合并；
- `adoption-baseline`：来源版本由 Trellis 生成、目标版本由 Forge 接管的文件，来源 manifest 提供 canonical old；
- `add`：目标版本新增且来源没有 canonical old 的文件，目标不存在时加入，已有不同内容时冲突；
- `structural`：无法由正文合并表达的改名、删除、目录、所有权和收据 schema 动作，只能由线性结构迁移脚本处理。

路径使用模板相对路径，可包含 `__PROJECT_PREFIX__`。对象以 UTF-8 无 BOM、LF 换行的 canonical 字节保存，SHA-256 对这些字节计算；规范化只统一 LF/CRLF 换行序列，不裁剪行尾空白、尾部空行或其他内容。收据的 baseline/installed 哈希也按相同规范化算法计算，使换行风格本身不构成用户漂移。执行前验证 manifest schema、版本、路径唯一性、路径边界、对象引用和哈希；任何异常均为 `unsupported` 并停止。当前 1.1 模板必须与 1.1 manifest 对应对象一致，否则升级器拒绝继续，防止同一版本 live 模板漂移。

升级器先比较来源和目标两个完整 manifest，导出本次受影响集合：canonical 对象相同的 `managed` 路径不写工作树，只读取当前内容供新收据记录；对象变化的路径才执行三方合并；目标新增路径执行 `add`；`adoption-baseline` 执行接管合并。来源存在而目标缺失的路径必须有显式结构迁移动作，否则以 `unsupported` 停止，1.0→1.1 不包含删除目标文件的动作。

`migrations/embedded-c-overlay/structural/1.0-to-1.1.json` 是线性结构链的首个审计步骤。当前版本没有文件改名或删除，因此 `actions` 为空，只声明 `from_version`、`to_version`、schema 和收据 bootstrap；执行器仍验证链连续性和动作白名单。未来结构动作必须在对应相邻版本步骤中显式加入，不能由文件 manifest 差异暗中推断 destructive 操作。

```json
{
  "schema_version": 1,
  "from_version": "1.0",
  "to_version": "1.1",
  "receipt_transition": "bootstrap-schema-1",
  "actions": []
}
```

对象库会保存当前 1.1 的 canonical 内容，因为它们在下一个版本中就是可合并的 old；每个不同正文只保存一次。这里允许 live 模板与对象库各有一份当前内容，但不会像逐对迁移矩阵那样为每个受支持的 from 重复保存同一 target 快照。

对子任务 1 交接的 `command-reference.md`，1.0 对象必须保留 `e40a942` 中的历史尾部空行；1.1 manifest 与当前模板使用包含新增公共规则且没有该多余空行的内容。未定制的 1.0 下游文件与历史对象相等，三方合并会把规则新增和空行删除视为版本变化，而不是用户修改。当前根目录参考中的多余空行已在 `11b16b9` 清理，不能用于重建 1.0 对象；实施前仍运行 `trellis update --dry-run` 核对上游管理状态，不再重复修改该文件。

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

默认模式只预检。已有有效收据时，来源版本、项目参数和每文件 canonical baseline 从收据读取；调用方同时传参时必须一致。没有收据且未提供项目参数时拒绝执行。收据已为 1.1 时报告 `already-current` 并以成功状态退出。

无收据且省略 `-FromVersion` 时，来源版本默认为 `1.0`；这只是进入历史 manifest 和结构适配链的默认值，不跳过兼容性验证。无收据时 `ProjectPrefix` 和 `ProjectName` 仍为必填，因为目标仓库中没有可靠的统一来源可还原原安装参数。显式传入其他来源版本、历史对象缺失、目标结构无法完成线性适配或三方合并无法成立时，以 `unsupported` 停止。

## 预检算法

1. 验证仓库、`.trellis/`、Git、版本文件、来源/目标 manifest、对象库、结构迁移链和参数/收据。
2. 解析来源版本；有有效收据时读取其 canonical baseline，无收据时进入显式或默认的 1.0 入场适配。
3. 校验历史对象、当前 1.1 模板和目标 manifest 哈希；统一换行序列时保留所有行尾空白和尾部空行。
4. 比较来源/目标完整 manifest 并导出受影响集合；canonical 对象相同的路径不进入写入计划，但读取当前规范化哈希供收据记录。
5. 先在临时目录预演线性结构迁移，验证路径和收据 schema，再对 canonical 对象变化的 `managed` 路径及 `adoption-baseline` 路径构造 old/current/new 三方输入，调用 `git merge-file --stdout`：退出码 0 为可合并，1 为冲突，其他值为工具错误。
6. 对 `add` 文件：缺失为 `add`；内容已等于当前模板为 `already-current`；其他既有内容为 `conflict`。
7. 将干净三方结果分为 `already-current`、`update` 或 `user-merged`，汇总所有路径后再决定结果，不能遇到首个可写文件就开始修改。

预检每次从目标当前状态重新计算；`-Apply` 不复用旧报告，而是在同一进程内重新完成预检，防止预检后文件变化。

## 冲突处理

任一 `conflict` 或 `unsupported` 都阻止整次工作树写入。工具通过 `git rev-parse --path-format=absolute --git-path trellisforge-upgrade` 取得 Git 元数据根，在唯一运行目录中写入：

```text
trellisforge-upgrade/<时间戳>-<GUID>/
  report.json
  report.txt
  candidates/<目标相对路径>
```

三方冲突的 candidate 保存带清晰 old/current/new 标签的冲突结果；新增文件冲突的 candidate 保存当前 1.1 候选内容。结构迁移失败的报告记录具体迁移动作和恢复建议。报告记录来源/目标版本、参数摘要、状态、相对路径和建议动作，不复制无关项目文件。生成这些诊断材料不算修改工作树，也不创建 1.1 收据。

用户根据报告手工解决目标文件后重新运行默认预检。升级器不提供忽略冲突或部分应用参数。

## 应用事务与回滚

全部路径预检通过后，`-Apply` 才进入事务：

1. 生成完整写入计划并再次确认所有目标路径仍在仓库根内，同时确认当前模板仍与目标 manifest 一致。
2. 在 `.git/trellisforge-backup/<时间戳>-<GUID>/` 备份每个将修改的既有文件和旧收据。
3. 写 `backup-manifest.json`，包含 schema、from/to、动作、旧 SHA-256、新增路径和收据状态。
4. 从临时输出原子替换目标文件，新增缺失文件。
5. 重新计算 canonical 对象、渲染后 baseline 和实际结果哈希，写 schema 1 的 1.1 收据。
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

重构现有 `tests/test_overlay_tools.py`，用 Python `unittest` 创建隔离临时 Git 仓库并调用 Windows PowerShell 5.1。测试夹具从 1.0 历史对象、1.1 manifest 和当前模板构建目标，不依赖开发者真实项目。

核心场景：

- 首次安装预览、`-Force` 备份、完整 1.1 文件、占位符与收据；
- 干净 1.0 预检/应用和二次运行幂等；
- 1.0 无收据入场后生成 schema 1 收据，后续基于 canonical baseline 继续升级；
- 来源/目标 manifest 中 canonical 对象相同的文件保持字节不变，即使其中存在用户定制；新收据仍准确记录 baseline 与 installed 哈希；
- 非重叠用户定制三方合并；
- `command-reference.md` 的历史 1.0 尾部空行与 1.1 新增规则/空行删除可无冲突迁移，并能区分真实用户修改；
- 同行/同段冲突时工作树零写入及 candidate/report；
- 新增路径已存在且不同；
- 参数/收据/版本/清单/哈希不一致；
- LF 与 CRLF；
- 路径逃逸、目录冲突、模板缓存；
- 历史对象缺失、manifest 哈希错误、同一版本 live 模板漂移和结构迁移链失败；
- 空的 1.0→1.1 结构步骤、链不连续、未知动作和来源有路径但目标无路径且缺少显式动作；
- 注入式写入失败后的覆盖恢复、新增清理和收据恢复。

验证命令同时包含现有 `.trellis/scripts/tests`、模板内测试、`tests/` 工具测试、Python 语法、PowerShell 解析、缓存/占位符扫描和 `git diff --check`。本仓库没有构建、部署或硬件目标。

## 审查策略

Review level 为 `standard`。实施完成后派发一次独立 affected-scope 审查，覆盖完整任务 diff、工具模块、两个入口、历史 manifest/对象库、结构迁移链、文档、测试、直接调用关系和全部验收项。修复后由主会话重跑受影响检查；只有任务范围实质变化时才重新派发完整独立审查。
