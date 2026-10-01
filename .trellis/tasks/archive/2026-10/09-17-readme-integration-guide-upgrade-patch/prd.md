# TrellisForge 1.3 发布收尾：README、接入指南与升级补丁

## Workflow Settings

- Review level: reinforced

## Spec References

- `.trellis/spec/main/tooling/templates-and-docs.md`
- `.trellis/spec/main/tooling/overlay-upgrade.md`
- `.trellis/spec/main/tooling/powershell.md`
- `.trellis/spec/main/tooling/python.md`
- `.trellis/spec/shared/validation.md`
- `.trellis/spec/shared/repository-layout.md`
- `.trellis/spec/guides/index.md`
- `.trellis/spec/guides/cross-layer-thinking-guide.md`
- `.trellis/spec/guides/code-reuse-thinking-guide.md`

## Goal

把已冻结的 TrellisForge 1.3 模板功能整理为可安装、可升级、可说明的正式交付：新项目一次安装 1.3；已有 1.0 无收据、1.1 收据或 1.2 收据的下游项目安全升级到 1.3。`.opencode/package.json` 不再作为官方受管文件安装或升级；本机生成的依赖清单从一开始就不进 git。README 与中文接入指南必须准确描述最终能力、命令、兼容范围和安全边界。

## Background And Confirmed Facts

- 本任务是父任务 `09-17-trellisforge-1-3-upgrade` 的固定最后一个子任务；`children` 仍以本任务结尾。
- 用户 2026-10-01 确认 1.3 功能集冻结于 9 个已归档功能子任务，并批准把 `.opencode/package.json` 移出官方交付：不进受管清单、模板源树删除、文档写依赖与 `npm install`；覆盖层自带 `.opencode/.gitignore` 忽略 `package.json` / `package-lock.json`；已跟踪下游需 `git rm --cached` 后 ignore 才生效。升级器不删除磁盘上的旧文件。
- 仓库 `VERSION` 仍为 `1.2`。历史资产为 `versions/1.0|1.1|1.2` 与 `structural/1.0-to-1.1.json`、`1.1-to-1.2.json`。上游 Trellis 基线仍为 `0.6.10`。
- 电梯模型已落地。安装器只写入当前版本 manifest 的受管文件。升级器对来源独有路径要求结构动作覆盖，分类为 `structural-remove` / `already-current`，不删目标工作树文件（`update-embedded-c-overlay.ps1:191-194`）。
- 1.2 manifest 将 `.opencode/package.json` 标为 managed（`history/.../versions/1.2/manifest.json:248`）。live 模板相对 1.2 另新增 7 个测试文件、无其他删除路径。模板尚无 `.opencode/.gitignore`；根自用 `.opencode/.gitignore` 已忽略 `package.json` / `package-lock.json`。
- 模板 `test_opencode_platform_contract.py` 仍把 `.opencode/package.json` 列为 `REQUIRED_ROOTS` 并解析插件依赖。根目录同名文件位于 `.trellis/scripts/tests/`，`TEMPLATE_ROOT` 解析为仓库根，测的是根 `.opencode/`，不是模板；本任务不改该根测试。
- `templates-and-docs.md:14-18`：下游功能默认只改 `templates/embedded-c-overlay/`；版本号、history、manifest、结构链、README、接入指南只由本发布收尾任务更新。根自用 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/` 不得因模板有对应路径而回改。
- 1.2 发布收尾是资产生成/校验参考。父任务排除：`docs/开发计划.md` 其余未点名条目；根 `.opencode/package.json` 本机钉死内容本身不提交。

## Requirements

### R1 版本与历史资产

- 将仓库版本事实提升为 `1.3`，新增完整 `versions/1.3/manifest.json` 和必要的新 canonical 对象。
- 1.0、1.1、1.2 manifest 与其 canonical 对象必须保持字节不可变。
- 新增 `structural/1.2-to-1.3.json`：`receipt_transition` 为 `preserve-schema-1`；`actions` 仅一项 `{ "action": "remove", "path": ".opencode/package.json" }`（覆盖来源独有路径，不删除磁盘文件）。不新增跨版本直连结构文件。
- 收据 schema 继续为 1。上游 Trellis 基线保持 `0.6.10`。

### R2 下游升级兼容

- 首次安装始终安装当前完整 1.3 模板并写入 schema 1 三类哈希收据；不安装 `.opencode/package.json`。
- 有效 1.1 或 1.2 收据必须可升级到 1.3；有效 1.3 收据必须返回 `already-current`。
- 无收据 1.0 项目继续支持默认或显式 `-FromVersion 1.0` 入场。文件正文只执行一次“来源 canonical + 下游当前文件 + 1.3 模板”三方合并；仅结构迁移按相邻步骤加载（1.0 三条、1.1 两条、1.2 一条）。
- 1.2 来源的 `.opencode/package.json` 必须由 `1.2-to-1.3` 的 `remove` 覆盖，否则 fail closed。升级后该路径退出 1.3 收据；磁盘文件保持不动。
- 未知来源、断链、历史对象缺失、live 模板与目标 manifest 漂移、收据/参数不一致以及任一文件冲突必须 fail closed。
- 保留默认预检、显式 `-Apply`、三方合并、冲突零工作树写入、备份、原子写入和异常回滚；不得增加静默覆盖、忽略冲突、部分应用或删除下游文件的路径。

### R3 OpenCode 依赖清单不再官方交付

- 从 `templates/embedded-c-overlay/` 删除 `.opencode/package.json`，不保留参考副本。
- 新增受管 `.opencode/.gitignore`，至少忽略 `package.json` 与 `package-lock.json`，使本机 `npm install` 产物从一开始不进 git。
- README 与接入指南写明：在 `.opencode/` 手工创建依赖声明并安装 `@opencode-ai/plugin`（可用 `npm install`）；已跟踪该文件的下游先 `git rm --cached .opencode/package.json`，ignore 才生效。
- 模板 `test_opencode_platform_contract.py` 不再把模板内 `.opencode/package.json` 当作必装根文件；改为断言 gitignore 覆盖上述两文件。
- 根目录自用 `.opencode/` 不因本条反向修改；根 `.opencode/package.json` 既有脏改动不纳入本任务 diff。

### R4 1.3 功能说明

README 与接入指南必须按最终工程状态说明，并明确这些能力在发布模板中交付、不宣称根目录自用 Trellis 已同步：

1. 小修可走 `plan.py revise`；完成后默认原地 `revise`；`sequel` / `plans/` 仅显式兼容。
2. Codex 原生静默等待、编号子步骤归并、Step detail `--platform` 送达、`write_json` 保持 LF。
3. 任务创建询问收窄：仅在用户明确要写代码或实施时询问。
4. 任务目录前缀 `MM-DD-HHmm`，同分钟错峰。
5. 规划门禁：`prd.md` 非空 `## Spec References`；子代理派发下 jsonl 须有真实条目。
6. 单次 `trellis-implement` 派发走完整执行计划链。
7. 审查循环退出以主会话复核后的 blocking 数为准。
8. OpenCode 依赖清单由本机生成，不随覆盖层官方安装；gitignore 与 `git rm --cached` 规则见 R3。

