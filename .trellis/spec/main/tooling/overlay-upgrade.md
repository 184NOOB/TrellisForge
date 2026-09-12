# 覆盖层升级架构（电梯模型）

本文件定义 TrellisForge 覆盖层「升级」的架构与可执行契约。首次安装见
[PowerShell 安装器](powershell.md)；本文件聚焦 `tools/update-embedded-c-overlay.ps1`
与 `tools/lib/TrellisForgeOverlay.psm1` 的升级侧。本文件是版本无关合同：
目标版本一律以仓库根 `VERSION` 为准，此处不冻结具体版本号。

## 核心设计

升级采用**电梯模型**：`VERSION` 指向的当前 live 模板是唯一升级目标，历史版本
正文从 Forge 侧 canonical 内容库取得，而不是为每个 `from→to` 复制目标快照。
每个受支持版本有完整 manifest；文件正文不变的部分在多个版本间共享同一
canonical 对象。三方合并的 `old` 来自 canonical 对象，且永远不是包含用户
定制的 `installed` 结果。文件正文永远**一步直达**：从来源 canonical 直接
合并到当前模板，不读取或落盘任何中间版本正文。

## 目录契约

| 路径 | 内容 |
|---|---|
| `history/embedded-c-overlay/objects/<sha256>` | canonical 正文对象：UTF-8 无 BOM、LF 规范化（CRLF→LF），按 SHA-256 去重 |
| `history/embedded-c-overlay/versions/<v>/manifest.json` | 版本 v 的完整 manifest |
| `migrations/embedded-c-overlay/structural/<from>-to-<to>.json` | 相邻版本结构迁移步骤（线性链） |
| `.trellis/tasks/…/gen_migration.py` | 资产生成器（保留历史、仅追加当前版本 manifest/对象与相邻结构步骤） |
| `.trellis/tasks/…/verify_assets.py` | 资产校验器（历史不变、引用完整性、去重、无方案 A 残留、git diff --check） |

对象命名 = `sha256(LF 规范化的去 BOM 正文)`。同一内容（如 `.agents/` 与
`.claude/` 的镜像）映射同一对象。已提交的历史对象不可重写。受支持来源版本
集合 = `versions/` 下存在 manifest 且能通过相邻步骤连接到 `VERSION` 的版本。

## Schema 契约

### 版本 manifest（`versions/<v>/manifest.json`）

```json
{
  "schema_version": 1,
  "overlay": "embedded-c",
  "trellisforge_version": "<v>",
  "trellis_version": "0.6.10",
  "render_tokens": ["PROJECT_PREFIX", "PROJECT_NAME", "__PROJECT_PREFIX__"],
  "files": [
    { "path": ".agents/skills/__PROJECT_PREFIX__-trellis-review/SKILL.md",
      "ownership": "managed", "canonical_sha256": "<object-ref>" }
  ]
}
```

- `files[].path` 为**未渲染**的相对路径，可含 `__PROJECT_PREFIX__` token。
- `ownership` ∈ `managed` | `adoption-baseline`。`adoption-baseline` 只在来源
  manifest 出现，表示「上游 Trellis 已生成、Forge 本版本才接管」的路径。
- `canonical_sha256` 指向 `objects/` 中的对象文件名。

### 安装收据（目标项目 `.trellis/trellisforge.json`，schema 1）

```json
{
  "schema_version": 1, "trellisforge_version": "<v>", "overlay": "embedded-c",
  "project_prefix": "example", "project_name": "Example Firmware",
  "files": [
    { "path": ".agents/skills/example-trellis-review/SKILL.md",
      "canonical_sha256": "<对象哈希>", "baseline_sha256": "<渲染后哈希>",
      "installed_sha256": "<实际结果哈希>" }
  ]
}
```

- `path` 为**渲染后**路径（token 已替换为项目前缀），必须能在目标磁盘定位。
- `canonical_sha256`：渲染前对象哈希，可回指 `history/…/objects/<sha256>`。
- `baseline_sha256`：按项目参数渲染后的基线，作为「用户是否改动」的判据源。
- `installed_sha256`：实际落盘结果；与 baseline 不同即表示保留了用户定制。

### 结构迁移步骤（`structural/<from>-to-<to>.json`）

```json
{ "schema_version": 1, "from_version": "1.0", "to_version": "1.1",
  "receipt_transition": "bootstrap-schema-1", "actions": [] }
```

只承载「正文三方合并无法表达」的变化（改名、目录变化、所有权迁移、收据
schema 变化）。步骤只允许出现在**相邻**的已发布版本对之间；不允许跨版本直连
文件。`receipt_transition` 白名单：`bootstrap-schema-1`（无收据入场建立
schema 1）、`preserve-schema-1`（schema 保持不变）。执行器校验 schema、
from/to 与相邻对匹配、动作白名单与转换白名单；未知动作/转换或断链以
`unsupported` 停止。

