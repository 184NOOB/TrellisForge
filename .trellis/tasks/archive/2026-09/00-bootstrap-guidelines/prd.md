# Bootstrap Task: 建立 TrellisForge 工具仓库规范

本任务用于把 `trellis init` 生成的前后端占位 Spec，改造成与 TrellisForge 实际结构一致的项目规范。TrellisForge 是工具、模板和文档仓库，没有后端服务、前端应用、数据库或固件产品源码。

## Workflow Settings

- Review level: standard
- Package: `main`
- Scope: `.trellis/spec/main/tooling/`、`.trellis/tasks/00-bootstrap-guidelines/`

## 状态

- [x] 核对 README、接入指南、AGENTS.md 和真实目录
- [x] 删除不适用的 backend/frontend 占位 Spec
- [x] 建立 tooling Spec，并引用 Python、PowerShell、模板和文档实例
- [x] 完成执行计划、验证和最终报告

## 目标

1. 让 Spec 索引只暴露 `main/tooling` 这一真实包层。
2. 固化 Python 工作流脚本、PowerShell 安装器、模板发布边界和文档契约。
3. 提供可复现的单测、语法、占位符、差异和安装器冒烟验证方法。

## 非目标

- 不新增后端或前端实现规范。
- 不修改安装器、Hook、代理或模板运行逻辑。
- 不把下游嵌入式 C 项目的硬件事实写入本仓库规范。

## 验收标准

- `.trellis/spec/backend/` 和 `.trellis/spec/frontend/` 不再存在，且 `.trellis/spec/main/tooling/index.md` 及其链接文件全部存在。
- `.trellis/spec/` 不含初始化占位文本；规范中的路径、命令和示例均能在仓库中定位。
- `task.py validate 00-bootstrap-guidelines`、执行计划 `validate/start/record/done` 全部成功。
- Python 单测、Python 语法检查和 `git diff --check` 通过；构建与硬件验证明确为 `not applicable`。
- 最终报告记录变更范围、验收证据和未执行类别。

## Planning Convergence

- Evidence: README、`docs/接入指南.md`、`AGENTS.md`、`.trellis/spec/shared/` 及脚本/测试目录已核对。
- Decisions: 采用单包 `main` 的 `tooling` Spec；删除不适用的 backend/frontend 层；不改运行逻辑。
- User approval: 用户已明确要求继续完成接入任务。
