# TrellisForge 1.2 发布收尾 — 最终验收报告

Active task: `.trellis/tasks/09-10-readme-integration-guide-upgrade-patch`
执行计划: revision 1，6 阶段全部完成（discover-baseline → assets-1.2 → chain-compose → tests-upgrade → docs-spec → verify-final）。

## 变更文件

### 版本与历史资产（assets-1.2）
- `VERSION`：`1.1` → `1.2`（保持无尾随换行的原字节格式）。
- `history/embedded-c-overlay/versions/1.2/manifest.json`：新增，151 个受管条目（150 模板文件 + `AGENTS.md.trellisforge-template`），与 live 模板逐文件一致。
- `history/embedded-c-overlay/objects/<sha256>`：仅追加 72 个新 canonical 对象（162 总数）；1.0/1.1 引用的对象字节未动（记录哈希复核：v1.0 manifest `ac26b097…`、v1.1 manifest `f0ed1f8f…`、`1.0-to-1.1.json` `66222336…` 均不变）。
- `migrations/embedded-c-overlay/structural/1.1-to-1.2.json`：新增相邻结构步骤（schema 1、`receipt_transition: preserve-schema-1`、`actions: []`）。
- 任务目录新增 `gen_migration.py`（先验证不可变历史与 e40a942 保真，再仅追加 1.2 资产）与 `verify_assets.py`（三代 manifest、对象自哈希/无孤儿、1.2==live==HEAD、相邻链连续性、无方案 A 残留、`git diff --check`）。

### 工具（chain-compose）
- `tools/lib/TrellisForgeOverlay.psm1`：`Get-OverlayStructuralChain` 重写为按 `versions/` manifest 版本序列组合相邻步骤，逐步校验 schema/from/to/动作白名单/收据转换白名单（`bootstrap-schema-1`、`preserve-schema-1`），返回 `Steps`/`Actions`/`ReceiptTransition`；缺清单、倒序、等序、断步、非法动作/转换均 `unsupported` 抛出。头部注释改为版本无关描述。
- `tools/update-embedded-c-overlay.ps1`：使用聚合链（`.ReceiptTransition`/`.Actions`）；修复来源独有路径检查中 `$_` 遮蔽（改为显式 `foreach` + 聚合动作匹配）；全部用户可见建议、结束提示与诊断改为 `$from`/`$forgeVersion` 动态版本，不再硬编码「1.1 模板」「1.0 基线」。
- `tools/install-embedded-c-overlay.ps1`：未改动（已批准计划各阶段 scope.write 均不含安装器；其功能全部动态读取 `VERSION`，无功能性 1.1 硬编码，docs-scan 禁则模式零命中）。

### 测试（tests-upgrade）
- `tests/test_overlay_tools.py`：重写为 1.2 目标、47 项。新增：不可变 1.1 manifest/canonical 渲染 + 真实 schema-1 收据的 1.1 下游夹具（不经过当前安装器）；`1.1→1.2` 干净升级/定制合并/冲突零写入保留 1.1 收据；`1.0→1.2` 正文一步直达断言（双跳变更文件终态等于 1.2 渲染且绝不等于 1.1 渲染、收据 canonical 为 1.2）；结构链组合断言（1.0→1.2 加载 2 步、1.1→1.2 加载 1 步，经合成发布树拒绝断链/非法动作/非法转换/版本违序）；OpenCode 新增路径缺失新增/一致 already-current/不同冲突零写入；无收据 `-FromVersion 1.1` 拒绝。保留首装、备份回滚、占位符、LF/CRLF、路径安全、缓存拒绝、Trellis 状态不修改等回归。

