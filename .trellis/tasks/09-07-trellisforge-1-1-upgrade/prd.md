# 升级 TrellisForge 到 1.1 并提供 1.0 升级方案

## Workflow Settings

- Review level: standard

## Goal

将当前分支尚未形成最终发布结果的 TrellisForge 1.1 方案 A 重构为电梯模型，使新项目能够一次安装当前完整覆盖层，并为已经接入 TrellisForge 1.0 的下游 Git 项目提供安全、可预检、可回滚且尽量保留用户定制的升级路径。

README 同步改写为当前工程入口，清楚区分 TrellisForge 版本、所基于的上游 Trellis 版本、首次接入与既有项目升级。

## Confirmed Facts

- 本地提交 `4dd3f00` 与 `11b16b9` 已按方案 A 实现并记录 TrellisForge `1.1`：包含 `VERSION`、首次安装器、升级器、共享模块、测试、README/指南，以及 `migrations/embedded-c-overlay/1.0-to-1.1/` 下冻结的旧基线和 1.1 `new/` 目标快照。这些提交是当前分支历史，不回滚，但其逐对迁移架构需要由本规划替换。
- 当前分支尚未创建或推送 TrellisForge 1.1 tag/release；因此可以在首次正式发布前调整升级架构和首版收据契约，无需兼容已发布的方案 A 收据。
- 提交 `e40a942` 是当前分支开始 1.1 工作前、README 明确标记 1.0 的模板基线。子任务 1 在其后为模板新增 12 个完整 `trellis-channel` Skill 文件、新增 1 个契约测试，并修改模板 workflow 与两个 channel worker 角色卡。
- 当前安装器、升级器与 `TrellisForgeOverlay.psm1` 已具备方案 A 的路径校验、收据、三方合并、冲突报告、备份和回滚基础；现有 `Get-OverlayMigrationManifest`、`migration.json`、测试夹具和文档直接依赖逐对 `baseline/new`，需要整体改为版本 manifest 与对象库，不能保留两套并行升级机制。
- 下游项目必须已经是 Git 仓库且已经运行 `trellis init`。Git 可作为升级工具的既有依赖，用于安全的三方文本合并。
- 上游 Trellis 的 `.trellis/.version` 与 `.trellis/.template-hashes.json` 属于 Trellis 自身版本和模板状态，不能用作 TrellisForge 版本收据，也不能由 Forge 升级工具伪造或整体覆盖。
- 当前 README、接入指南和模板清单已经描述方案 A，必须同步改为电梯模型的 manifest、对象库、1.0 入场适配和结构迁移链，避免用户按已废弃资产布局维护升级包。

## Requirements

### R1. TrellisForge 1.1 版本事实

- 保持仓库级 TrellisForge 版本事实源为 `1.1`；README、安装器、升级器、版本 manifest 和安装收据均从同一事实或受测试约束的等价来源保持一致。
- TrellisForge `1.1` 与上游 Trellis `0.6.10` 分开表达。本任务不因 Forge 版本变化而擅自升级上游 Trellis 基线；若实施前证据证明模板已依赖其他 Trellis 版本，必须回到规划修正兼容说明。
- 不创建或推送 Git tag，不发布远端 release；本任务只准备仓库内的 1.1 交付内容。

### R2. 1.1 首次接入

- 更新 `tools/install-embedded-c-overlay.ps1`，使首次接入安装当前 1.1 模板，包括子任务 1 新增的完整 `trellis-channel` Skill。
- 保持现有参数兼容：`-TargetRoot`、`-ProjectPrefix`、`-ProjectName`、`-Force` 继续可用；保持目标必须为 Git 根目录、必须已运行 `trellis init`、模板缓存拒绝、路径安全、冲突预览、Git 元数据备份、占位符替换、异常回滚和不删除目标文件等约束。
- 首次安装前必须验证 live 模板与 1.1 manifest 一致；成功后写入 `.trellis/trellisforge.json` schema 1 收据，记录 TrellisForge 版本、覆盖层类型、项目名称/前缀，并为每个受管文件记录 `canonical_sha256`、渲染后的 `baseline_sha256` 和实际结果 `installed_sha256`。写收据必须纳入备份/回滚事务，不能在安装失败时留下虚假 1.1 状态。
- 安装器与升级器共用路径校验、模板渲染、哈希、备份、原子写入/回滚和收据处理逻辑，避免两套安全实现漂移；共享实现保持 Windows PowerShell 兼容。

