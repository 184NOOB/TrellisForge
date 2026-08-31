# TrellisForge

TrellisForge 是一套面向嵌入式 C 项目的 Trellis 项目级覆盖模板。它不替代
`trellis init`，而是在初始化后的仓库中补齐以下能力：

- 规划阶段的 Grill Me 与显式审批门禁；
- Claude Code 与 Codex 的子代理上下文注入；
- implement/check/research 代理定义；
- 子代理批量读取、合并编辑、分阶段验证、最小复验与停止条件；
- 项目级 `light`、`standard`、`strict` 审查合同；
- 面向嵌入式 C 的构建、硬件验证和硬件合同边界。

从 [docs/接入指南.md](docs/接入指南.md) 开始。最短接入命令为：

```powershell
# 在目标项目根目录执行
trellis init
# 在 TrellisForge 根目录执行
& .\tools\install-embedded-c-overlay.ps1 -TargetRoot C:\path\to\project -ProjectPrefix example -ProjectName "Example Firmware" -Force
```

安装后必须按指南填写 `AGENTS.md` 和 `.trellis/spec/` 中的项目事实，再提交。
模板从参考工程抽取，但不含其产品源码、任务记录、Flash 布局或硬件协议。
