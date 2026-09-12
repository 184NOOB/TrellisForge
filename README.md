# TrellisForge

> TrellisForge 当前版本：`1.2`（版本事实源：仓库根目录 [`VERSION`](VERSION)）
>
> 上游 Trellis 基线：`0.6.10`（独立标识，未随 1.2 升级）

TrellisForge 是一套可复用的 Trellis 项目级工作流覆盖模板集合，以嵌入式 C
项目作为完整范例。它不替代 `trellis init`，而是在初始化后的仓库中补齐规划
门禁、代理上下文、执行计划、审查合同和收尾边界等能力。

TrellisForge 不是 Trellis 的私有分叉，也不包含任何特定产品的源码、任务记录、
Flash 布局或硬件协议。下游必须已经运行 `trellis init`，TrellisForge 只是
在初始化结果上叠加项目级覆盖层。

## 版本兼容

| 组件 | 版本 | 说明 |
| --- | --- | --- |
| TrellisForge | `1.2` | 本仓库当前交付版本，安装收据、版本 manifest 与工具输出均以 `VERSION` 为事实源 |
| Trellis 基线 | `0.6.10` | 模板针对的上游 Trellis 版本；`trellis init` 需先于 Forge 覆盖层运行 |
| 首次接入 | 安装器 `tools/install-embedded-c-overlay.ps1` | 面向新项目，含 1.2 完整覆盖层（Claude Code / Codex / OpenCode 三平台） |
| 1.0 → 1.2 | 升级器 `tools/update-embedded-c-overlay.ps1` | 面向无收据的 1.0 项目入场，须显式原安装参数 |
| 1.1 → 1.2 | 同一升级器 | 面向带有效 1.1 收据的项目，来源版本与项目参数从收据识别 |

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

升级到 1.2（先预检，不写入；预检全部通过后再 `-Apply`）：

```powershell
# 1.1 项目（有 .trellis\trellisforge.json 收据）：来源与项目参数自动识别
& .\tools\update-embedded-c-overlay.ps1 -TargetRoot C:\work\example-firmware
& .\tools\update-embedded-c-overlay.ps1 -TargetRoot C:\work\example-firmware -Apply

# 1.0 项目（没有安装收据）：必须显式提供原安装参数
& .\tools\update-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -ProjectPrefix example `
  -ProjectName "Example Firmware"

& .\tools\update-embedded-c-overlay.ps1 `
  -TargetRoot C:\work\example-firmware `
  -ProjectPrefix example `
  -ProjectName "Example Firmware" `
  -Apply
```

`1.0` 没有安装收据。无收据且省略 `-FromVersion` 时默认按 `1.0` 入场候选
预检；`ProjectPrefix` 和 `ProjectName` 仍然必填，升级器不猜测这两个项目参数。
升级使用电梯模型：历史版本正文从 Forge 侧 canonical 内容库取得（而不是逐对
`new/` 快照），1.2 模板是唯一升级目标。文件正文一律从来源 canonical 一步
三方合并到 1.2，不经过中间版本正文；仅结构迁移按相邻步骤组合
（依次加载 `1.0-to-1.1` 与 `1.1-to-1.2`）。已有 1.2 收据的项目重复运行直接报告
`already-current` 并安全退出。

详细的接入、升级、冲突处理和验证步骤见 [docs/接入指南.md](docs/接入指南.md)。

## 当前能力

- 规划阶段：Grill Me 与显式审批门禁（`planning_ready` / `plan_approved`），
  任务创建、规划批准和实施启动分离；
- 代理上下文：Claude Code、Codex 与 OpenCode 三个默认平台的子代理上下文
  注入（Hook / plugin），把活动任务、PRD、Spec 清单送达子代理；OpenCode
  需要 Node.js 运行时并使用原生 Task 子代理；
- 执行计划：schema 3 `execution-plan.json` 状态机、追加式审计日志
  `execution-events.jsonl`、`minimal`/`report` 两级验证与
  `plan.py` 唯一状态推进 CLI；
- 子代理效率：批量读取、合并编辑、分阶段验证、最小复验与完成即停止；
  实施派发提示按“目标/范围/非目标/验收/命令/执行策略”分区，只批量化明确
  执行策略中的碎片化工具编排；
- 审查合同：五级审查序列 `light < standard < reinforced < comprehensive <
  strict`——reinforced 在 affected-scope 内做“修复后全新独立复审直至阻塞
  清零”；comprehensive 扩到 full-scope 闭环复审但不追加 commit-ready 终审；
  strict 在 full-scope 闭环之外仍要求稳定 commit-ready 快照上的一次全新
  全范围终审；
- Channel 混合上下文模型：标准派发不再通过命令行注入任务正文；
  Implement/Check 从活动任务路径、PRD、可选 design/implement 与各自 JSONL
  manifest 在首次工作前主动批量读取，任一必需材料缺失或越界即 fail closed
  停止；
- 审查阻塞项责任分流：Check Agent 只直接修复“局部、机械、小规模、判定
  明确”的问题；设计判断与较大实现修复返回主会话路由，优先可靠续接原
  Implement Agent，其次主会话直修或派发新 Implement Agent；分流本身不
  增加审查轮次；
- **Trellis Channel 派发与唯一等待**：主会话每个 worker 工作单元只
  `spawn` 一次、只 `wait` 一次（`--kind done,error`），等待期间不轮询、
  不重建 channel，worker 结束 turn 即作为完成信号；`wait` 超时（退出码
  124）与失败走异常处理入口而不是无条件重试；worker provider 仍只支持
  `claude|codex`，`--provider opencode` 不在本次支持范围；
- 嵌入式 C 边界：构建、静态检查、单元测试和实体硬件验证分开报告，不虚构
  上游模板不存在的验证命令。

## 仓库目录与交付物

```text
VERSION                                  TrellisForge 版本事实源（1.2）
README.md                                本入口
docs/接入指南.md                          首次接入、1.0/1.1→1.2 升级与上游 Trellis 更新
tools/
  install-embedded-c-overlay.ps1         首次接入安装器（1.2）
  update-embedded-c-overlay.ps1          电梯模型升级器（默认预检、-Apply 应用、相邻结构链组合）
  lib/TrellisForgeOverlay.psm1           安装器与升级器共享的安全/事务模块