### R5 文档与发布边界

- 更新根 `README.md`：版本兼容（含 1.2→1.3）、最短安装/升级命令、当前能力、目录与交付物、安全边界和非目标。
- 更新 `docs/接入指南.md`：首次接入 1.3、1.0/1.1/1.2 升级到 1.3、OpenCode 本机依赖步骤、预检/应用/冲突/恢复/幂等、三平台验证和独立上游 Trellis 更新。
- 同步更新 `TEMPLATE-CONTENTS.md`：1.3 版本事实、7 个新增测试文件、`.opencode/.gitignore`、不再交付 `package.json`。
- `overlay-upgrade.md` 保持版本无关合同；补一条来源独有路径 `remove` 不删磁盘的说明，并修正仍写死 1.2 的验证举例。

### R6 写入范围（spec 对齐）

允许写入：

- `templates/embedded-c-overlay/`（删 `package.json`、加 `.opencode/.gitignore`、改模板 OpenCode 合同测试、更新 `TEMPLATE-CONTENTS.md`）
- 发布资产：`VERSION`、`history/embedded-c-overlay/**`（只追加 1.3）、`migrations/embedded-c-overlay/structural/1.2-to-1.3.json`
- 发布工具回归：`tests/test_overlay_tools.py`；工具入口仅当仍写死 1.2 目标语义时改注释/断言，不改电梯算法、不把 `remove` 变成删文件
- 发布文档：`README.md`、`docs/接入指南.md`
- 仓库维护 Spec：`.trellis/spec/main/tooling/overlay-upgrade.md`（仅补 `remove` 不删盘与四代资产举例）
- 本任务目录规划/生成/校验脚本

