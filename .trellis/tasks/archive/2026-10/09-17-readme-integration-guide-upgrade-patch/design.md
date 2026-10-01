# TrellisForge 1.3 发布收尾技术设计

## Architecture And Boundaries

本任务沿用现有电梯模型，不创建第二套升级机制：

```text
VERSION=1.3
  -> versions/1.3/manifest.json + canonical objects
  -> install: live template == 1.3 manifest -> 写 1.3 receipt
  -> update: source manifest + 相邻 structural steps + 1.3 manifest
             -> 逐路径三方合并/新增分类 -> 预检
             -> 备份 -> 原子写入 -> 写 1.3 receipt
```

发布模板正文只来自 `templates/embedded-c-overlay/`。根自用 `.trellis/`、`.agents/`、`.claude/`、`.codex/`、`.opencode/` 不因模板已有对应路径而回改。根 `.trellis/scripts/tests/test_opencode_platform_contract.py` 的 `TEMPLATE_ROOT` 解析为仓库根，测的是根 `.opencode/`；删模板 `package.json` 不会让该根测试变红，也不得去改它。

`VERSION`、`history/`、`migrations/`、`tests/test_overlay_tools.py`、`README.md`、`docs/接入指南.md`、`.trellis/spec/main/tooling/overlay-upgrade.md` 属于发布收尾授权范围（`templates-and-docs.md:18`），不是根自用工作流实例。

## Release Asset Design

### Immutable history

- 以现有 1.0/1.1/1.2 manifest 和对象库为历史事实，不从当前模板重新生成旧版本。1.2 仍包含 `.opencode/package.json` 的 canonical 对象。
- `gen_migration.py` 先验证历史哈希，再从 live 模板生成 1.3 manifest。排除名与 1.2 生成器相同：`AGENTS.md.template`、`TEMPLATE-CONTENTS.md`。`package.json` 因已从源树删除而不会进入 1.3。
- 不可变基线 raw SHA-256：
  - `versions/1.0/manifest.json` `ac26b0975422f17068033764a734d35daddf7d640cef1b3e3856190d10c86a92`
  - `versions/1.1/manifest.json` `f0ed1f8fbd332cd2669129126b3899227fa6b207ec597eab68a576c49a354587`
  - `versions/1.2/manifest.json` `6e6c46839f488cccce8e0d4774080c85aecd199d3ad41dddaa721149a95abec1`
  - `structural/1.0-to-1.1.json` `66222336d31259acc9baa3da25d9038c1d0deb4d2ad67b7768363f90e1afa276`
  - `structural/1.1-to-1.2.json` `d2c23fbaf82ad11f1f6d30f3e93828c8b6cc712442625bd897a728b1b3d09829`
- `verify_assets.py` 校验四代 manifest、对象引用、无孤儿、旧资产不变、1.3/live/HEAD 一致、结构链连续。1.3 受管路径预期：1.2 的 151 − 1（`package.json`）+ 7（新测试）+ 1（`.opencode/.gitignore`）= 158。

### Adjacent structural chain

- 保留 `1.0-to-1.1.json` 与 `1.1-to-1.2.json`。
- 新增 `1.2-to-1.3.json`：

```json
{
  "schema_version": 1,
  "from_version": "1.2",
  "to_version": "1.3",
  "receipt_transition": "preserve-schema-1",
  "actions": [
    { "action": "remove", "path": ".opencode/package.json" }
  ]
}
```

- 该 `remove` 满足升级器对来源独有路径的覆盖检查。现有执行器把此类路径标为 `structural-remove` / `already-current`，不写入、不删除磁盘文件（`update-embedded-c-overlay.ps1:191-194`）。本任务不把 `remove` 升级成真实删文件。
- 1.0→1.3 加载三步，1.1→1.3 两步，1.2→1.3 一步。不创建 `1.0-to-1.3` / `1.1-to-1.3`。

## OpenCode Dependency Unofficialization

