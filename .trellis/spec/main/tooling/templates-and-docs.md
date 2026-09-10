# 模板与文档

## 发布边界

- `templates/embedded-c-overlay/` 是面向下游嵌入式 C 项目的发布模板；其中的硬件术语仅属于模板示例，不代表本仓库拥有硬件目标。
- `templates/language-adaptation/` 描述迁移到其他语言时必须替换的 C 特化规则。
- `.trellis/tasks/`、`.trellis/workspace/`、`.trellis/.runtime/` 和 `.trellis/.template-hashes.json` 是运行状态，禁止加入发布模板。
- `.git/trellisforge-backup/` 是安装器的 Git 元数据备份，不属于工作树或模板。
- `history/embedded-c-overlay/`（对象库 + 版本 manifest）与
  `migrations/embedded-c-overlay/structural/` 是升级交付物，不属于发布模板本身。

## 下游功能修改的默认归属

- 除非用户或任务 PRD 明确要求修改 TrellisForge 仓库自身的工作流实例，面向下游项目的新功能、行为调整和缺陷修复只修改 `templates/embedded-c-overlay/` 内的对应文件。
- 根目录 `.trellis/`、`.agents/skills/`、`.claude/` 和 `.codex/` 是 TrellisForge 自身正在使用的项目级工作流实现。实施者可以读取、比较或运行它们来确认现有行为，但不得仅因模板存在对应路径就反向修改这些文件。
- “修改根目录自用 Trellis 时必须同步相关模板”是单向约束，不表示“修改模板时必须同步根目录”。任务规划必须分别列出模板写入范围和根目录禁改范围，避免把参考实现误判为交付目标。
- 模板功能的实现和契约测试优先落在 `templates/embedded-c-overlay/` 内；允许只读运行仓库级检查，但除非任务明确授权，不修改根目录自用 Trellis 的测试或运行时实现。
- 版本号、历史对象、版本 manifest、结构迁移链、README 和接入指南只由明确拥有发布收尾职责的任务更新，普通模板功能子任务不得提前扩展到这些交付物。

错误做法：为实现一个下游审查等级，先修改根目录 `.trellis/workflow.md`，再复制到模板。

正确做法：只修改 `templates/embedded-c-overlay/.trellis/workflow.md` 及模板内相关 Skill、Agent、门禁和测试；根目录对应文件仅作为只读参考。

## 文档契约

README 负责说明定位、最短安装命令和覆盖层边界；`docs/接入指南.md` 负责逐步接入、合并规则、验证命令和升级维护。新增或改变模板目录时同步更新这两处目录说明。

## 内容要求

- 模板正文中的项目占位符必须由安装器替换，发布前扫描尖括号标记和初始化模板提示语等残留。
- 文档命令使用 Windows PowerShell 语法，并区分 `pass`、`fail`、`not run`、`not applicable`。
- 不把下游项目的构建、硬件验证或产品事实写成 TrellisForge 自身已经验证的事实。
