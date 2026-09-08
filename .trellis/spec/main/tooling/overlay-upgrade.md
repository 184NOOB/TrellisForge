# 覆盖层升级架构（电梯模型）

本文件定义 TrellisForge 覆盖层「升级」的架构与可执行契约。首次安装见
[PowerShell 安装器](powershell.md)；本文件聚焦 `tools/update-embedded-c-overlay.ps1`
与 `tools/lib/TrellisForgeOverlay.psm1` 的升级侧。

## 核心设计

升级采用**电梯模型**：当前 1.1 模板是唯一升级目标，历史版本正文从 Forge 侧
canonical 内容库取得，而不是为每个 `from→to` 复制目标快照。每个受支持版本
有完整 manifest；文件正文不变的部分在多个版本间共享同一 canonical 对象。
三方合并的 `old` 来自 canonical 对象，且永远不是包含用户定制的 `installed`
结果。

## 目录契约

| 路径 | 内容 |
|---|---|
| `history/embedded-c-overlay/objects/<sha256>` | canonical 正文对象：UTF-8 无 BOM、LF 规范化（CRLF→LF），按 SHA-256 去重 |
| `history/embedded-c-overlay/versions/<v>/manifest.json` | 版本 v 的完整 manifest |
| `migrations/embedded-c-overlay/structural/<from>-to-<to>.json` | 线性结构迁移链 |
| `.trellis/tasks/…/gen_migration.py` | 资产生成器（从 `e40a942` + live 模板确定性地产对象/清单/结构链） |
| `.trellis/tasks/…/verify_assets.py` | 资产校验器（引用完整性、去重、无方案 A 残留、git diff --check） |

对象命名 = `sha256(LF 规范化的去 BOM 正文)`。同一内容（如 `.agents/` 与
`.claude/` 的镜像）映射同一对象。已提交的历史对象不可重写。

## Schema 契约

### 版本 manifest（`versions/<v>/manifest.json`）

```json
{
  "schema_version": 1,
  "overlay": "embedded-c",
  "trellisforge_version": "1.1",
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
  "schema_version": 1, "trellisforge_version": "1.1", "overlay": "embedded-c",
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

### 结构迁移链（`structural/<from>-to-<to>.json`）

```json
{ "schema_version": 1, "from_version": "1.0", "to_version": "1.1",
  "receipt_transition": "bootstrap-schema-1", "actions": [] }
```

只承载「正文三方合并无法表达」的变化（改名、目录变化、所有权迁移、收据
schema 变化）。执行器校验 schema、from/to 版本匹配、链连续性与动作白名单；
未知动作或断链以 `unsupported` 停止。

## 三方合并流程

1. 加载来源与目标两个 manifest，校验 schema/版本/对象引用。
2. **验证 live 模板与目标 manifest 一致**（见失败矩阵）。
3. 对每个受管路径分类：
   - 来源与目标 canonical 相同 → 工作树不变，仅进入新收据；
   - canonical 变化 → `old`（来源对象，渲染后）+ `current`（目标文件）+
     `new`（live 模板渲染后）三方合并；
   - `adoption-baseline` → 接管合并（old 取自来源对象）；
   - 目标新增且无 adoption baseline → `add`/`already-current`/`conflict`。
4. 任一 `conflict`/`unsupported` → 工作树零写入，只在
   `.git/trellisforge-upgrade/<时间戳>-<GUID>/` 写 `report.json`/`report.txt`/
   `candidates/`。全部通过才 `-Apply`。

## 失败矩阵（fail closed，均以 `unsupported` 或其他错误停止）

| 条件 | 结果 |
|---|---|
| live 模板与目标 manifest 不一致（同版本漂移，包括缺失/多余/内容不同） | `unsupported`，安装与升级都拒绝 |
| manifest schema/版本/overlay 不符 | `unsupported` |
| canonical 对象缺失或哈希与 manifest 不符 | `unsupported` |
| 结构链断链 / 未知动作 / from/to 不匹配 | `unsupported` |
| 任一文件三方合并冲突 | 整次 fail closed，零写入包/收据 |

## 维护契约

- 模板正文变化必须提升 `VERSION`、生成新 manifest 与必要新对象，用
  `gen_migration.py` 生成、`verify_assets.py` 校验；**不得改写已提交的历史对象**。
- 历史对象只有在所有引用它的受支持版本均停止支持后才可清理。
- 1.0 内容来源固定为提交 `e40a942`，不得用当前已规范化的根文件重生成。

## Design Decision: 电梯模型 vs 逐对迁移

- 逐对迁移（已废弃的方案 A）为每个 `from→to` 冻结一份 `baseline/` 旧基线 +
  `new/` 目标快照；目标快照与 live 模板重复，版本越多冗余越大（`new/` 复制 N 份）。
- 电梯模型：单一最新目标 + 按 SHA-256 去重的历史正文 + 逐文件三类哈希收据，
  Forge 侧旧数据与版本数解耦，且三方合并 old 永远来自 canonical 而非用户定制。
- 取舍：电梯模型要求长期维护历史对象库与其 manifest；结构级变化另走结构链。

## 1.0 入场（adoption）

1.0 无收据。省略 `-FromVersion` 时默认来源 `1.0`，仍强制 `-ProjectPrefix`/
`-ProjectName`；入场候选必须通过 1.0 manifest、canonical 对象、结构链与三方
合并预检验证兼容性，无法确认即 `unsupported` 停止，不得猜测项目参数。

## 验证

- `python -B -m unittest discover -s tests -p "test_*.py"`（升级/安装 30 项）
- `python -B .trellis/tasks/…/verify_assets.py`（对象/清单/结构链/无方案 A 残留）
- PowerShell `Parser::ParseFile` 解析模块 + 两个入口
- `git diff --check`（交付文件）