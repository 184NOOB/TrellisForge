# TrellisForge 1.3 发布收尾证据

## Task Tree

- 父任务：`.trellis/tasks/09-17-trellisforge-1-3-upgrade`，状态 `planning`，`children` 以本任务结尾，`terminal_child` 为本任务。
- 用户 2026-10-01 确认：1.3 功能集在 9 个已归档功能子任务处冻结，不再向父任务追加功能子任务。
- 已归档前置子任务：`09-17-small-patch-and-sequel-plans`、`09-21-codex-native-wait-quiet`、`09-22-refine-task-triage-consent`、`09-22-task-dir-time-prefix`、`09-24-template-platform-hint-and-step-text`、`09-24-spec-first-planning-gate`、`09-26-dispatch-chain-contract`、`09-27-review-severity-readjudication`、`10-01-allow-plan-post-complete-edit`。

## Upgrade Evidence

- `VERSION` 当前为 `1.2`。历史资产：`versions/1.0|1.1|1.2` 与 `structural/1.0-to-1.1.json`、`1.1-to-1.2.json`。
- 不可变基线哈希（本规划盘点）：1.0 manifest `ac26b0975422…c86a92`，1.1 manifest `f0ed1f8fbd33…354587`，`1.0-to-1.1.json` `66222336d312…afa276`，1.2 manifest `6e6c46839f48…5abec1`，`1.1-to-1.2.json` `d2c23fbaf82a…d09829`。
- `.trellis/spec/main/tooling/overlay-upgrade.md` 已是版本无关电梯合同：当前 `VERSION` 为唯一目标，正文一步直达，结构按相邻步骤组合，live/manifest 漂移 fail closed。
- `Get-OverlayForgeVersion` 已从根 `VERSION` 读取；安装器/升级器入口不再硬编码 `1.2`。`tests/test_overlay_tools.py` 仍把 `TARGET_VERSION` 钉在 `1.2`，并缺少 `make_12_project`。
- live 模板相对 1.2 manifest：新增 7 个 `.trellis/scripts/tests/test_*.py`。用户随后决定 1.3 删除模板 `.opencode/package.json`（1.2 managed，`versions/1.2/manifest.json:248`），并新增 `.opencode/.gitignore`。因此 `1.2-to-1.3.json` 必须含 `{ "action": "remove", "path": ".opencode/package.json" }`；升级器对该动作不删磁盘（`update-embedded-c-overlay.ps1:191-194`）。
- 用户确认不在模板源树保留参考 `package.json`；文档写 `@opencode-ai/plugin` 与 `npm install`；已跟踪下游自行 `git rm --cached`。
- 1.2 收尾 `archive/2026-09/09-10-readme-integration-guide-upgrade-patch` 的 `gen_migration.py` / `verify_assets.py` 是生成/校验参考；本任务需在本任务目录新写 1.3 版本，并把 1.2 资产纳入不可变历史。

## 1.3 Feature Evidence

模板内已落地、文档必须说明的用户可见能力：

1. 小修 `plan.py revise`；完成后默认原地 `revise`；`sequel`/`plans/` 仅显式兼容。
2. Codex 原生静默等待、编号子步骤归并、Step detail `--platform` 送达、`write_json` 保持 LF。
3. 任务创建询问收窄：仅在用户明确要写代码/实施时询问。
4. 任务目录前缀 `MM-DD-HHmm` 与同分钟错峰。
5. 规划门禁：`prd.md` 非空 `## Spec References`；子代理派发下 jsonl 须有真实条目。
6. 单次 `trellis-implement` 派发走完整执行计划链。
7. 审查循环退出以主会话复核后的 blocking 数为准。

`TEMPLATE-CONTENTS.md` 已登记 5 个 1.3 测试文件，缺 `test_review_severity_adjudication_contract.py` 与 `test_small_patch_and_sequel_contract.py`。

## Documentation Gaps

- `README.md` 与 `docs/接入指南.md` 仍把当前版本、升级矩阵、资产目录写成 1.2，升级来源只写 1.0/1.1，未写 1.2 收据升级与 1.3 能力。
- 接入指南能力对照表停在 1.2 合同测试，未列 1.3 七项能力。
- `overlay-upgrade.md` 验证段仍举例 1.1 收据升级到当前版本，未点名四代 manifest。

## Selected Scope

- 发布事实/资产：`VERSION`、`history/**`、`migrations/**`、本任务 `gen_migration.py`/`verify_assets.py`。
- 模板：删除 `.opencode/package.json`，新增 `.opencode/.gitignore`，改模板 OpenCode 合同测试。
- 工具：仅在测试或硬编码诊断仍写死 1.2 时调整；不把 `remove` 改成真实删文件。
- 验证：`tests/test_overlay_tools.py` 重定向到 1.3，新增 1.2 收据夹具；根/模板 Trellis 单测只读回归。
- 文档：README、接入指南、`TEMPLATE-CONTENTS.md`；Spec 仅补版本无关合同中仍写死 1.2 的验证举例。
- 禁改：根自用 Trellis（`.trellis/scripts/`、`.trellis/workflow.md`、`.agents/`、`.claude/`、`.codex/`、根 `.opencode/`）。`VERSION`/history/README 仍由本收尾更新。
- 禁改其余：`docs/开发计划.md` 未点名条目；提交/tag/推送。
