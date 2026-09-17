# 支持小修绕过执行计划与同一任务后续计划

## Workflow Settings

- Review level: reinforced

## Goal

修复已完成执行计划后的小修被逼走 `plan.py revise`、以及无法在同一任务另开后续计划的问题。小修直接改代码并在必要时同步 spec；大修冻结旧计划后另开下一份 live plan。旧 report 只做历史，不当活门。

## Background And Confirmed Facts

- 触发会话：原任务执行计划已完成 terminal `report` 后，模型要移除启动/运行误差窗口、相邻 raw 跳变限制和 5 秒超时。它先试图 `revise` 并把已完成 report 改成普通阶段，被审计拒绝；随后直接改代码且不同步 PRD/spec。
- 当前一份任务只有一组 live 文件：`<task>/execution-plan.json` + `<task>/execution-events.jsonl`。`revise` 重开同一份计划，不是另开一份。
- 已完成 phase 不能降级或改写内容；`report` 必须是唯一终端阶段，且须传递依赖所有其他 phase。因此“在已完成 report 后再挂工作阶段”会被 `validate` 拒绝。这是防伪史，不是小修通道。
- 模板 workflow 现行门禁：`Phase 2 source edits require an approved <task>/execution-plan.json`。没有“计划已闭环后的小修”出口，也没有 sequel plan 对象。
- `templates/embedded-c-overlay/.trellis/scripts/common/execution_plan.py` 与根目录对应文件当前字节相同，但本任务只改模板副本。
- 1.2 默认规则且本任务已确认：面向下游的功能只改 `templates/embedded-c-overlay/`；根目录 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/` 仅作只读参考。
- 本任务是父任务 `09-17-trellisforge-1-3-upgrade` 的功能子任务，必须排在固定收尾 `09-17-readme-integration-guide-upgrade-patch` 之前。不更新 `VERSION`、manifest、canonical、结构链、README 或接入指南。
- Hook 与 OpenCode 插件只展示计划状态，不推进状态。`plan.py` 在 Hook 全关时仍须独立正确。

## Explicit User Decisions

- 小修不走 `plan.py`，写成硬规则，不靠模型临时判断。
- 满足任一即可算小修：用户明确说这是小修，或明确说不走 `plan.py`；否则必须同时满足：不改验收，或只删用户已确认过时的限制；范围小、同一模块、不换架构；不需要新的 phase 拆分；文档默认不同步 PRD/design，只有以后还会踩的约定才写 spec。
- 小修动作：直接改代码 → 跑该跑的检查 → 必要时补 spec。不要 `revise`，不要新 phase，不要新任务。
- 进行中任务的当前 phase 范围内小修，就在当前 phase 里改，不要为小修重开计划。
- 同一任务允许多份顺序闭环的执行计划；不写死数量 2。同时只有一份 live plan，旧计划只读冻结。
- 每份 plan 仍是：≤ 8 个 phase、一个 terminal `report`、独立事件账本。
- 修复审查或实施中的阻塞问题默认走小修，不因此开 sequel。只有阻塞项过多、冗杂且复杂，需要新的拆步、检查和 report 时，才开下一份 plan。
- 开新 plan 而不是小修：目标变了但仍是同一需求线；需要新的拆步、检查和 report；旧验收部分作废，要改 PRD 但不值得新开 Trellis 任务；或阻塞修复已达到“过多、冗杂且复杂”。
- 开新任务而不是 sequel plan：需求主体换了；要独立归档、独立审查等级、独立回滚；旧任务已 archive。
- 文档同步按文件拆：spec 写可复用约定；PRD 在本轮验收变了时必须改；小修通常不动 design/implement.md；小修不动 execution-plan，大修开新 plan 不改旧 plan。
- 交付范围只改下游模板 `templates/embedded-c-overlay/`，不改根目录自用 Trellis。

## Requirements

### R1 小修退出执行计划门禁

- 模板 workflow、implement Agent、plan 协议注入必须写明小修硬规则：用户明确声明优先；否则适用其余四条客观门槛。
- 满足门槛时，禁止 `revise`、禁止新 phase、禁止新任务；直接改代码、跑检查、必要时补 spec。
- 修复阻塞问题默认按小修处理。只有阻塞项过多、冗杂且复杂时才允许 `sequel`。
- 当前 live plan 仍有未完成 phase 时，范围内小修继续记在该 phase，不另开计划。
- live plan 已完成全部 phase（含 terminal report）后，小修不碰任何执行计划文件。
- `plan.py` 不自动判定一次编辑是否小修；门槛由 workflow 文本约束模型，不新增分类器。

### R2 同一任务后续计划

- live plan 全部完成后，允许冻结旧计划并另开下一份 live plan。
- 同时最多一份 live plan；`status`、breadcrumb、protocol 只展示 live plan。
- 不设数量上限 2；第 3 份及以后同样合法。
- 每份 plan 保持 schema 3：≤ 8 phase、一个 terminal `report`、独立事件账本。
- `revise` 只重开当前 live plan，不承担 sequel。
- 禁止把已完成 report 改成普通阶段；该拒绝继续存在。
- 仅有旧单文件布局的任务仍可作为第 1 份 live plan 使用，无需先迁移。

### R3 文档同步与发布边界

- 验收变了必须先改 PRD，再开 sequel plan。
- 小修默认可不改 PRD/design；可复用约定写入任务范围内允许的 spec 路径，本任务不扩展到发布收尾文档。
- 本子任务不更新 `VERSION`、历史 canonical、版本 manifest、结构迁移链、README 或接入指南。

## Acceptance Criteria

- [ ] 模板 workflow 与 implement 协议明确：用户明确说小修或不走 `plan.py`，或满足其余四条客观门槛时，不走 `plan.py revise`、不新建 phase、不新建任务。
- [ ] 模板 workflow 与 implement 协议明确：修复阻塞问题默认走小修；只有阻塞项过多、冗杂且复杂时才开 sequel。
- [ ] 当前 phase 未完成时，范围内小修仍在该 phase 内实施和记录检查。
- [ ] live plan 的 report 完成后，小修不修改已冻结或已完成的执行计划文件。
- [ ] live plan 全部完成后可另开下一份 live plan；旧 plan 只读，report 历史保留。
- [ ] 不存在数量上限 2；第 3 份及以后同样合法。
- [ ] 同时最多一份 live plan；`status` 与注入面包屑只展示 live plan。
- [ ] 已完成 report 仍不能被改写成普通阶段；该拒绝继续存在。
- [ ] 仅有旧单文件布局的任务仍可 `validate` / `status` / 推进，无需先迁移。
- [ ] 模板内执行计划测试覆盖：旧单文件兼容、sequel 冻结旧 plan、同时只有一份 live、禁止改写已完成 report、`revise` 不创建 sequel。
- [ ] 实际功能改动仅位于 `templates/embedded-c-overlay/`；根目录自用 Trellis 无本任务功能修改。
- [ ] 项目规定的 Python 单测、Python 语法检查和 `git diff --check` 通过；构建、部署和硬件验证报告为 `not applicable`。

## Out Of Scope

- 修改根目录自用 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/`、`.opencode/`。
- 更新 `VERSION`、历史 canonical、版本 manifest、结构迁移链、README 或接入指南。
- 改变 `minimal` / `report` 两级校验模型，或取消已完成 phase 的防伪史。
- 让 `plan.py` 自动判断一次编辑算不算小修。
- 修改 Channel worker 生命周期、审查等级或提交授权。
- 将根目录 `.opencode/package.json` 的本机插件钉死纳入本任务。

## Key Decisions

- 小修是 workflow 硬规则，不是 `plan.py` 运行时分类。
- sequel 使用兼容布局：第 1 份继续占用任务根目录 `execution-plan.json`；后续计划进入 `plans/<n>/`，任务根文件成为指向 live 的指针。
- 开 sequel 的 CLI 是 `plan.py sequel --reason "..."`，只在当前 live plan 全部 phase 完成后允许。
- 各 sequel 的 `final-report.md` 分目录存放，避免互相覆盖。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
