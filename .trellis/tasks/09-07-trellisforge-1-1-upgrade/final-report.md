# TrellisForge 1.1 电梯模型重构最终报告

## 概述

按 implement.md 步骤 1-7 完成「方案 A → 电梯模型」重构。放弃逐对迁移
（`migrations/embedded-c-overlay/1.0-to-1.1/` 的 `baseline/` + `new/` +
`migration.json`），改为 Forge 侧 canonical 内容库 + 版本 manifest + 一次性
1.0 入场适配 + 线性结构迁移链 + 三类哈希收据（`canonical_sha256` /
`baseline_sha256` / `installed_sha256`）。首次安装器与 1.0→1.1 升级器共享
`tools/lib/TrellisForgeOverlay.psm1` 的安全/事务机制。版本事实源为根目录
`VERSION`（`1.1`），上游 Trellis 基线独立标识为 `0.6.10`；本任务未升级上游
Trellis、未修改 `.trellis/.version` 与 `.trellis/.template-hashes.json`、未创建
tag、未推送 release。独立审查（implement.md 步骤 8）由主会话派发
`trellis-check` 完成，不在本实施代理职责内。

## 变更文件

新增：

- `VERSION` — TrellisForge 版本事实源，内容 `1.1`（保持既有）。
- `history/embedded-c-overlay/objects/` — canonical 对象库，按 SHA-256 去重
  保存 UTF-8 无 BOM、LF 的版本正文（90 个去重对象）。
- `history/embedded-c-overlay/versions/1.0/manifest.json` — 1.0 版本清单：
  75 个 `managed` + 12 个 `adoption-baseline`（trellis-channel skill，canonical
  直接取自提交 `e40a942` 根目录，`command-reference.md` 忠实保留历史尾部空行）
  + `AGENTS.md.trellisforge-template` = 88 条。
- `history/embedded-c-overlay/versions/1.1/manifest.json` — 1.1 版本清单：88 个
  `managed`（canonical 取自已提交的 live 模板，含子任务 1 新增的
  “Standard dispatch use…”规则且无多余尾部空行）+ `AGENTS.md.trellisforge-template`
  = 89 条。
- `migrations/embedded-c-overlay/structural/1.0-to-1.1.json` — 线性结构迁移链：
  schema 1、`from_version=1.0`、`to_version=1.1`、
  `receipt_transition=bootstrap-schema-1`、`actions=[]`。
- `tools/update-embedded-c-overlay.ps1` — 电梯模型升级器（默认预检、`-Apply`
  应用、1.0 无收据入场、冲突整次 fail closed、三类哈希收据）。
- `tests/fixtures/build_10.py` — 从 1.0 manifest + canonical 对象库构建 1.0
  目标的夹具。
- 任务目录 `gen_migration.py` / `verify_assets.py` — 替换方案 A 生成/校验工具，
  生成并校验电梯模型资产。

修改：

- `tools/lib/TrellisForgeOverlay.psm1` — 共享模块重构到电梯模型：新增
  `Get-OverlayVersionManifest`、`Get-OverlayCanonicalText`、
  `Get-OverlayStructuralChain`、`Assert-OverlayLiveTemplateMatchesManifest`、
  `Get-OverlayHistoryRoot`、`Get-OverlayStructuralDir`；移除方案 A 的
  `Get-OverlayMigrationManifest` / `Resolve-OverlayAssetPath`；收据改为三类哈希；
  保留路径/Git 元数据校验、渲染、LF/CRLF、SHA-256、备份清单、原子事务回滚。
- `tools/install-embedded-c-overlay.ps1` — 首次安装器：安装前校验 live 模板与
  1.1 manifest/canonical 对象一致，安装 89 个受管文件并写三类哈希收据；保留
  `-TargetRoot/-ProjectPrefix/-ProjectName/-Force` 与既有安全语义。
- `tests/test_overlay_tools.py` — 29 个临时 Git 仓库自动化测试，移除方案 A
  baseline/new/migration.json 依赖，基于电梯模型资产。
- `README.md` — 目录/交付物更新为 history 对象库 + 版本 manifest + 结构迁移链，
  升级描述改为电梯模型与三类哈希收据。
- `docs/接入指南.md` — 首次接入/1.0→1.1/上游 Trellis 三节更新：canonical old
  三方合并、adoption-baseline 接管、结构链预演、三类哈希收据与冲突材料。
- `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` — 移除 baseline/new
  描述，改为接管合并、history/objects 交付物与脚本生成收据边界。

删除（git 已提交历史保留）:

- `migrations/embedded-c-overlay/1.0-to-1.1/`（`migration.json`、`baseline/`、
  `new/`）— 方案 A 逐对迁移资产，等价性验证完成后删除，工作树仅一套升级资产源。

## 阶段结果

| 阶段 | 结果 | 说明 |
| --- | --- | --- |
| discover-baseline | completed | 固定 e40a942、盘点 75→88 模板差异（13 新增/3 merge/0 删除）、交接差异三态确认、trellis update --dry-run 记录 |
| elevator-assets | completed | history 对象库 90 对象 + 1.0/1.1 manifest + 结构迁移链生成，方案 A 遗留删除，verify_assets 全通过 |
| shared-module | completed | 模块重构电梯模型，PS 5.1 解析零错误，27 个契约函数，manifest/canonical/结构链冒烟通过 |
| installer-11 | completed | 安装器重构，live 模板一致性校验，89 文件三类哈希收据，占位符零残留，状态文件保护 |
| updater-11 | completed | 升级器预检/应用/幂等/冲突零写入/自定义合并全部验证通过 |
| overlay-tests | completed | 29/29 测试通过（安装/升级/冲突/幂等/LF/CRLF/回滚/路径/历史对象） |
| docs-11 | completed | README/指南/TEMPLATE-CONTENTS 版本与命令一致 |
| verify-final | completed | 见下方检查结果 |