history/embedded-c-overlay/
  objects/<sha256>                       canonical 对象库（按 SHA-256 去重的版本正文）
  versions/1.0/manifest.json             1.0 版本清单（受管 + adoption-baseline）
  versions/1.1/manifest.json             1.1 版本清单（不可变历史）
  versions/1.2/manifest.json             1.2 版本清单（当前唯一升级目标）
migrations/embedded-c-overlay/structural/  相邻结构迁移步骤（1.0-to-1.1、1.1-to-1.2）
templates/embedded-c-overlay/            1.2 覆盖层模板（三平台 + 完整 trellis-channel Skill）
templates/language-adaptation/           迁移到其他语言时替换 C 特化规则
tests/test_overlay_tools.py              临时 Git 仓库安装/升级自动化测试
```

## 验证与安全边界

- 新项目安装器保留 Git 根目录校验、`trellis init` 前置检查、模板缓存拒绝、
  路径安全、无 `-Force` 冲突预览、`-Force` 覆盖前 Git 元数据备份与异常回滚；
  安装前验证 live 模板与 1.2 manifest 一致，成功后写 `.trellis/trellisforge.json`
  schema 1 收据，每个受管文件记录 `canonical_sha256`（渲染前对象）、
  `baseline_sha256`(渲染后基线)与 `installed_sha256`（实际结果）。
- 升级器不复制逐对目标快照：它加载来源/目标两个版本 manifest，canonical 对象
  相同的受管路径保持工作树不变，对象变化的路径以 canonical old 做“来源基线 +
  当前文件 + 1.2 模板”三方文本合并（1.0 来源同样一步直达 1.2，不读取或落盘
  1.1 正文），adoption-baseline 路径执行接管合并，1.2 新增文件（含 OpenCode
  闭包）按缺失/一致/冲突分类；结构变化按相邻迁移步骤组合校验；非重叠用户定制
  保留，不做全量覆盖，不删除目标文件。
- 任一冲突或 `unsupported` 都会阻止整次工作树写入和 1.2 收据更新，并在
  `.git/trellisforge-upgrade/<时间戳>-<GUID>/` 生成 `report.json`、
  `report.txt` 与 `candidates/` 候选合并文件，供手工解决后重新预检。
- 安装器和升级器都不修改上游 Trellis 的 `.trellis/.version` 与
  `.trellis/.template-hashes.json`，也不自动合并根 `AGENTS.md`（只生成
  `AGENTS.md.trellisforge-template` 供人工合并）。
- 自动化测试见 `tests/test_overlay_tools.py`；覆盖首次安装、live 模板/manifest
  一致性、1.0 无收据入场、1.1 收据升级、正文一步直达、相邻结构链组合与拒绝
  （断链/非法动作/非法转换）、新增文件冲突、用户定制合并、冲突零写入、幂等、
  相同 canonical 零写入、错误版本、LF/CRLF、路径拒绝、结构链校验和写入失败
  回滚。
- 本仓库没有构建、部署或硬件目标，相关验证一律报告 `not applicable`。

## 非目标

- 不替代 `trellis init`，也不修改 Trellis CLI 的全局安装目录；
- 不把 `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 或
  `.trellis/.template-hashes.json` 复制进发布模板；
- 不成为通用包管理器；升级来源只支持存在完整历史 manifest 且能组成相邻结构
  链的版本（当前为 1.0 入场与 1.1 收据），不猜测更早来源；
- 不提供 `trellis channel --provider opencode` 或 OpenCode `trellis mem`
  读取器，也不宣称已完成真实 OpenCode CLI/TUI 端到端验证；
- 不保存下游项目的产品事实、业务代码或硬件配置。