## 相邻链组合

`Get-OverlayStructuralChain` 不再读取单个 `<from>-to-<to>.json`，而是：

1. 枚举 `versions/` 下带 manifest 的版本并按数值序排序；
2. 校验 `from`、`to` 都在该集合内且 `from < to`，否则 `unsupported`；
3. 对 `from` 到 `to` 之间每一对**相邻**版本逐一加载 `<left>-to-<right>.json`
   并按上述规则校验，任何缺失/重复/非法即 `unsupported`；
4. 返回完整 `Steps`、按序聚合的 `Actions` 与合并的 `ReceiptTransition`。

组合**只作用于结构迁移**。文件正文不受步骤数影响：无论来源是 1.0、1.1 还是
更晚版本，每个受管路径仍只执行一次「来源 canonical + 下游当前文件 + 当前
模板」三方合并，中间版本的正文永不被读取或写入。

## 三方合并流程

1. 加载来源与目标两个 manifest，校验 schema/版本/对象引用。
2. **验证 live 模板与目标 manifest 一致**（见失败矩阵）。
3. 校验相邻结构链（见上节），聚合结构动作。
4. 对每个受管路径分类：
   - 来源与目标 canonical 相同 → 工作树不变，仅进入新收据；
   - canonical 变化 → `old`（来源对象，渲染后）+ `current`（目标文件）+
     `new`（live 模板渲染后）三方合并；
   - `adoption-baseline` → 接管合并（old 取自来源对象）；
   - 目标新增且无 adoption baseline → `add`/`already-current`/`conflict`；
   - 来源独有路径 → 必须由聚合结构动作显式覆盖，否则 `unsupported`。
   - `git merge-file` 返回 `0` 表示干净合并，返回 `1..127` 表示冲突块数量
     （超过 127 时截断为 127）；所有冲突结果都必须保留带冲突标记的候选文件，
     不得把多冲突块返回码误判为工具错误。
5. 任一 `conflict`/`unsupported` → 工作树零写入，只在
   `.git/trellisforge-upgrade/<时间戳>-<GUID>/` 写 `report.json`/`report.txt`/
   `candidates/`。全部通过才 `-Apply`。

## 失败矩阵（fail closed，均以 `unsupported` 或其他错误停止）

| 条件 | 结果 |
|---|---|
| live 模板与目标 manifest 不一致（同版本漂移，包括缺失/多余/内容不同） | `unsupported`，安装与升级都拒绝 |
| manifest schema/版本/overlay 不符 | `unsupported` |
| canonical 对象缺失或哈希与 manifest 不符 | `unsupported` |
| 来源/目标无版本清单、版本倒序、相邻步骤缺失/重复、未知动作或转换 | `unsupported` |
| 来源独有路径无聚合结构动作覆盖 | `unsupported` |
| 任一文件三方合并冲突 | 整次 fail closed，零写入包/收据 |

## 维护契约

- 模板正文变化必须提升 `VERSION`、生成新 manifest 与必要新对象，用
  发布收尾任务的 `gen_migration.py` 追加生成（先验证历史资产字节不变，再
  仅追加当前版本内容）、`verify_assets.py` 校验；**不得改写已提交的历史对象
  或旧版本 manifest**。
- 每个新版本只新增一个相邻结构步骤（即使 `actions` 为空也要显式声明
  `receipt_transition`）；不新增跨版本直连结构文件。
- 历史对象只有在所有引用它的受支持版本均停止支持后才可清理。
- 最早入场版本的内容来源固定为提交 `e40a942`，不得用当前已规范化的根文件
  重生成。

## 1.0 入场（adoption）

1.0 无收据。省略 `-FromVersion` 时默认来源 `1.0`，仍强制 `-ProjectPrefix`/
`-ProjectName`；入场候选必须通过 1.0 manifest、canonical 对象、相邻结构链与
三方合并预检验证兼容性（直达当前目标），无法确认即 `unsupported` 停止，不得
猜测项目参数。1.1 及以后的来源版本从 `.trellis/trellisforge.json` 收据识别。

## 验证

- `python -B -m unittest discover -s tests -p "test_*.py"`（安装/升级回归：
  首装、1.1 收据升级、1.0 无收据直达、幂等、相邻链组合与拒绝、正文直达合并、
  新增路径冲突、定制合并、预检零写入与回滚）
- `python -B .trellis/tasks/…/verify_assets.py`（历史不变、对象/清单/结构链、
  无方案 A 残留）
- PowerShell `Parser::ParseFile` 解析模块 + 两个入口
- `git diff --check`（交付文件）
