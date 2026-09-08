# 升级 TrellisForge 到 1.1 并提供 1.0 升级方案

## Workflow Settings

- Review level: standard

## Goal

发布 TrellisForge 1.1，使新项目能够按更新后的接入指南和安装脚本一次安装当前完整覆盖层，并为已经接入 TrellisForge 1.0 的下游 Git 项目提供安全、可预检、可回滚且尽量保留用户定制的升级路径。

README 同步改写为当前工程入口，清楚区分 TrellisForge 版本、所基于的上游 Trellis 版本、首次接入与既有项目升级。

## Confirmed Facts

- 当前 README 标记 TrellisForge `1.0`，模板基于 Trellis `0.6.10`；仓库没有 TrellisForge 专用版本文件、发布 tag 或下游安装收据。
- 提交 `e40a942` 是当前分支开始 1.1 工作前、README 明确标记 1.0 的模板基线。子任务 1 在其后为模板新增 12 个完整 `trellis-channel` Skill 文件、新增 1 个契约测试，并修改模板 workflow 与两个 channel worker 角色卡。
- `tools/install-embedded-c-overlay.ps1` 面向首次接入：递归收集模板文件，检测目标冲突，无 `-Force` 时拒绝覆盖；使用 `-Force` 时先把既有文件和 SHA-256 清单写到 Git 元数据目录，再全量覆盖并在异常时回滚。
- 现有安装器没有来源版本识别、版本化差异集合或三方合并能力。对已定制的 1.0 项目再次使用 `-Force` 会把全部同名模板文件覆盖掉，因此不能作为 1.0→1.1 的正常升级方案。
- 下游项目必须已经是 Git 仓库且已经运行 `trellis init`。Git 可作为升级工具的既有依赖，用于安全的三方文本合并。
- 上游 Trellis 的 `.trellis/.version` 与 `.trellis/.template-hashes.json` 属于 Trellis 自身版本和模板状态，不能用作 TrellisForge 版本收据，也不能由 Forge 升级工具伪造或整体覆盖。
- README 当前主要介绍首次安装和历史上的提示规范化修复，没有独立的升级入口、版本兼容说明、仓库结构或当前 Channel 派发等待能力；接入指南末尾的“升级”只描述上游 Trellis 更新，没有 TrellisForge 1.0→1.1 操作流程。

## Requirements

### R1. TrellisForge 1.1 版本事实

- 新增仓库级 TrellisForge 版本事实源，版本值为 `1.1`；README、安装器、升级器、迁移清单和安装收据均从同一事实或受测试约束的等价来源保持一致。
- TrellisForge `1.1` 与上游 Trellis `0.6.10` 分开表达。本任务不因 Forge 版本变化而擅自升级上游 Trellis 基线；若实施前证据证明模板已依赖其他 Trellis 版本，必须回到规划修正兼容说明。
- 不创建或推送 Git tag，不发布远端 release；本任务只准备仓库内的 1.1 交付内容。

### R2. 1.1 首次接入

- 更新 `tools/install-embedded-c-overlay.ps1`，使首次接入安装当前 1.1 模板，包括子任务 1 新增的完整 `trellis-channel` Skill。
- 保持现有参数兼容：`-TargetRoot`、`-ProjectPrefix`、`-ProjectName`、`-Force` 继续可用；保持目标必须为 Git 根目录、必须已运行 `trellis init`、模板缓存拒绝、路径安全、冲突预览、Git 元数据备份、占位符替换、异常回滚和不删除目标文件等约束。
- 首次安装成功后写入 `.trellis/trellisforge.json` 安装收据，至少记录 schema、TrellisForge 版本、覆盖层类型、项目名称/前缀和受管文件摘要。写收据必须纳入备份/回滚事务，不能在安装失败时留下虚假 1.1 状态。
- 安装器与升级器共用路径校验、模板渲染、哈希、备份、原子写入/回滚和收据处理逻辑，避免两套安全实现漂移；共享实现保持 Windows PowerShell 兼容。

### R3. 版本化 1.0→1.1 升级包

- 升级补丁确定采用 Windows PowerShell 实现：用户入口为 `tools/update-embedded-c-overlay.ps1`，与首次安装器共用 `tools/lib/TrellisForgeOverlay.psm1` 中的路径校验、模板渲染、三方合并、哈希、备份、收据和事务回滚逻辑。Python 不作为用户升级入口，只用于临时 Git 仓库自动化测试。
- 升级脚本默认只做预检和报告，只有显式 `-Apply` 才写入目标项目。
- 新增版本化迁移资产，记录 1.0→1.1 的受影响路径、每个路径的动作（新增/修改）及修改文件所需的 1.0 旧基线。升级不得依赖用户的 TrellisForge 克隆仍保留完整 Git 历史，也不得运行时从网络下载旧版本。
- 迁移包只处理 1.0 与 1.1 间真实变化的模板文件，不全量覆盖 1.0 的全部 77 个模板文件，不删除目标仓库文件。
- 1.0 没有安装收据。无收据且未传 `-FromVersion` 时，脚本默认来源版本为 `1.0`；调用方也可显式传入 `-FromVersion 1.0`。无收据时仍必须显式传入原安装使用的 `-ProjectPrefix` 和 `-ProjectName`，不得猜测这两个项目参数。
- 默认来源版本只是迁移候选，不是无条件信任：脚本必须通过版本化迁移清单、目标结构、旧基线和三方合并预检验证目标兼容性；无法确认时以 `unsupported` 停止，不得写入。
- 升级成功后写入 1.1 安装收据。以后再次运行同一升级应识别“已是 1.1”并安全退出，不重复修改或生成额外冲突。
- 若目标已有收据，参数与收据冲突时 fail closed；不得猜测项目名称、前缀或来源版本。