禁止写入：根自用 `.trellis/scripts/`（含根 `test_opencode_platform_contract.py`）、`.trellis/workflow.md`、`.agents/`、`.claude/`、`.codex/`、根 `.opencode/`（含已脏的 `package.json`）、根 `.opencode/.gitignore`。

## Acceptance Criteria

- [ ] `VERSION`、1.3 manifest、安装/升级收据、工具输出、README、接入指南和模板内容清单一致指向 TrellisForge 1.3；Trellis 基线仍为 0.6.10。
- [ ] 1.0、1.1、1.2 历史 manifest 与已有 canonical 对象保持字节不变；1.3 manifest 与 live 模板受管路径一致（含 7 个新增测试文件与 `.opencode/.gitignore`，不含 `.opencode/package.json`），全部对象哈希有效且无未引用对象。
- [ ] 文件正文只执行一次“来源 canonical + 下游当前文件 + 1.3 模板”三方合并；结构迁移按来源加载相邻步骤（1.0 三条、1.1 两条、1.2 一条）；`1.2-to-1.3` 对 `.opencode/package.json` 有 `remove`；不存在跨版本直连结构文件。
- [ ] 新项目安装 1.3 后获得完整 schema 1 收据且工作树无 `.opencode/package.json`；1.0 无收据、1.1 收据、1.2 收据项目均可先预检再 `-Apply` 升级到 1.3，重复运行返回 `already-current`。
- [ ] 1.2 夹具升级后：`.opencode/package.json` 仍留在磁盘（若升级前存在），但退出 1.3 收据；gitignore 已安装；升级器未删除该文件。
- [ ] 非重叠用户定制得到保留；1.3 新增路径已存在且内容不同时报告冲突；任何冲突或 unsupported 都不会留下部分 1.3 工作树或虚假收据。
- [ ] README、接入指南和模板清单准确覆盖 R4 八项，并写明 OpenCode 本机 `npm install @opencode-ai/plugin` 与已跟踪文件的 `git rm --cached`。
- [ ] 模板 OpenCode 合同测试不再要求模板内 `package.json`；工具回归、根/模板 Trellis 单测、语法检查、PowerShell 解析、资产校验、占位符/缓存扫描和交付路径 `git diff --check` 通过；构建/部署/硬件为 `not applicable`。
- [ ] 按 `reinforced` 完成 affected-scope 独立审查并清零阻塞；未执行提交、推送、tag 或发布。

## Out Of Scope

- 升级上游 Trellis 或改变 `0.6.10` 基线。
- 修改根目录自用 Trellis 工作流来追随发布模板（含根 `.opencode/`、根 `.trellis/scripts/`、根 Hook/代理）。
- 升级器自动删除下游磁盘上的 `.opencode/package.json`，或代替用户执行 `git rm --cached`。
- 把 `docs/开发计划.md` 其余未点名条目纳入本收尾。
- 为未知或早于 1.0 的来源版本提供猜测式迁移。
- 新增 `trellis channel --provider opencode`、OpenCode `trellis mem` 读取器，或宣称已完成真实 OpenCode CLI/TUI 端到端验证。
- 自动合并根 `AGENTS.md`、忽略冲突、部分应用升级。
- 创建 Git 提交、tag、release 或推送远端。
- 向 1.3 父任务追加新的功能子任务。

## Key Decisions

- 用户确认 1.3 功能集冻结于上述 9 个子任务。
- `.opencode/package.json` 退出 1.3 官方交付：模板源树删除、不进 1.3 manifest；新增 `.opencode/.gitignore`；文档写 `@opencode-ai/plugin` 与 `npm install`；已跟踪项目需用户自己 `git rm --cached`。
- 结构 `remove` 只让路径退出收据与受管集合，不删除下游工作树文件。
- 继续采用电梯模型；支持 1.0 无收据、1.1 收据、1.2 收据升级到 1.3。
- 审查级别沿用 `reinforced`。
- 文档最后更新，以最终 CLI 输出和测试事实为准。
- 用户澄清：不要动根目录自用 Trellis。`VERSION`/history/README 等发布资产按 `templates-and-docs.md:18` 仍由本收尾更新。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes

