# TrellisForge 1.1 升级最终报告

## 概述

TrellisForge 1.1 交付完成：新项目通过 `tools/install-embedded-c-overlay.ps1` 安装
完整 1.1 覆盖层并写入 `.trellis/trellisforge.json` 收据；1.0 项目通过
`tools/update-embedded-c-overlay.ps1` 做版本化升级（默认预检、显式 `-Apply`
应用、三方合并、冲突零写入、备份回滚、幂等退出）。版本事实源为根目录
`VERSION`（`1.1`），上游 Trellis 基线独立标识为 `0.6.10`，本任务未升级上游
Trellis、未创建 tag、未推送 release。

## 变更文件

新增：

- `VERSION` — TrellisForge 版本事实源，内容 `1.1`。
- `migrations/embedded-c-overlay/1.0-to-1.1/migration.json` — 版本化迁移清单，
  记录 from/to 版本、overlay、Trellis 基线、16 个受管路径的动作（merge=3、
  adopt=12、add=1）与 old/new 的 LF 规范化内容 SHA-256。
- `migrations/embedded-c-overlay/1.0-to-1.1/baseline/` — 从提交 `e40a942` 忠
  实提取的 15 个 1.0 旧基线文件；`command-reference.md` 保留历史尾部空行。
- `tools/lib/TrellisForgeOverlay.psm1` — 安装器与升级器共享模块（路径/参数安
  全、渲染、LF/CRLF 规范化与哈希、Git 元数据备份与清单、原子事务与回滚、收
  据读写、迁移清单加载与哈希校验、`git merge-file` 三方文本合并）。
- `tools/update-embedded-c-overlay.ps1` — 1.0→1.1 版本化升级器。
- `tests/test_overlay_tools.py` — 22 个临时 Git 仓库自动化测试。
- `.trellis/tasks/09-07-trellisforge-1-1-upgrade/gen_migration.py`、
  `verify_assets.py` — 迁移清单生成/校验工作脚本（任务目录审计产物）。

修改：

- `tools/install-embedded-c-overlay.ps1` — 重构为共享模块；保留
  `-TargetRoot/-ProjectPrefix/-ProjectName/-Force` 与既有安全语义；成功安装
  后写 1.1 收据并纳入事务回滚。
- `README.md` — 重构为当前工程入口（定位与非目标、版本兼容、首次接入与
  1.0 升级最短命令、当前能力含 Channel 唯一等待、目录与交付物、验证/安全
  边界、非目标），压缩历史修复叙述。
- `docs/接入指南.md` — 分成“首次接入 1.1”“从 1.0 升级到 1.1”“升级上游
  Trellis”三章，命令使用 Windows PowerShell 语法。
- `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` — 列出完整
  trellis-channel Skill、脚本生成的安装收据与版本化迁移交付物归属。
- `.agents/skills/trellis-channel/references/command-reference.md`、
  `.claude/skills/trellis-channel/references/command-reference.md` — 仓库维护
  空白规范化：去掉历史多余尾部空行（先于清理提取 1.0 old 资产，历史资产未被
  改写）。

## 阶段结果

| 阶段 | 结果 | 说明 |
| --- | --- | --- |
| discover-baseline | completed | 固定 e40a942、盘点 16 个 1.0→1.1 模板差异、`trellis update --dry-run` 记录 |
| version-migration-assets | completed | VERSION + 迁移资产 + 根参考空白清理全部校验通过 |
| shared-module | completed | 模块解析零错误、导出 20 个契约函数，核心机制冒烟通过 |
| installer-11 | completed | 安装器重构、89 个受管文件、收据、占位符零残留 |
| updater-11 | completed | 升级器预检/应用/冲突/幂等/CRLF 全部验证通过 |
| overlay-tests | completed | 22/22 测试通过 |
| docs-11 | completed | README/指南/TEMPLATE-CONTENTS 版本与命令一致 |
| verify-final | completed | 见下方检查结果 |

## 检查结果（verify-final）