### R4. 用户定制保护、冲突和事务

- 对 1.0 中已存在且在 1.1 修改的文件，升级器使用“渲染后的 1.0 基线 + 目标当前文件 + 渲染后的 1.1 模板”执行三方文本合并；非重叠的用户定制应保留。
- 对 1.1 新增文件：目标不存在时可新增；目标已存在且与 1.1 内容一致时视为已满足；目标已存在但内容不同则视为冲突，不静默覆盖。
- 预检报告至少区分 `add`、`update`、`already-current`、`user-merged`、`conflict`、`unsupported`，列出相对路径并给出下一步。
- 任一文件出现冲突时，整次升级 fail closed：升级工具不得修改工作树、不得写入或更新 1.1 收据，也不得先应用无冲突文件。工具在 Git 元数据目录 `.git/trellisforge-upgrade/<时间戳>-<GUID>/` 生成冲突报告和候选合并文件；用户根据这些材料处理目标文件后重新预检，只有全部路径无冲突时才允许 `-Apply`。
- 实际写入前，把所有将修改的既有文件及其 SHA-256 复制到 `.git/trellisforge-backup/<时间戳>-<GUID>/`，清单同时记录来源版本、目标版本、新增路径和计划动作。
- 写入过程任何一步失败时恢复所有已覆盖文件、删除本次新增文件、恢复或移除安装收据，并返回非零退出码。不得把部分升级记录为 1.1。
- 不修改目标 `.trellis/.version` 或 `.trellis/.template-hashes.json`；升级前指导用户先运行 `trellis update --dry-run` 并处理上游 Trellis 状态，Forge 工具本身不执行整体 `trellis update --force`。

### R5. 子任务 1 交接差异

- 模板两套 `trellis-channel/references/command-reference.md` 含子任务 1 有意新增的规则，并比根目录上游参考少一个尾部空行。
- 1.0→1.1 `adopt` 迁移的 `old` 必须直接从提交 `e40a942` 的上游 `trellis-channel` 文件提取并忠实保留历史内容，包括 `command-reference.md` 原有的多余尾部空行；不得从清理后的当前根文件反向生成或覆盖历史 `old`。
- 迁移的 `new` 使用当前 1.1 模板内容，其中包含子任务 1 新增的约 6 行公共规则，并删除上述多余尾部空行。该规则新增和空行删除都是预期的 1.0→1.1 变化，不得标记为下游用户定制或内容漂移。
- 合并与内容哈希允许统一 LF/CRLF 作为换行序列，但不得裁剪行尾空白、尾部空行或其他内容；目标文件的实际换行风格仍按设计保留。
- 根目录对应参考文件的多余尾部空行作为独立的仓库维护改动清理，使其与模板公共基准恢复可维护关系；该清理不能改变已经固化的 1.0 历史迁移资产。
- 除上述已交接的规范化外，不借升级任务修改仓库自身现用 Trellis 工作流行为。

### R6. README、接入指南与模板清单

