# TrellisForge 1.2 发布收尾：README、接入指南与升级补丁

## Workflow Settings

- Review level: strict
- Task-specific review exception: strict review applies to significant implementation batches, but this task does not require a final full-scope review before commit.

## Goal

把当前已完成的 TrellisForge 1.2 模板功能整理为可安装、可升级、可说明的正式交付：新项目一次安装 1.2；已有 1.1 收据的下游项目安全升级到 1.2；无收据的 1.0 下游项目继续沿用既有入场适配并直达 1.2。README 与中文接入指南必须准确描述最终能力、命令、兼容范围和安全边界。

## Background And Confirmed Facts

- 本任务是父任务 `09-10-trellisforge-1-2-upgrade` 的固定最后一个子任务；前置四个功能子任务均已完成，父任务 `children` 列表仍以本任务结尾。
- 仓库当前 `VERSION` 仍为 `1.1`；历史资产只有 `versions/1.0`、`versions/1.1` manifest 和 `structural/1.0-to-1.1.json`，而 live 模板已经包含 1.2 的四批功能变更。
- 既有升级合同是电梯模型：唯一目标为当前版本，历史正文来自内容寻址 canonical 对象库，正文变化执行三方合并，结构变化走相邻版本线性迁移步骤，任一冲突或不支持状态均 fail closed。
- 1.0 没有安装收据，必须显式提供原 `ProjectPrefix` / `ProjectName` 并通过历史 manifest 与 canonical 基线验证；1.1 及以后从 `.trellis/trellisforge.json` 读取来源版本和项目参数。
- 当前 `Get-OverlayStructuralChain` 只读取一个精确的 `<from>-to-<to>.json`，尚不能组合 `1.0-to-1.1` 与 `1.1-to-1.2`；这是结构迁移链的实现缺口，不改变文件正文从来源 canonical 直接三方合并到目标模板的既有合同。
- 1.2 live 模板相对 1.1 新增 OpenCode 平台闭包及合同测试，并修改审查等级、Channel 上下文加载和审查阻塞修复责任相关文件；没有证据表明需要删除、重命名或移动既有受管路径。
- 上游 Trellis 基线仍为 `0.6.10`，不随 Forge 1.2 发布改变。

## Requirements

### R1 版本与历史资产

- 将仓库版本事实提升为 `1.2`，新增完整 `history/embedded-c-overlay/versions/1.2/manifest.json` 和必要的新 canonical 对象。
- 1.0、1.1 manifest 与其 canonical 对象必须保持不可变；生成和校验工具只能验证历史资产并追加 1.2 所需内容，不能用当前模板重写历史版本。
- 新增相邻结构步骤 `migrations/embedded-c-overlay/structural/1.1-to-1.2.json`。本次没有路径重命名、移动或删除，`actions` 为空；收据 schema 继续为 1，步骤明确记录 schema 1 保持不变。

### R2 下游升级兼容

- 首次安装始终安装当前完整 1.2 模板并写入 schema 1 三类哈希收据。
- 有效 1.1 收据必须可升级到 1.2；有效 1.2 收据必须返回 `already-current`。
- 无收据 1.0 项目继续支持默认或显式 `-FromVersion 1.0` 入场。文件正文只执行一次“1.0 canonical + 下游当前文件 + 1.2 模板”三方合并，不读取或落盘 1.1 正文；仅结构迁移依次加载 `1.0-to-1.1` 与 `1.1-to-1.2`。
- 未知来源版本、断裂或非法结构链、历史对象缺失、live 模板与目标 manifest 漂移、收据/参数不一致以及任一文件冲突必须 fail closed。
- 保留默认预检、显式 `-Apply`、三方合并、冲突零工作树写入、Git 元数据报告、应用前备份、原子写入和异常回滚合同；不得增加静默覆盖、忽略冲突、部分应用或删除下游文件的路径。

### R3 1.2 功能说明

