# TrellisForge 1.3 发布收尾实施计划

## 实施前门禁

- 确认当前任务来源为精确的 `session:*` 指针，任务状态仍为 `planning`，并在用户批准后才运行 `task.py start`。
- 复核父任务九个前置子任务均已归档，本任务仍是父任务最后一个 child。
- 读取 PRD、design、research、implement/check JSONL 与相关 Spec；记录 `VERSION`、1.0/1.1/1.2 manifest、对象库和结构步骤的实施前哈希。
- 确认工作树没有未识别改动；根 `.opencode/package.json` 为用户既有脏文件，必须保留，不得回滚或提交进本任务。
- 写入白名单见 PRD R6。禁止改根自用 `.trellis/scripts/`、`.agents/`、`.claude/`、`.codex/`、根 `.opencode/`。

## 实施顺序

1. **调整模板交付物（OpenCode 依赖清单退出官方文件）**
   - 删除 `templates/embedded-c-overlay/.opencode/package.json`。
   - 新增 `templates/embedded-c-overlay/.opencode/.gitignore`，忽略 `package.json` 与 `package-lock.json`。
   - 改 `templates/embedded-c-overlay/.trellis/scripts/tests/test_opencode_platform_contract.py`：不再要求模板内 `package.json`，改为断言 gitignore。
   - 不修改根目录 `.opencode/` 与根 `test_opencode_platform_contract.py`。

2. **建立 1.3 版本资产**
   - 将 `VERSION` 提升为 1.3。
   - 在本任务目录新增 `gen_migration.py` 与 `verify_assets.py`：验证并保留 1.0/1.1/1.2 资产，只追加 1.3 manifest 与新对象。
   - 新增 `structural/1.2-to-1.3.json`：`preserve-schema-1`，`actions` 含 `{ "action": "remove", "path": ".opencode/package.json" }`。
   - 运行资产校验，任何旧资产变化或 live/1.3 不一致立即停止。1.3 不得再引用 `.opencode/package.json`。

3. **对齐安装/升级回归到 1.3**
   - 更新 `tests/test_overlay_tools.py`：`TARGET_VERSION=1.3`，新增 1.2 收据夹具。
   - 覆盖首次安装（无官方 `package.json`、有 gitignore）、1.0 无收据直达、1.1→1.3、1.2→1.3（旧 `package.json` 留盘且退出收据）、1.3 幂等、相邻链三步组合与拒绝、新路径冲突、用户定制合并、预检零写入和事务回滚。
   - 只在测试或诊断仍写死 1.2 目标语义时改注释/断言；不把 `remove` 改成真实删文件。

4. **更新 Spec 与发布文档**
   - `overlay-upgrade.md`：来源独有 `remove` 不删磁盘；验证举例改为四代资产。
   - `TEMPLATE-CONTENTS.md`：1.3 事实、7 个新测试、gitignore、不再交付 `package.json`。
   - 最后更新 `README.md` 与 `docs/接入指南.md`：R4 八项能力、本机 `npm install @opencode-ai/plugin`、已跟踪文件的 `git rm --cached`、1.0/1.1/1.2→1.3 命令。

5. **执行验证与 reinforced 审查**
   - 运行三套 Python 单测、Python 语法检查、PowerShell 解析、资产验证、缓存/占位符扫描和交付路径 `git diff --check`。
   - 运行工具测试覆盖的临时 Git 仓库安装/升级冒烟。
   - 按 `reinforced` 对 affected-scope 执行独立审查并修复阻塞项。

## Validation Commands

```powershell
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
python -B -m unittest discover -s tests -p "test_*.py"
python -B .trellis/tasks/09-17-readme-integration-guide-upgrade-patch/verify_assets.py

$pythonFiles = Get-ChildItem .trellis/scripts,.claude/hooks,.codex/hooks,templates/embedded-c-overlay/.trellis/scripts,templates/embedded-c-overlay/.claude/hooks,templates/embedded-c-overlay/.codex/hooks,tests -Recurse -Filter *.py | ForEach-Object FullName
python -m py_compile @pythonFiles

$psFiles = @('tools/lib/TrellisForgeOverlay.psm1','tools/install-embedded-c-overlay.ps1','tools/update-embedded-c-overlay.ps1')
foreach ($file in $psFiles) { [void][scriptblock]::Create((Get-Content -LiteralPath $file -Raw -Encoding UTF8)) }

rg -n "当前版本：`1\.2`|首次接入 TrellisForge 1\.2|升级到 1\.2（" README.md docs/接入指南.md templates/embedded-c-overlay/TEMPLATE-CONTENTS.md
Test-Path -LiteralPath "templates/embedded-c-overlay/.opencode/package.json"
rg -n "package\.json|package-lock\.json" templates/embedded-c-overlay/.opencode/.gitignore
rg -n "<[^>]+>|__pycache__|\.py[co]$" templates/embedded-c-overlay
git diff --check -- VERSION history migrations tools tests README.md docs/接入指南.md templates/embedded-c-overlay .trellis/spec/main/tooling/overlay-upgrade.md .trellis/tasks/09-17-readme-integration-guide-upgrade-patch
```

`Test-Path` 对模板 `package.json` 必须为 `False`。Python 语法检查产生的缓存只在受控目录确认后清理。全局 `git diff --check` 可能仍被既有 CRLF `task.json` 干扰；交付验收以 scoped 检查为准。

## 验收映射

| 验收主题 | 实施步骤 |
| --- | --- |
| 1.3 版本事实与历史资产不可变 | 2、5 |
| `package.json` 退出官方交付、gitignore 生效 | 1、2、3、4 |
| 正文直达 1.3、结构 remove 不删盘 | 3、5 |
| 八项能力与升级/本机依赖文档 | 4、5 |
| 全量验证与 reinforced 审查 | 5 |

## 风险文件与回滚点

- `history/embedded-c-overlay/**`：旧 manifest/对象禁止重写。
- `migrations/.../1.2-to-1.3.json`：漏写 `remove` 会让 1.2 升级 fail closed。
- `templates/.../test_opencode_platform_contract.py`：必须与删文件同批。
- `tests/test_overlay_tools.py`：1.2 夹具来自历史 manifest，不能从 1.3 live 反推。
- 根 `.opencode/package.json`：用户既有脏改动，禁止纳入本任务 diff。
- 不提交、不推送、不打 tag。
