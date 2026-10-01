# TrellisForge 1.3 发布收尾最终报告

任务：`.trellis/tasks/09-17-readme-integration-guide-upgrade-patch`

## 交付结果

TrellisForge 1.3 已作为可安装、可升级、可说明的正式交付落地：

- 仓库版本事实提升到 `1.3`（`VERSION`），上游 Trellis 基线保持 `0.6.10`。
- `history/embedded-c-overlay/versions/1.3/manifest.json` 共 158 个受管文件；
  新增 canonical 对象 38 个（对象库 162 → 200），1.0/1.1/1.2 历史资产字节不变。
- `migrations/embedded-c-overlay/structural/1.2-to-1.3.json`：
  `receipt_transition=preserve-schema-1`，唯一动作
  `{ "action": "remove", "path": ".opencode/package.json" }`。
- `.opencode/package.json` 退出官方交付：模板源树删除，模板新增
  `.opencode/.gitignore`（忽略 `package.json`、`package-lock.json`、
  `node_modules`、`bun.lock`）。
- 升级器对 `structural-remove` 路径只让其退出新收据与受管集合，不写入、
  不删除下游磁盘文件（`tools/update-embedded-c-overlay.ps1` 应用循环跳过）。
- README、`docs/接入指南.md`、`TEMPLATE-CONTENTS.md` 与
  `.trellis/spec/main/tooling/overlay-upgrade.md` 已同步 1.3 事实、八项能力、
  本机 `npm install @opencode-ai/plugin` 与 `git rm --cached` 规则、
  `remove` 不删磁盘说明。

## 修改/新增文件

- `VERSION`：`1.2` → `1.3`。
- `history/embedded-c-overlay/versions/1.3/manifest.json`（新增，158 条）。
- `history/embedded-c-overlay/objects/<sha256>`（新增 38 个对象，仅追加）。
- `migrations/embedded-c-overlay/structural/1.2-to-1.3.json`（新增）。
- `templates/embedded-c-overlay/.opencode/package.json`（删除）。
- `templates/embedded-c-overlay/.opencode/.gitignore`（新增）。
- `templates/embedded-c-overlay/.trellis/scripts/tests/test_opencode_platform_contract.py`：
  不再要求模板内 `package.json`，改为断言 `.gitignore` 覆盖并验证该文件不存在；
  collector parity 放行本机生成清单。
- `templates/embedded-c-overlay/TEMPLATE-CONTENTS.md`：1.3 版本事实、7 个新增
  测试、`.opencode/.gitignore`、依赖清单不再交付。
- `tests/test_overlay_tools.py`：`TARGET_VERSION=1.3`、新增 1.2 收据夹具与
  `UpgradeFrom12Tests`，覆盖首次安装、1.0/1.1/1.2 升级、`remove` 留盘与退出
  收据、gitignore 冲突零写入、定制合并、结构链三步组合。
- `tools/update-embedded-c-overlay.ps1`：应用阶段跳过 `structural-remove`，
  该路径不进入新收据且磁盘文件保持不动。
- `README.md`、`docs/接入指南.md`：1.3 兼容矩阵、命令、能力、边界与 OpenCode
  本机依赖流程。
- `.trellis/spec/main/tooling/overlay-upgrade.md`：`remove` 不删磁盘说明与
  四代资产验证举例。
- 任务目录：`gen_migration.py`、`verify_assets.py`、本报告。

## 执行计划阶段结果

| 阶段 | 状态 | 结果 |
| --- | --- | --- |
| discover-baseline | completed | 记录基线哈希；确认 live 模板相对 1.2 仅 7 个新增测试 + 本任务预期的删除/新增/修改 |
| template-unofficialize-package-json | completed | 模板删除 `package.json`、新增 `.gitignore`、合同测试改写 |
| assets-1.3 | completed | 生成 1.3 manifest（158）与相邻结构步骤；历史资产校验不变 |
| tests-upgrade | completed | 升级器 `structural-remove` 修复 + 工具回归重定向 1.3（52 项） |
| docs-spec | completed | Spec 与发布文档同步；扫描无过期“当前 1.2”表述 |
| verify-final | completed | 全量验收检查与独立/最终回归 |

## 检查结果

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| root-tests | `python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"` | pass：154 项 OK |
| template-tests | `python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"` | pass：271 项 OK |
| unit-tests-tools | `python -B -m unittest discover -s tests -p "test_*.py"` | pass：52 项 OK（含 1.2→1.3 `remove` 留盘、1.0/1.1/1.2 升级、冲突零写入、回滚） |
| asset-verify | `python -B .trellis/tasks/09-17-readme-integration-guide-upgrade-patch/verify_assets.py` | pass：四代 manifest/对象/结构链、无孤儿、无方案 A 残留、`git diff --check`（history/migrations） |
| py-compile | `python -m py_compile` 列出的 105 个 Python 文件 | pass（exit 0）；缓存已清理 |
| powershell-parse | `Parser::ParseFile` 解析模块 + 安装/升级入口 | pass：3/3 |
| diff-check | `git diff --check` 交付路径（VERSION、history、migrations、tools、tests、README、接入指南、模板、Spec） | pass（exit 0） |
| docs-scan | 三个文档 + 模板 `.opencode` 状态扫描 | pass：1.3 事实、八项能力、`npm install`、`git rm --cached`、`structural-remove`；无过期当前版本表述 |
| template-scan | 模板占位符/缓存扫描 | pass：0 缓存；仅 4 处已知人工合并标记/断言文本 |

- 安装/升级冒烟：由 `tests/test_overlay_tools.py` 在临时 Git 仓库执行
  （首装 1.3、1.0 直达、1.1/1.2 收据升级、幂等、冲突零写入、备份与回滚）。
- 构建/部署/硬件验证：`not applicable`（本仓库不产出固件或可执行产品）。
- 下游目标仓库验证：`not run`（需使用者在真实项目中执行；本仓库无下游环境）。

## 已跳过项与说明

- 全局 `git diff --check` 仍被既有任务元数据（`task.json` CRLF 尾随空白、
  `prd.md` EOF 空行）报出；这些是任务工作流产物而非交付文件，按
  `implement.md` 以交付路径 scoped 检查为准（exit 0）。
- 模板中 4 处 `<PROJECT_PREFIX>`/`<PROJECT_NAME>` 为已知人工合并标记与合同
  测试断言文本，非安装残留；安装后占位符替换由工具回归断言。
- 未执行提交、推送、tag；未改动根目录自用 Trellis
  （`.trellis/scripts/`、`.trellis/workflow.md`、`.agents/`、`.claude/`、
  `.codex/`、根 `.opencode/` 及既有脏 `package.json`）。

## 已知风险

- `verify_assets.py` 的 HEAD 对比在用户提交本任务改动后仍可通过（三处 1.3
  预期变更被显式白名单），但若提交前有其他模板改动混入会 fail closed。
- `1.2-to-1.3.json` 的 `remove` 只退出收据；下游磁盘上的旧
  `.opencode/package.json` 与 git 索引需使用者按文档自行处理。
- 上游 Trellis 仍为 `0.6.10`；升级上游属于独立通道，不在本任务范围。