# TrellisForge

> TrellisForge 当前版本：`1.1`（版本事实源：仓库根目录 [`VERSION`](VERSION)）
>
> 上游 Trellis 基线：`0.6.10`（独立标识，未随 1.1 升级）

TrellisForge 是一套可复用的 Trellis 项目级工作流覆盖模板集合，以嵌入式 C
项目作为完整范例。它不替代 `trellis init`，而是在初始化后的仓库中补齐规划
门禁、代理上下文、执行计划、审查合同和收尾边界等能力。

TrellisForge 不是 Trellis 的私有分叉，也不包含任何特定产品的源码、任务记录、
Flash 布局或硬件协议。下游必须已经运行 `trellis init`，TrellisForge 只是
在初始化结果上叠加项目级覆盖层。

## 版本兼容

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| TrellisForge | `1.1` | 本仓库当前交付版本，安装收据、版本 manifest 与工具输出均以 `VERSION` 为事实源 |
| Trellis 基线 | `0.6.10` | 模板针对的上游 Trellis 版本；`trellis init` 需先于 Forge 覆盖层运行 |
| 首次接入 | 安装器 `tools/install-embedded-c-overlay.ps1` | 面向新项目，含 1.1 完整覆盖层 |
| 1.0 → 1.1 | 升级器 `tools/update-embedded-c-overlay.ps1` | 面向已接入 1.0 的项目，默认预检、显式 `-Apply` 应用 |

## 快速入口

首次接入（目标项目先执行 `trellis init`）：

```powershell
# 在目标项目根目录执行
trellis init
# 在 TrellisForge 根目录执行
& .\tools\install-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -ProjectPrefix example `
  -ProjectName "Example Firmware" `
  -Force
```

从 TrellisForge 1.0 升级（1.0 项目没有安装收据，必须显式提供原安装参数）：

```powershell
# 在 TrellisForge 根目录执行；先预检（不写入）
& .\tools\update-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -ProjectPrefix example `
  -ProjectName "Example Firmware"

# 预检全部通过后应用；覆盖前的原文件和旧收据会备份到 .git\trellisforge-backup\
& .\tools\update-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -ProjectPrefix example `
  -ProjectName "Example Firmware" `
  -Apply
```

`1.0` 没有安装收据。无收据且省略 `-FromVersion` 时默认按 `1.0` 入场候选
预检；`ProjectPrefix` 和 `ProjectName` 仍然必填，升级器不猜测这两个项目参数。
升级使用电梯模型：历史版本正文从 Forge 侧 canonical 内容库取得（而不是逐对
`new/` 快照），1.1 模板是唯一升级目标。已有的 1.1 收据会被如实识别，二次
升级直接报告 `already-current` 并安全退出。

详细的接入、升级、冲突处理和验证步骤见 [docs/接入指南.md](docs/接入指南.md)。

## 当前能力

- 规划阶段：Grill Me 与显式审批门禁（`planning_ready` / `plan_approved`），
  任务创建、规划批准和实施启动分离；
- 代理上下文：Claude Code 与 Codex 的 `inject-subagent-context` 与
  `inject-workflow-state` Hook，把任务 manifest、PRD、Spec 注入子代理；
- 执行计划：schema 3 `execution-plan.json` 状态机、追加式审计日志
  `execution-events.jsonl`、`minimal`/`report` 两级验证与
  `plan.py` 唯一状态推进 CLI；
- 子代理效率：批量读取、合并编辑、分阶段验证、最小复验与完成即停止；
  实施派发提示按“目标/范围/非目标/验收/命令/执行策略”分区，只批量化明确
  执行策略中的碎片化工具编排；
- 审查合同：项目级 `light`/`standard`/`strict` 对照
  changed-scope / affected-scope / full-scope；
- **Trellis Channel 派发与唯一等待**：主会话每个 worker 工作单元只
  `spawn` 一次、只 `wait` 一次（`--kind done,error`），等待期间不轮询、
  不重建 channel，worker 结束 turn 即作为完成信号；`wait` 超时（退出码
  124）与失败走异常处理入口而不是无条件重试；
- 嵌入式 C 边界：构建、静态检查、单元测试和实体硬件验证分开报告，不虚构
  上游模板不存在的验证命令。

## 仓库目录与交付物

```text
VERSION                                  TrellisForge 版本事实源（1.1）
README.md                                本入口
docs/接入指南.md                          首次接入、1.0→1.1 升级与上游 Trellis 更新
tools/
  install-embedded-c-overlay.ps1         首次接入安装器（1.1）
  update-embedded-c-overlay.ps1          1.0→1.1 电梯模型升级器（默认预检、-Apply 应用）
  lib/TrellisForgeOverlay.psm1           安装器与升级器共享的安全/事务模块
history/embedded-c-overlay/
  objects/<sha256>                       canonical 对象库（按 SHA-256 去重的版本正文）
  versions/1.0/manifest.json             1.0 版本清单（受管 + adoption-baseline）
  versions/1.1/manifest.json             1.1 版本清单（当前唯一升级目标）
migrations/embedded-c-overlay/structural/1.0-to-1.1.json  线性结构迁移链
templates/embedded-c-overlay/            1.1 覆盖层模板（含完整 trellis-channel Skill）
templates/language-adaptation/           迁移到其他语言时替换 C 特化规则
tests/test_overlay_tools.py              临时 Git 仓库安装/升级自动化测试
```

## 验证与安全边界

- 新项目安装器保留 Git 根目录校验、`trellis init` 前置检查、模板缓存拒绝、
  路径安全、无 `-Force` 冲突预览、`-Force` 覆盖前 Git 元数据备份与异常回滚；
  安装前验证 live 模板与 1.1 manifest 一致，成功后写 `.trellis/trellisforge.json`
  schema 1 收据，每个受管文件记录 `canonical_sha256`（渲染前对象）、
  `baseline_sha256`(渲染后基线)与 `installed_sha256`（实际结果）。
- 升级器不复制逐对目标快照：它加载来源/目标两个版本 manifest，canonical 对象
  相同的受管路径保持工作树不变，对象变化的路径以 canonical old 做“1.0 基线 +
  当前文件 + 1.1 模板”三方文本合并，adoption-baseline 路径执行接管合并，1.1
  新增文件按缺失/一致/冲突分类；非重叠用户定制保留，不做全量覆盖，不删除
  目标文件。
- 任一冲突或 `unsupported` 都会阻止整次工作树写入和 1.1 收据更新，并在
  `.git/trellisforge-upgrade/<时间戳>-<GUID>/` 生成 `report.json`、
  `report.txt` 与 `candidates/` 候选合并文件，供手工解决后重新预检。
- 安装器和升级器都不修改上游 Trellis 的 `.trellis/.version` 与
  `.trellis/.template-hashes.json`，也不自动合并根 `AGENTS.md`（只生成
  `AGENTS.md.trellisforge-template` 供人工合并）。
- 自动化测试见 `tests/test_overlay_tools.py`；覆盖首次安装、live 模板/manifest
  一致性、1.0 无收据入场、用户定制合并、冲突零写入、新增文件冲突、幂等、
  相同 canonical 零写入、错误版本、LF/CRLF、路径拒绝、结构链校验和写入失败
  回滚。
- 本仓库没有构建、部署或硬件目标，相关验证一律报告 `not applicable`。

## 非目标

- 不替代 `trellis init`，也不修改 Trellis CLI 的全局安装目录；
- 不把 `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 或
  `.trellis/.template-hashes.json` 复制进发布模板；
- 不成为通用包管理器，不维护 1.0 之外的历史升级路径；
- 不保存下游项目的产品事实、业务代码或硬件配置。