### R3. 电梯模型与 1.0 入场适配

- 升级补丁确定采用 Windows PowerShell 实现：用户入口为 `tools/update-embedded-c-overlay.ps1`，与首次安装器共用 `tools/lib/TrellisForgeOverlay.psm1` 中的路径校验、模板渲染、三方合并、哈希、备份、收据和事务回滚逻辑。Python 不作为用户升级入口，只用于临时 Git 仓库自动化测试。
- 升级脚本默认只做预检和报告，只有显式 `-Apply` 才写入目标项目。
- 1.1 直接采用电梯模型：当前 1.1 模板是唯一升级目标；升级器不得为每个 `from→to` 迁移复制一份目标 `new/` 快照。
- 新增 Forge 侧历史内容库：按 SHA-256 去重保存受支持版本的 canonical 模板正文，并由每个版本的 manifest 记录完整受管路径、对象引用、内容哈希、路径渲染规则和所有权状态。历史正文必须足以作为三方合并的 `old`，不能只保存哈希。
- 1.0 manifest 除当时由 Forge 管理的路径外，还可记录 Trellis 0.6.10 已生成、1.1 将接管的 `adoption-baseline` 路径；它们提供接管时的 canonical old，但不倒推为 1.0 已由 Forge 发布的模板。
- 当前 1.1 发布内容必须生成不可漂移的 1.1 manifest 和 canonical 对象。升级器运行时验证 live 模板与目标 manifest 一致；未来模板内容变化必须提升 Forge 版本并生成新 manifest，不得静默改变同一版本目标。
- 1.0→1.1 只保留一次性入场适配：从 `e40a942` 固化 1.0 canonical 内容，预演并执行必要的线性结构迁移，再写入可供后续直达最新版本的 1.1 收据。该适配不保存 1.1 专用 `new/` 快照。
- 文件改名、目录变化、所有权迁移和收据 schema 变化等无法仅由正文三方合并表达的变更，使用独立、按版本有序的结构迁移链；普通文件内容升级不写逐对规则。
- 1.0 没有安装收据。无收据且未传 `-FromVersion` 时，脚本默认来源版本为 `1.0`；调用方也可显式传入 `-FromVersion 1.0`。无收据时仍必须显式传入原安装使用的 `-ProjectPrefix` 和 `-ProjectName`，不得猜测这两个项目参数。
- 默认来源版本只是入场候选，不是无条件信任：脚本必须通过 1.0 manifest、canonical 对象、目标结构、结构迁移链和三方合并预检验证目标兼容性；无法确认时以 `unsupported` 停止，不得写入。
- 升级成功后写入 1.1 安装收据。以后再次运行同一升级应识别“已是 1.1”并安全退出，不重复修改或生成额外冲突。
- 若目标已有收据，参数与收据冲突时 fail closed；不得猜测项目名称、前缀或来源版本。

### R4. 用户定制保护、冲突和事务