## 检查结果（verify-final）

| 检查 | 结果 | 命令/证据 |
| --- | --- | --- |
| dot-trellis-unittest | pass | `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` → 89 tests OK |
| template-unittest | pass | `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` → 99 tests OK |
| overlay-unittest | pass | `python -B -m unittest discover -s tests -p "test_*.py"` → 29 tests OK |
| py-compile | pass | `python -m py_compile` 覆盖 `.trellis/scripts`、`.claude/hooks`、`.codex/hooks`、模板与 `tests` 全部 Python 文件 |
| ps-parse-all | pass | Windows PowerShell 5.1 `Parser::ParseFile`：模块 + 两个入口零错误 |
| installer-smoke | pass | 临时 Git 仓库安装：`trellisforge_version=1.1`、`overlay=embedded-c`、89 文件三类哈希收据 |
| updater-smoke | pass | 临时 1.0 布局预检 + `-Apply` 成功、收据 1.1 files=89、command-reference 含规则且尾部 `**.\n` |
| cache-residue-scan | pass | 清理全部 91 个 `__pycache__`/`.pyc`/`.pyo` 后零残留 |
| asset-version-consistent | pass | VERSION=1.1 与 1.0/1.1 manifest、canonical 对象、结构链、收据三类哈希一致；无 Plan-A 遗留；模板无禁止运行时路径 |
| git-diff-check | pass | 本次交付文件 `git diff --check` 零空白错误 |

跳过项（not applicable）：

- 构建、部署、硬件验证：本仓库无固件目标或硬件设备，报告为 `not applicable`。
- 下游项目真实构建与硬件验证：由接入者升级后自行执行。
- 标准独立审查（implement.md 步骤 8）：由主会话派发 `trellis-check` 完成，
  不在本实施代理职责内。

## 关键验收覆盖

- 干净 1.0 升级：canonical 相同的受管路径保持工作树不变，变化的
  managed/adoption-baseline 路径以 canonical old 做三方合并，新增文件分类为
  add；`command-reference.md` 从含历史尾部空行的 1.0 canonical 升级为含
  “Standard dispatch use…”规则、无多余空行的 1.1 内容，零虚假冲突。
- 非重叠用户定制：`user-merged` 保留用户修改；重叠修改触发 `conflict`，
  工作树零写入，`.git/trellisforge-upgrade/<时间戳>-<GUID>/` 生成
  report.json/report.txt 与 candidates/，路径可定位相对路径。
- 新增文件冲突：目标已存在且内容不同 → `conflict`，不静默覆盖。
- 1.0 无收据入场：省略 `-FromVersion` 默认 1.0，仍强制显式项目参数，并经
  完整 manifest/canonical/结构链/三方合并预检；无法验证以 `unsupported` 停止。
- 参数/收据冲突：fail closed，不猜测项目名称、前缀或来源版本。
- 幂等：二次升级识别为 `already-current` 并安全退出。
- LF 与 CRLF 目标：均无虚假冲突，CRLF 换行风格在合并输出中保留。
- 路径逃逸、目录冒充文件、模板缓存、前缀非法：均被拒绝。
- 写入失败回滚：恢复已覆盖文件、删除本次新增文件并恢复/移除收据。
- 安装器与升级器都不修改 `.trellis/.version`、`.trellis/.template-hashes.json`，
  不删除目标文件，不复制运行时状态。

## 已知风险与说明

1. 预检失败时的控制台消息为中文；Windows PowerShell 5.1 原生输出经管道捕获时
   按系统 OEM 代码页编码，自动化测试因此以退出码与 ASCII 标记（`[CONFLICT]`、
   `[USER-MERGED]`、`already-current`、`unsupported`）断言，冲突详情以
   `report.txt`/`report.json` 为准。
2. `tools/*.ps1`、`tools/lib/*.psm1` 与 `tests/` 下的 PowerShell 驱动保持
   Windows PowerShell 5.1 兼容并带 UTF-8 BOM；模块写入的下游内容仍为
   UTF-8 无 BOM。
3. `.trellis/tasks/09-07-trellisforge-1-1-upgrade/task.json` 的既有尾随空白为
   主会话（`0ff4ede` 后工作树更新）的 Trellis 运行时状态内容，由任务系统
   维护，不属于本任务交付；按要求未手工改动。
4. 电梯模型资产契约：1.0 manifest 的 `adoption-baseline` canonical 直接从
   `e40a942` 提取，1.1 manifest 的 canonical 从已提交的 live 模板生成；任何
   模板内容变化必须提升 Forge 版本并重新生成 manifest/对象，不得改写同一版本
   历史对象。对象库 `history/embedded-c-overlay/objects/` 按版本 manifest
   引用独立保存，旧版本 object 在所有引用版本停止支持前不清除。
5. 结构迁移链当前为空 actions（1.0→1.1 无改名/删除）；未来正文合并无法表达
   的结构变化必须显式加入相邻版本步骤，不能由 manifest 差异暗中推断。