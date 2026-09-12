# TrellisForge 1.2 发布收尾证据

## Task Tree

- 父任务：`.trellis/tasks/09-10-trellisforge-1-2-upgrade`，状态 `planning`，本任务是 `children` 最后一项。
- 已归档前置子任务：审查五级化、Channel 上下文加载优化、审查阻塞修复责任、OpenCode 平台支持。
- 本会话精确绑定：`.trellis/tasks/09-10-readme-integration-guide-upgrade-patch`，来源 `session:codex_01a09172-066d-7c03-95ec-c13da0dc6455`。

## Upgrade Evidence

- `.trellis/spec/main/tooling/overlay-upgrade.md:9` 定义当前版本为唯一升级目标；`:21` 定义线性结构迁移链；`:105` 起定义历史对象不可重写的维护合同。
- `.trellis/spec/main/tooling/templates-and-docs.md:18` 明确版本号、历史对象、manifest、结构链、README 和接入指南只由发布收尾任务更新；`:24` 起定义 README/接入指南职责。
- `VERSION` 当前为 1.1；历史目录只有 1.0/1.1 manifest，结构目录只有 `1.0-to-1.1.json`。
- `tools/lib/TrellisForgeOverlay.psm1:453` 的 `Get-OverlayStructuralChain` 当前只读取精确 `$FromVersion-to-$ToVersion.json`，不能把两个相邻步骤组合为 1.0->1.2。
- `tools/update-embedded-c-overlay.ps1:18` 的架构注释仍写 1.0->1.1；`:107`、`:210`、`:363`、`:432` 等位置还有 1.1 硬编码诊断。
- 历史规划会话 `01a08194-495` 的 brainstorm 结论与当前 Spec 一致：最新版本直达、Forge canonical 历史正文、相邻版本线性结构链、1.0 无收据一次性入场、三方合并和 fail closed。

## 1.2 Feature Evidence

- `b9fa213..HEAD` 的发布模板 diff 包含 89 个路径、约 10755 行新增；主要是 OpenCode 完整目录和三批既有文件合同调整。
- 审查等级任务最终合同：`light < standard < reinforced < comprehensive < strict`；reinforced 为 affected-scope 修复后独立复审，comprehensive 为 full-scope 闭环但不追加 commit-ready 终审，strict 另有 fresh commit-ready 终审。
- Channel 上下文任务最终合同：标准派发不再通过命令行注入任务正文；Implement/Check 从活动任务、PRD、可选 design/implement 和各自 JSONL 主动批量读取，首次工作前 fail closed。
- 审查阻塞责任任务最终合同：Check Agent 直接修复机械且边界清晰的问题；设计判断和较大实现返回主会话，可靠时优先续接原 Implement Agent；责任分流本身不增加审查轮次。
- OpenCode 任务最终合同：第三默认平台、原生 Task 子代理、Node.js 运行时；Channel worker provider 仍只支持 `claude|codex`，OpenCode `trellis mem` 读取器暂不可用，真实 CLI/TUI 端到端未在当前环境执行。

## Documentation Gaps

- `README.md` 仍把当前版本、唯一目标、目录、收据和升级章节写为 1.1，并只列三档审查及 Claude Code/Codex 上下文。
- `docs/接入指南.md:14` 仍声称只支持 Claude Code/Codex，首次安装与升级章节仍为 1.1，能力表仍列三档审查。
- `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 已列出 OpenCode 1.2 文件树，但收据和历史资产段仍写 1.1。

## Selected Scope

- 发布事实/资产：`VERSION`、`history/**`、`migrations/**`、任务内生成/校验脚本。
- 工具：共享模块、升级器；安装器仅在存在版本硬编码时调整。
- 验证：`tests/test_overlay_tools.py` 与现有根/模板 Trellis 测试。
- 文档/Spec：README、中文接入指南、模板内容清单、overlay upgrade Spec。
- 禁改：根目录自用 Trellis 工作流实现，除项目 Spec 与任务资料外不做镜像式同步。
