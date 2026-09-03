# 模板与文档

## 发布边界

- `templates/embedded-c-overlay/` 是面向下游嵌入式 C 项目的发布模板；其中的硬件术语仅属于模板示例，不代表本仓库拥有硬件目标。
- `templates/language-adaptation/` 描述迁移到其他语言时必须替换的 C 特化规则。
- `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 和 `.trellis/.template-hashes.json` 是运行状态，禁止加入发布模板。
- `.git/trellisforge-backup/` 是安装器的 Git 元数据备份，不属于工作树或模板。

## 文档契约

README 负责说明定位、最短安装命令和覆盖层边界；`docs/接入指南.md` 负责逐步接入、合并规则、验证命令和升级维护。新增或改变模板目录时同步更新这两处目录说明。

## 内容要求

- 模板正文中的项目占位符必须由安装器替换，发布前扫描尖括号标记和初始化模板提示语等残留。
- 文档命令使用 Windows PowerShell 语法，并区分 `pass`、`fail`、`not run`、`not applicable`。
- 不把下游项目的构建、硬件验证或产品事实写成 TrellisForge 自身已经验证的事实。