- 对来源与目标 manifest 共同管理的文件，以及来源声明为 `adoption-baseline`、目标开始管理的文件，升级器使用“来源 canonical old + 目标当前文件 + 当前 1.1 模板 new”执行三方文本合并；非重叠的用户定制应保留。
- 收据为每个文件记录 canonical 对象哈希、按项目参数渲染后的 `baseline_sha256` 和实际写入结果的 `installed_sha256`。后续三方合并的 old 必须由 canonical 对象取得，不能把含用户定制的 installed 结果当作祖先。
- 对目标版本新增且没有 adoption baseline 的文件：目标不存在时可新增；目标已存在且与 1.1 内容一致时视为已满足；目标已存在但内容不同则视为冲突，不静默覆盖。
- 预检报告至少区分 `add`、`update`、`already-current`、`user-merged`、`conflict`、`unsupported`，列出相对路径并给出下一步。
- 任一文件出现冲突时，整次升级 fail closed：升级工具不得修改工作树、不得写入或更新 1.1 收据，也不得先应用无冲突文件。工具在 Git 元数据目录 `.git/trellisforge-upgrade/<时间戳>-<GUID>/` 生成冲突报告和候选合并文件；用户根据这些材料处理目标文件后重新预检，只有全部路径无冲突时才允许 `-Apply`。
- 实际写入前，把所有将修改的既有文件及其 SHA-256 复制到 `.git/trellisforge-backup/<时间戳>-<GUID>/`，清单同时记录来源版本、目标版本、新增路径和计划动作。
- 写入过程任何一步失败时恢复所有已覆盖文件、删除本次新增文件、恢复或移除安装收据，并返回非零退出码。不得把部分升级记录为 1.1。
- 不修改目标 `.trellis/.version` 或 `.trellis/.template-hashes.json`；升级前指导用户先运行 `trellis update --dry-run` 并处理上游 Trellis 状态，Forge 工具本身不执行整体 `trellis update --force`。

### R5. 子任务 1 交接差异与历史基线

- 模板两套 `trellis-channel/references/command-reference.md` 含子任务 1 有意新增的规则，并比根目录上游参考少一个尾部空行。
- 1.0 入场适配的 `adoption-baseline` canonical old 必须直接从提交 `e40a942` 的上游 `trellis-channel` 文件提取并忠实保留历史内容，包括 `command-reference.md` 原有的多余尾部空行；不得从清理后的当前根文件反向生成历史对象。
- 当前 1.1 模板是 canonical new，其中包含子任务 1 新增的约 6 行公共规则，并删除上述多余尾部空行。该规则新增和空行删除都是预期的版本变化，不得标记为下游用户定制或内容漂移。
- 合并与内容哈希允许统一 LF/CRLF 作为换行序列，但不得裁剪行尾空白、尾部空行或其他内容；目标文件的实际换行风格仍按设计保留。
- 根目录对应参考文件的多余尾部空行已在 `11b16b9` 作为独立仓库维护改动清理。电梯模型资产生成必须从 `e40a942` 读取 1.0 内容，不得把当前已清理文件当作历史来源。
- 除上述已交接的规范化外，不借升级任务修改仓库自身现用 Trellis 工作流行为。

### R6. README、接入指南与模板清单