- README 与接入指南准确说明五级审查序列 `light < standard < reinforced < comprehensive < strict` 及其主要范围差异。
- 文档说明 Channel 默认使用“稳定规则注入 + 任务文档/Spec 主动读取”的混合模型，Implement/Check 在首次工作前执行 fail-closed 上下文预检。
- 文档说明审查阻塞项的责任分流：Check Agent 只直接修复机械且边界清晰的问题，较大实现或设计决策返回主会话，并优先续接可靠的原 Implement Agent。
- 文档将 OpenCode 列为 Claude Code、Codex 之外的第三个默认平台，说明其需要 Node.js、使用原生 Task 子代理，且 `trellis channel --provider opencode` 与 OpenCode `trellis mem` 读取器不在本次支持范围。

### R4 文档与发布边界

- 更新根 `README.md`：版本兼容、最短安装/升级命令、当前能力、目录与交付物、安全边界和非目标。
- 更新 `docs/接入指南.md`：首次接入 1.2、1.0/1.1 升级到 1.2、预检/应用/冲突/恢复/幂等、三平台接入验证和独立的上游 Trellis 更新流程。
- 同步更新 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 与 `.trellis/spec/main/tooling/overlay-upgrade.md`，消除硬编码 1.1 叙述并准确说明 1.2 资产和相邻结构链。
- 根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 不因发布模板已有对应路径而反向修改；本任务只允许修改明确属于发布收尾、工具、测试和项目 Spec 的文件。

## Acceptance Criteria

- [ ] `VERSION`、1.2 manifest、安装/升级收据、工具输出、README、接入指南和模板内容清单一致指向 TrellisForge 1.2；Trellis 基线仍为 0.6.10。
- [ ] 1.0、1.1 历史 manifest 与已有 canonical 对象保持字节不变；1.2 manifest 与 live 模板逐文件一致，全部对象哈希有效且无未引用对象。
- [ ] 1.0 到 1.2 的文件正文只执行一次“1.0 canonical + 下游当前文件 + 1.2 模板”三方合并，不读取或落盘 1.1 正文；仅结构迁移连续验证并依次加载 `1.0-to-1.1` 与 `1.1-to-1.2`，1.1 来源只加载后一结构步骤；未知版本和断链被拒绝。
- [ ] 新项目安装 1.2 后获得完整 schema 1 三类哈希收据；1.0 无收据项目和 1.1 有收据项目均可先预检再 `-Apply` 升级到 1.2，重复运行返回 `already-current`。
- [ ] 非重叠用户定制得到保留；新增 OpenCode 路径已存在且内容不同时报告冲突；任何冲突、非法 manifest/对象/结构链或写入故障都不会留下部分 1.2 工作树或虚假收据。
- [ ] README、中文接入指南和模板内容清单准确覆盖五级审查、Channel 主动读取与预检、阻塞修复责任、OpenCode 能力/限制及 Windows PowerShell 可执行命令。
- [ ] 工具回归测试、根/模板 Trellis Python 单测、Python 语法检查、PowerShell 解析、资产校验、占位符/缓存扫描和 `git diff --check` 全部通过；构建、部署、硬件验证报告为 `not applicable`。
- [ ] 按本任务的 `strict` 配置完成实施批次审查并清零阻塞问题；提交前不执行全盘终审；未执行提交、推送、tag 或发布。

## Out Of Scope

- 升级上游 Trellis 或改变 `0.6.10` 基线。
- 修改根目录自用 Trellis 工作流来追随发布模板。
- 为未知或早于 1.0 的来源版本提供猜测式迁移。
- 新增 `trellis channel --provider opencode`、OpenCode `trellis mem` 读取器，或宣称已完成真实 OpenCode CLI/TUI 端到端验证。
- 自动合并根 `AGENTS.md`、删除下游文件、忽略冲突、部分应用升级。
- 创建 Git 提交、tag、release 或推送远端。

## Key Decisions

- 继续采用“最新目标 + 历史 canonical + 相邻结构链 + 三方合并 + fail closed”的既有电梯模型，不恢复逐对 `baseline/new` 快照。
- 支持来源为 1.0 无收据入场和 1.1 有收据升级；文件正文始终从来源 canonical 直接三方合并到 1.2，只有结构迁移按相邻步骤组合，不新增 `1.0-to-1.2` 直连快照、正文或结构文件。
- 1.2 保持 receipt schema 1；`1.1-to-1.2` 只声明 schema 保持与空结构动作。
- 本任务审查级别定制为 `strict`；提交前跳过全盘终审仅适用于本任务，不修改项目默认审查配置或 Spec。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