- 删除 `templates/embedded-c-overlay/.opencode/package.json`。
- 新增 `templates/embedded-c-overlay/.opencode/.gitignore`，内容至少包含 `package.json` 与 `package-lock.json`；可与根自用 `.opencode/.gitignore` 对齐 `node_modules` / `bun.lock`，但不把根文件的 `.gitignore` 自忽略项当作必须交付。
- 安装器不会安装已删除的 `package.json`，因为写入循环只遍历 1.3 manifest。
- 升级 1.2 下游：该路径退出新收据；若磁盘仍有已跟踪文件，文档要求用户自行 `git rm --cached .opencode/package.json`。Forge 工具不代跑 git 索引命令。
- 模板 `test_opencode_platform_contract.py`：`REQUIRED_ROOTS` 去掉 `package.json`，增加 `.opencode/.gitignore`；`test_package_json_declares_plugin_dependency` 改为断言 gitignore 含 `package.json` 与 `package-lock.json`，并断言模板树不存在该文件。根目录同名测试不改。

## Installer And Updater Contracts

- 安装器继续从 `VERSION` 动态取目标版本。
- updater 保留收据优先来源解析。1.2 收据升级必须能组合到含 `remove` 的 `1.2-to-1.3`。
- 1.3 新增路径：7 个测试文件 + `.opencode/.gitignore`。`.gitignore` 按 `add/already-current/conflict` 分类。
- 预检只写 Git 元数据目录；仅无冲突且 `-Apply` 时进入备份、原子写入和收据更新。

## Compatibility Matrix

| 下游状态 | 来源识别 | 文件正文 | 结构迁移 | 预期结果 |
| --- | --- | --- | --- | --- |
| 未安装 | 无 | 直接安装 1.3 | 无 | 完整 1.3，无官方 `package.json`，有 `.opencode/.gitignore` |
| 1.0，无收据 | 默认/显式 1.0 + 项目参数 | 一步直达 1.3 | 三步相邻链 | 直达 1.3；1.0 本无 `package.json` |
| 1.1，有效收据 | 收据 | 一步直达 1.3 | 两步 | 升级到 1.3；1.1 本无 `package.json` |
| 1.2，有效收据 | 收据 | 一步直达 1.3 | `1.2-to-1.3`（含 remove） | 新测试文件与 gitignore 装入；旧 `package.json` 留盘、退出收据 |
| 1.3，有效收据 | 收据 | 无 | 无 | `already-current` |
| 未知/损坏来源 | 收据或参数 | 不执行 | 无法形成合法链 | fail closed |

## Documentation Design

- README：版本矩阵含 1.2→1.3；OpenCode 节改为本机安装 `@opencode-ai/plugin`，不把 `package.json` 列为交付物。
- 接入指南：首次接入写 `npm install`；升级节写已跟踪文件的 `git rm --cached`；能力表补 R4 八项。
- `TEMPLATE-CONTENTS.md`：`.opencode/` 说明改为 gitignore + 本机依赖，不再写官方 `package.json`。
- `overlay-upgrade.md`：明确 `remove` 覆盖来源独有路径且不删磁盘；验证举例改为四代资产。

## Test Design

- `tests/test_overlay_tools.py`：`TARGET_VERSION=1.3`；新增 `make_12_project`。
- 首次安装断言：无 `.opencode/package.json`，有 `.opencode/.gitignore`，gitignore 含两文件名。
- 1.2→1.3：升级前夹具含 1.2 官方 `package.json`；`-Apply` 后该文件仍在磁盘、不在 1.3 收据；报告对该路径为 `structural-remove` / `already-current`。
- 结构链断言：1.2→1.3 一步且含 `remove`；1.1→1.3 两步；1.0→1.3 三步；无跨版本直连文件。
- live/manifest 一致性改为 1.3；1.2 改为历史自洽，禁止用 live 重写 1.2 对象。
- 模板 OpenCode 合同测试按上文改写。

## Risks And Rollback Points

- 误写历史对象：生成前后逐字节复核基线哈希。
- `remove` 若未写入结构步骤，1.2 升级会因来源独有路径 fail closed。
- 模板测试仍要求 `package.json` 会导致模板套件红。先改测试再删文件，或同批提交。
- 文档若仍指向模板内 `package.json`，会把已删除文件写成交付事实。文档最后写。
- 不重写 Git 历史，不删除历史 canonical，不代提交下游 `git rm --cached`。