- 重构 README，使其至少包含：项目定位与非目标、Forge/Trellis 版本兼容信息、首次接入快速入口、1.0→1.1 升级快速入口、当前能力摘要（包含 Channel 唯一等待规则）、仓库目录与交付物、验证/安全边界以及详细接入指南链接。
- README 删除或压缩只服务于单次历史修复的长篇叙述；保留仍能解释当前能力和设计边界的内容，不把 README 写成 changelog。
- 更新 `docs/接入指南.md`，分开描述“首次接入 1.1”“从 TrellisForge 1.0 升级到 1.1”“升级上游 Trellis”三种流程，提供 Windows PowerShell 可直接解释的命令、预检/应用步骤、冲突处理、备份恢复和升级后验证。
- 更新 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 和其他直接受影响的目录说明，列出新增完整 Channel Skill、安装收据和版本化升级交付物的归属；不得把 `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 或 `.trellis/.template-hashes.json` 加入发布模板。

### R7. 自动验证

- 为安装/升级公共逻辑和两个入口增加可在临时 Git 仓库运行的自动化测试，至少覆盖：首次安装 1.1、无 `-Force` 冲突预览、覆盖前备份、占位符替换、收据写入、1.0 干净升级、非重叠用户定制合并、新增文件冲突、已有 1.1 幂等、错误来源版本、预检零写入、写入失败回滚和路径逃逸拒绝。
- 测试同时覆盖 LF 与 CRLF 目标文本，避免 Windows 换行差异被误报为用户冲突。
- 运行项目既定 Python 单测、Python 语法检查、PowerShell 解析检查、安装器和升级器临时仓库冒烟、未替换占位符/缓存扫描及 `git diff --check`。
- 构建、部署和硬件验证为 `not applicable`；下游项目的真实构建与硬件验证由接入者在升级后执行并记录。

## Acceptance Criteria

- [ ] 仓库的 TrellisForge 版本事实、README、安装器、升级器、迁移清单和成功收据一致为 1.1，并与上游 Trellis 版本清楚区分。
- [ ] 新项目使用更新后的首次接入命令可安装完整 1.1 覆盖层，保留既有安全检查，并生成准确的 1.1 安装收据。
- [ ] 1.0 项目可先预检再显式应用版本化升级；升级只处理真实变化路径，不全量覆盖模板，也不删除目标文件。
- [ ] 无收据且省略 `-FromVersion` 时默认使用 1.0 迁移候选，同时要求显式项目名称/前缀并完成兼容性预检；无法验证的项目不会被修改。
- [ ] 干净 1.0、带非重叠用户定制的 1.0、存在冲突、已是 1.1 和不受支持来源版本均有确定、可测试的结果。
- [ ] 1.0 下游原样保留历史尾部空行的 `command-reference.md` 可无冲突升级：结果包含子任务 1 新增规则且移除多余空行；真正的下游内容修改仍由三方合并识别和保护。
- [ ] 任一冲突会阻止整次工作树写入和 1.1 收据更新，并在 Git 元数据目录生成可定位到相对路径的报告与候选合并文件；解决后可重新预检。
- [ ] 所有实际写入在备份后发生；任一步骤失败会恢复原文件和收据，不留下部分 1.1 状态。
- [ ] 升级工具不修改上游 Trellis 的 `.trellis/.version` 与 `.trellis/.template-hashes.json`，也不使用整体强制更新覆盖用户定制。
- [ ] README 能让新用户在首屏找到项目定位、当前版本、首次接入和 1.0 升级入口；详细指南明确区分 Forge 升级和上游 Trellis 升级。
- [ ] 模板内容清单与实际 1.1 文件结构一致，子任务 1 的 Channel 能力和新增升级交付物均有准确说明。
- [ ] 自动化测试覆盖安装、升级、冲突、幂等、换行、路径和回滚关键分支；项目规定的静态检查全部通过。

## Out Of Scope

- 自动升级 1.0 以外的历史 TrellisForge 版本，或设计任意版本图的通用包管理器。
- 自动解决语义冲突、在工作树中留下冲突标记后继续升级，或静默覆盖用户修改。
- 升级 Trellis CLI/npm 包、修改其全局安装目录，或伪造上游模板哈希。
- 修改下游项目的业务代码、硬件配置、项目事实或 AGENTS.md 中用户维护的非 TrellisForge 内容。
- 创建 Git tag、GitHub Release、推送或部署。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes

## Handoff Notes From Child Task 1（子任务 1 交接）

- 模板 `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/command-reference.md`（及其 `.claude/skills/trellis-channel/references/command-reference.md` 镜像）与根上游源 `.agents/skills/trellis-channel/references/command-reference.md` **并非逐字节一致**。做版本识别 / 哈希迁移比对时，不要把这个差异误判为「用户改动」或「内容漂移」。差异共两处：
  1. 模板副本多约 6 行公共规则（如 "Standard dispatch use..." 段落），是子任务 1 有意写入的交付内容。
  2. 模板副本比根源少 1 个空行；根源自带一个多余空行，子任务 1 为通过 `git diff --check` 从模板副本截除。根源在子任务 1 禁改清单内，因此该规范化延后到本任务。
- 本任务必须先从 `e40a942` 固化包含历史尾部空行的 1.0 `old` 资产，再单独删除当前根源的多余尾部空行；1.1 `new` 取包含新增规则且无多余空行的模板。历史资产不得因当前根源规范化而被改写。

## 迁移资产维护契约（方案 A，1.1 交付后持续有效）

- 迁移资产**自包含（方案 A）**：`migrations/embedded-c-overlay/1.0-to-1.1/` 下同时冻结 `baseline/`（1.0 旧基线）与 `new/`（1.1 目标快照）；清单 `new` 字段指向 `new/` 快照而非 live 模板。因此后续修改模板（1.2+）不会改变 1.0→1.1 迁移的产出。
- 维护契约：改动任何被清单收录的模板文件后，必须重跑 `gen_migration.py` 刷新 `new/` 快照与 `new_sha256`，并用 `verify_assets.py` 复核；否则 1.0→1.1 升级会以 `unsupported` fail-closed，或与 `tests/test_overlay_tools.py` 的一致性断言冲突。
- 未来版本策略（1.2 规划输入，不在本任务 accepted scope）：拟采用 point-to-point latest——保留「全新安装=最新」与「N→最新」直跳、删除中间停靠（如 1.0→1.1），每版发布时对每个受支持的历史 `from` 做一次性快照，形成 O(N) 迁移矩阵。规划期需显式决定保留哪些历史 `from` 与何时 prune。
