# TrellisForge 1.2 发布收尾实施计划

## 实施前门禁

- 确认当前任务来源为精确的 `session:*` 指针，任务状态仍为 `planning`，并在用户批准后才运行 `task.py start`。
- 复核父任务四个前置子任务均已归档，本任务仍是父任务最后一个 child。
- 读取 PRD、design、research、implement/check JSONL 与相关 Spec；记录 `VERSION`、1.0/1.1 manifest、对象库和结构步骤的实施前哈希。
- 确认工作树没有未识别改动；若出现用户改动，保留并重新评估写入范围。

## 实施顺序

1. **建立 1.2 版本资产**
   - 将 `VERSION` 提升为 1.2。
   - 在本任务目录新增/改造 `gen_migration.py` 与 `verify_assets.py`：验证并保留 1.0/1.1 资产，只追加 1.2 manifest 与新对象。
   - 新增 `structural/1.1-to-1.2.json`，确认本次 `actions=[]`、receipt schema 1 保持。
   - 运行资产校验，任何旧资产变化或 live/1.2 不一致立即停止。

2. **让结构链支持相邻步骤组合**
   - 修改 `tools/lib/TrellisForgeOverlay.psm1`，按 manifest 版本序列加载并验证完整相邻结构链，保留 Windows PowerShell 5.1 语法和现有导出边界。
   - 修改 `tools/update-embedded-c-overlay.ps1` 使用聚合结构链，修复来源独有路径动作匹配，并把硬编码 1.1/1.0 诊断替换为动态来源/目标版本；正文仍只执行一次“来源 canonical + 下游当前文件 + 1.2 模板”三方合并，不把相邻结构步骤当作正文升级阶段。
   - 只在需要时更新安装器中的版本特定注释或诊断；不改变安装清单、`-Force`、备份和回滚语义。

3. **扩展安装/升级回归**
   - 更新 `tests/test_overlay_tools.py` 为 1.2 目标，新增由 1.1 manifest/receipt 构建的旧版下游夹具。
   - 覆盖首次安装 1.2、1.1->1.2、1.0 无收据直达 1.2、1.2 幂等、相邻链断裂/非法内容、OpenCode 新路径冲突、用户定制合并、预检零写入和事务回滚；明确断言 1.0->1.2 正文只从 1.0 canonical 合并一次且不读取或落盘 1.1 正文，同时结构迁移加载两个相邻步骤，1.1->1.2 只加载后一结构步骤。
   - 保留路径安全、占位符、LF/CRLF、Trellis 状态不修改和缓存拒绝回归。

4. **更新 Spec 与发布文档**
   - 将 `.trellis/spec/main/tooling/overlay-upgrade.md` 更新为版本无关的最新目标/相邻链组合合同。
   - 更新 `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md` 的 1.2 版本事实、三平台目录、收据和历史资产说明。
   - 最后更新 `README.md` 与 `docs/接入指南.md`，按最终 CLI/测试事实说明五级审查、Channel 主动读取、阻塞修复责任、OpenCode 能力与限制，以及 1.0/1.1 到 1.2 的命令。

5. **执行验证与 strict 审查（任务定制例外）**
   - 运行三套 Python 单测、Python 语法检查、PowerShell 解析、资产验证、缓存/占位符扫描和 `git diff --check`。
   - 运行工具测试覆盖的临时 Git 仓库安装/升级冒烟；不把下游构建、部署或硬件验证伪报为已执行。
   - 按 `strict` 在重大实施批次后执行独立审查并修复阻塞项；修复后重跑受影响检查，实质范围变化才重新进入相应审查。
   - 本任务明确跳过提交前的全盘终审；该例外只写入本任务规划，不修改项目级审查机制或 Spec。

## Validation Commands

```powershell
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s tests -p "test_*.py"
python -B .trellis/tasks/09-10-readme-integration-guide-upgrade-patch/verify_assets.py

$pythonFiles = Get-ChildItem .trellis/scripts,.claude/hooks,.codex/hooks,templates/embedded-c-overlay/.trellis/scripts,templates/embedded-c-overlay/.claude/hooks,templates/embedded-c-overlay/.codex/hooks,tests -Recurse -Filter *.py | ForEach-Object FullName
python -m py_compile @pythonFiles

$psFiles = @('tools/lib/TrellisForgeOverlay.psm1','tools/install-embedded-c-overlay.ps1','tools/update-embedded-c-overlay.ps1')
foreach ($file in $psFiles) { [void][scriptblock]::Create((Get-Content -LiteralPath $file -Raw -Encoding UTF8)) }

rg -n "1\.1 模板|1\.0 -> 1\.1|1\.0→1\.1|当前覆盖层只支持 Claude Code 和 Codex" README.md docs/接入指南.md tools templates/embedded-c-overlay/TEMPLATE-CONTENTS.md .trellis/spec/main/tooling/overlay-upgrade.md
rg -n "<[^>]+>|__pycache__|\.py[co]$" templates/embedded-c-overlay
git diff --check
```

Python 语法检查生成的 `__pycache__` / `.pyc` 只在列出并确认位于上述受控目录后清理，再复查模板和工作树无缓存残留。

## 验收映射

| 验收主题 | 实施步骤 |
| --- | --- |
| 1.2 版本事实与历史资产不可变 | 1、5 |
| 正文直达 1.2、结构迁移按相邻步骤组合 | 2、3、5 |
| 三方合并、冲突零写入、备份回滚 | 2、3、5 |
| 五级审查、Channel、修复责任、OpenCode 文档 | 4、5 |
| 全量验证与 strict 批次审查（提交前不做全盘终审） | 5 |

## 风险文件与回滚点

- `history/embedded-c-overlay/**`：旧 manifest/对象禁止重写；资产步骤单独验证后再继续。
- `tools/lib/TrellisForgeOverlay.psm1` 与 `tools/update-embedded-c-overlay.ps1`：共同决定版本链和事务前预检，必须与工具测试同批审查。
- `tests/test_overlay_tools.py`：旧版夹具必须来自历史 manifest/receipt，不能从 1.2 live 模板反推。
- `README.md`、`docs/接入指南.md`、`TEMPLATE-CONTENTS.md`：最后修改并与实际命令、输出、限制逐项核对。
- 不提交、不推送、不打 tag；提交计划属于后续独立批准门禁。