- 重构 README，使其至少包含：项目定位与非目标、Forge/Trellis 版本兼容信息、首次接入快速入口、1.0→1.1 升级快速入口、当前能力摘要（包含 Channel 唯一等待规则）、仓库目录与交付物、验证/安全边界以及详细接入指南链接。
- README 删除或压缩只服务于单次历史修复的长篇叙述；保留仍能解释当前能力和设计边界的内容，不把 README 写成 changelog。
- 更新 `docs/接入指南.md`，分开描述“首次接入 1.1”“从 TrellisForge 1.0 升级到 1.1”“升级上游 Trellis”三种流程，提供 Windows PowerShell 可直接解释的命令、预检/应用步骤、冲突处理、备份恢复和升级后验证。
- 更新 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 和其他直接受影响的目录说明，列出新增完整 Channel Skill、安装收据和版本化升级交付物的归属；不得把 `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 或 `.trellis/.template-hashes.json` 加入发布模板。

### R7. 自动验证

- 重构安装/升级公共逻辑的临时 Git 仓库自动化测试，至少覆盖：首次安装 1.1、live 模板/manifest 一致性、无 `-Force` 冲突预览、覆盖前备份、占位符替换、三类哈希收据、1.0 无收据入场、非重叠用户定制合并、相同 canonical 路径零写入、新增文件冲突、已有 1.1 幂等、历史对象/来源版本错误、结构链验证、预检零写入、写入失败回滚和路径逃逸拒绝。
- 测试同时覆盖 LF 与 CRLF 目标文本，避免 Windows 换行差异被误报为用户冲突。
- 运行项目既定 Python 单测、Python 语法检查、PowerShell 解析检查、安装器和升级器临时仓库冒烟、未替换占位符/缓存扫描及 `git diff --check`。
- 构建、部署和硬件验证为 `not applicable`；下游项目的真实构建与硬件验证由接入者在升级后执行并记录。

## Acceptance Criteria

- [ ] 仓库的 TrellisForge 版本事实、README、安装器、升级器、版本 manifest 和成功收据一致为 1.1，并与上游 Trellis 版本清楚区分。
- [ ] 新项目使用更新后的首次接入命令可安装完整 1.1 覆盖层，保留既有安全检查，并生成准确的 1.1 安装收据。
- [ ] 1.0 项目可先预检再显式应用电梯模型升级；升级只处理受管文件和结构迁移链，不全量覆盖模板，也不删除目标文件。
- [ ] 无收据且省略 `-FromVersion` 时默认使用 1.0 入场适配，同时要求显式项目名称/前缀并完成历史 manifest、canonical 对象和结构兼容性预检；无法验证的项目不会被修改。
- [ ] 干净 1.0、带非重叠用户定制的 1.0、存在冲突、已是 1.1 和不受支持来源版本均有确定、可测试的结果。
- [ ] 1.0 下游原样保留历史尾部空行的 `command-reference.md` 可无冲突升级：结果包含子任务 1 新增规则且移除多余空行；真正的下游内容修改仍由三方合并识别和保护。
- [ ] 1.1 安装或升级后的收据可定位每个文件的 canonical baseline，并区分渲染后基线与实际安装结果；后续升级不依赖逐对 `new/` 快照即可取得 old。
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

- Status: pending
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: no

## Handoff Notes From Child Task 1（子任务 1 交接）

- 模板 `templates/embedded-c-overlay/.agents/skills/trellis-channel/references/command-reference.md`（及其 `.claude/skills/trellis-channel/references/command-reference.md` 镜像）与根上游源 `.agents/skills/trellis-channel/references/command-reference.md` **并非逐字节一致**。做版本识别 / 哈希迁移比对时，不要把这个差异误判为「用户改动」或「内容漂移」。差异共两处：
  1. 模板副本多约 6 行公共规则（如 "Standard dispatch use..." 段落），是子任务 1 有意写入的交付内容。
  2. 模板副本比根源少 1 个空行；根源自带一个多余空行，子任务 1 为通过 `git diff --check` 从模板副本截除。根源在子任务 1 禁改清单内，因此该规范化延后到本任务。
- 根源的多余尾部空行已在 `11b16b9` 删除；本次必须直接从 `e40a942` 固化仍包含该空行的 1.0 canonical 对象，并可用已提交方案 A baseline 交叉验证。1.1 manifest 对应包含新增规则且无多余空行的模板，当前根文件不得用于重建 1.0 对象。

## 电梯模型资产维护契约

- 当前模板是唯一升级目标；每个受支持版本有完整 manifest，manifest 的文件条目指向按 SHA-256 去重的 canonical 对象，不建立逐对目标快照。
- 修改模板正文必须提升 Forge 版本、生成新 manifest 和必要的新对象，并验证旧版本 manifest 与对象未被改写。同一版本下 live 模板与 manifest 不一致时，安装和升级均 fail closed。
- 收据保存当前 Forge 版本、项目渲染参数，以及每个受管文件的 canonical 对象哈希、渲染后基线哈希和 installed 哈希。历史对象只有在所有引用它的受支持版本均明确停止支持后才可清理。
- 结构迁移按版本形成单一线性链，只处理内容三方合并无法表达的变化；文件正文始终从来源 canonical 直接合并到当前目标模板。