| 检查 | 结果 | 命令/证据 |
| --- | --- | --- |
| dot-trellis-unittest | pass | `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` → 89 tests OK |
| template-unittest | pass | `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` → 99 tests OK |
| overlay-unittest | pass | `python -B -m unittest discover -s tests -p "test_*.py"` → 22 tests OK |
| py-compile | pass | `python -m py_compile` 覆盖 `.trellis/scripts`、`.claude/hooks`、`.codex/hooks`、模板与 `tests` 全部 Python 文件 |
| ps-parse-all | pass | PowerShell 5.1 `Parser::ParseFile`：模块 + 两个入口零错误（文件为 UTF-8 带 BOM） |
| installer-smoke | pass | 临时 Git 仓库安装：`trellisforge_version=1.1`、`overlay=embedded-c` |
| updater-smoke | pass | 临时 1.0 布局预检通过 + `-Apply` 成功、收据 1.1、command-reference 含规则 |
| cache-residue-scan | pass | 清理所有 `__pycache__`/`.pyc`/`.pyo`（81 个残留清零），模板树无缓存 |
| migration-version-consistent | pass | VERSION=1.1 与 migration.json from/to（1.0→1.1）一致，迁移目录不含 tasks/workspace/runtime/template-hashes |
| git-diff-check | pass | 本次交付文件 `git diff --check` 零空白错误 |

跳过项（not applicable）：

- 构建、部署、硬件验证：本仓库无固件目标或硬件设备，报告为 `not applicable`。
- 下游项目真实构建与硬件验证：由接入者升级后自行执行。
- 标准独立审查（implement.md 步骤 8）：由主会话派发 `trellis-check` 完成，
  不在本实施代理职责内。

## 关键验收覆盖

- 干净 1.0 升级：16 个受管路径为 update/add（无变化文件 already-current），
  `command-reference.md` 从含历史尾部空行的 1.0 形态升级为含“Standard
  dispatch use…”规则、无多余空行的 1.1 形态，零冲突。
- 非重叠用户定制：`user-merged` 保留用户修改；同区域/插入边界修改触发
  `conflict`，工作树零写入，`.git/trellisforge-upgrade/<时间戳>-<GUID>/` 生成
  report.json/report.txt 与 candidates/，路径可定位到相对路径。
- 新增文件冲突：目标已存在且内容不同 → `conflict`，不静默覆盖。
- 幂等：二次升级识别为 `already-current` 并安全退出。
- 错误来源版本（`0.9`）与缺失项目参数：无条件 `unsupported`/fail closed。
- 收据/参数冲突：fail closed，不猜测项目名称、前缀或来源版本。
- 无收据且省略 `-FromVersion` 默认按 1.0 迁移候选，且仍要求显式项目参数。
- LF 与 CRLF 目标：均无虚假冲突，CRLF 换行风格在合并输出中保留。
- 路径逃逸、目录冒充文件、模板缓存、前缀非法：均被拒绝。
- 写入失败回滚：读只读文件导致的失败恢复已覆盖文件、删除本次新增文件并恢复/
  移除收据。
- 安装器与升级器都不修改 `.trellis/.version`、`.trellis/.template-hashes.json`，
  不删除目标文件，不复制运行时状态。

## 已知风险与说明

1. 预检失败时的控制台消息为中文；Windows PowerShell 5.1 原生输出经管道捕获时
   按系统 OEM 代码页编码，自动化测试因此以退出码与 ASCII 标记（`[CONFLICT]`、
   `already-current`、`unsupported`）断言，冲突详情以 `report.txt`/`report.json`
   为准。
2. `tools/*.ps1` 与 `tools/lib/*.psm1` 为 Windows PowerShell 5.1 兼容并带 UTF-8
   BOM；模块写入的下游内容仍为 UTF-8 无 BOM。
3. `.trellis/tasks/09-07-trellisforge-1-1-upgrade/task.json` 的既有尾部空白为
   Trellis 运行时状态文件内容（本会话开始前已存在、由任务系统维护），不属于
   本任务交付；按要求未手工改动。
4. 迁移清单的 `new` 引用解析自当前模板树并校验内容哈希；后续任何模板文件
   变更都会使对应 `new_sha256` 失效，需同步更新迁移清单与测试（migration 资产
   是版本化的，不应被静默漂移）。