### Spec 与文档（docs-spec）
- `.trellis/spec/main/tooling/overlay-upgrade.md`：改为版本无关合同；新增「相邻链组合」节（结构组合与正文直达分离）、转换白名单、来源独有路径覆盖要求、维护契约（仅追加、不重写历史、不建跨版本直连文件）。
- `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md`：收据/历史资产段更新为 1.2 事实（三代 manifest、两条相邻步骤、正文直达与结构组合语义）；OpenCode 行的收尾待办改为已完成表述。
- `README.md`：版本矩阵（1.2 / Trellis 0.6.10）、首装与 1.0/1.1→1.2 命令、五级审查序列、Channel 混合上下文与 fail-closed 预检、阻塞修复责任分流、OpenCode 能力与限制、目录与交付物（1.2 manifest + 相邻结构步骤）、安全边界与测试覆盖描述。
- `docs/接入指南.md`：三平台支持声明（OpenCode 需 Node.js、原生 Task 子代理、provider/`trellis mem`/端到端限制）；首次接入 1.2（含 OpenCode 接入确认与命令验证）；「从 1.0 或 1.1 升级到 1.2」两类来源识别、预检/冲突/应用事务/恢复/幂等；能力对照表补五级审查、上下文预检、修复责任、OpenCode 闭包与 1.2 合同测试行；语言迁移清单纳入 `.opencode/`。

## 各阶段与最终检查结果

| 阶段 | 检查 | 结果 | 证据 |
| --- | --- | --- | --- |
| assets-1.2 | asset-verify | pass | `verify_assets.py` 全 OK，exit 0 |
| chain-compose | powershell-parse | pass | 3 文件 `Parser::ParseFile` 无错误 + 链冒烟（2 步/1 步/4 类拒绝） |
| tests-upgrade | unit-tests-tools | pass | 47 项 OK（83.7s） |
| docs-spec | docs-scan | pass | 禁则模式（1.1 模板 / 1.0 -> 1.1 / 1.0→1.1 / 只支持两平台）在 README、接入指南、tools、TEMPLATE-CONTENTS、overlay-upgrade.md 零命中 |
| verify-final | test | pass | 根 99 项 OK + 模板 154 项 OK + 工具 47 项 OK（共 300） |
| verify-final | asset-verify | pass | 复跑全 OK |
| verify-final | python-syntax | pass | `py_compile` 93 个受控文件 + 2 个任务脚本，exit 0；生成的 14+1 个 `__pycache__` 目录列出后全部清理 |
| verify-final | powershell-parse | pass | 复跑 3 文件 PARSE-OK + 链冒烟一致 |
| verify-final | docs-scan | pass | 禁则 grep exit 1（零命中）；模板缓存文件扫描为空；`<...>` 匹配 1296 处均为设计内模板占位符（AGENTS.md.template 人工合并、report 骨架、`<task-path>` 等，安装器对三类 token 全量替换有回归） |
| verify-final | diff-check | pass | 交付路径（VERSION/history/migrations/tools/tests/README/docs/spec/templates）`git diff --check` exit 0；verify_assets 内 history/migrations 检查 OK |

## 安装/升级冒烟

工具测试即以临时 Git 仓库运行两个入口脚本完成首装 1.2、1.0 入场直达、1.1 收据升级、幂等与回滚冒烟（47 项覆盖），未在真实下游项目执行。

## 跳过项

- 提交前全盘终审：按本任务 PRD 定制例外跳过（仅记录于本任务规划，不改项目默认）。
- 未执行 commit/push/tag/release（任务约束）。
- 安装器注释中的历史「1.1」字样：所在文件不在已批准计划任何阶段的 scope.write 内，未改动；功能与用户可见输出均动态取自 `VERSION`，docs-scan 禁则零命中。

## 已知风险与限制

- `task.json` / `prd.md` / `implement.md` 三个规划文件在进入本会话前已被主会话修改且为 CRLF，全仓 `git diff --check` 对其报 trailing-whitespace；非本实现改动，交付路径检查独立通过。
- OpenCode 真实 CLI/TUI 端到端未在当前环境验证；`trellis channel --provider opencode` 与 OpenCode `trellis mem` 读取器不在本次范围（文档已如实声明）。
- 上游 Trellis 基线保持 `0.6.10`，未随 Forge 1.2 变化。
