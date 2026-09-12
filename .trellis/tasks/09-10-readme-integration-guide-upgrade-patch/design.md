# TrellisForge 1.2 发布收尾技术设计

## Architecture And Boundaries

本任务沿用现有电梯模型，不创建第二套升级机制：

```text
VERSION=1.2
  -> versions/1.2/manifest.json + canonical objects
  -> install: live template == 1.2 manifest -> 写 1.2 receipt
  -> update: source manifest + 相邻 structural steps + 1.2 manifest
             -> 逐路径三方合并/新增分类 -> 预检
             -> 备份 -> 原子写入 -> 写 1.2 receipt
```

发布模板正文只来自 `templates/embedded-c-overlay/`。`history/`、`migrations/`、工具、测试和根文档属于 Forge 发布交付物，不安装到下游；`.trellis/tasks/` 仅保存本任务的生成/验证辅助脚本和规划证据。

## Release Asset Design

### Immutable history

- 以现有 1.0/1.1 manifest 和对象库为历史事实，不从当前模板重新生成旧版本。
- 任务内 `gen_migration.py` 先验证历史 manifest 引用与对象哈希，再从 live 模板生成 1.2 manifest；对象按 LF 规范化内容 SHA-256 去重，只追加缺失对象。
- `AGENTS.md.trellisforge-template` 继续由 `AGENTS.md.template` 产生，但 1.2 manifest 引用当前模板内容的新 canonical；旧 manifest 的引用不变。
- `verify_assets.py` 对三代 manifest、对象引用、无孤儿对象、旧资产字节不变、1.2/live 一致性、结构链连续性和版本事实执行确定性校验。

### Adjacent structural chain

- 保留 `1.0-to-1.1.json` 的 `bootstrap-schema-1`。
- 新增 `1.1-to-1.2.json`，使用 `receipt_transition: preserve-schema-1`、`actions: []`。
- `Get-OverlayStructuralChain` 根据版本 manifest 集合确定从来源到目标的有序版本区间，逐一加载相邻步骤并校验 schema、from/to、动作白名单和收据转换白名单。
- 返回结果保留完整 `steps`，并提供按顺序聚合的结构动作供 updater 检查来源独有路径。缺 manifest、版本倒序、重复/断裂步骤或非法动作/转换均 `unsupported`。
- 这里的“步骤”仅指结构迁移：1.0 -> 1.2 依次加载 `1.0-to-1.1` 与 `1.1-to-1.2`，1.1 -> 1.2 只加载 `1.1-to-1.2`。文件正文不经过 1.1，也不会创建 `1.0-to-1.2` 直连快照、正文或结构文件。

## Installer And Updater Contracts

- 安装器继续从 `VERSION` 动态取得目标版本；只把注释、诊断和测试中的 1.1 硬编码改为当前版本语义，不扩大写入清单。
- updater 保留收据优先的来源解析。无收据仍只允许 1.0，且要求显式项目参数；有收据允许存在历史 manifest 且能形成完整相邻链的旧版本。
- 逐文件正文合并与结构链相互独立，且每个文件只合并一次：直接比较来源 manifest 与目标 1.2 manifest，使用“来源 canonical + 下游当前文件 + 1.2 模板”。canonical 不变则不改工作树，canonical 改变则执行三方合并，目标新增路径按 `add/already-current/conflict` 分类；1.0 来源不读取或落盘 1.1 正文。
- 所有用户可见建议、报告和结束提示使用 `$from` / `$forgeVersion`，不再硬编码“1.0 基线”“1.1 模板”。
- 来源有而目标无的路径必须由聚合结构动作明确覆盖；修复当前检查中脚本块 `$_` 变量遮蔽，避免未来删除/重命名路径被误判为已覆盖。
- 预检报告仍只写 Git 元数据目录；仅在无冲突且显式 `-Apply` 时进入完整备份、原子写入和收据更新事务。

## Compatibility Matrix

| 下游状态 | 来源识别 | 文件正文 | 结构迁移 | 预期结果 |
| --- | --- | --- | --- | --- |
| 未安装 | 无 | 直接安装 1.2 | 无 | 安装完整 1.2，写 schema 1 收据 |
| 1.0，无收据 | 默认/显式 1.0 + 显式项目参数 | 1.0 canonical + 当前文件 + 1.2 模板，只合并一次 | 依次加载 `1.0-to-1.1`、`1.1-to-1.2` | 预检后可直达 1.2，不读取或落盘 1.1 正文 |
| 1.1，有效收据 | 收据 | 1.1 canonical + 当前文件 + 1.2 模板，只合并一次 | 只加载 `1.1-to-1.2` | 保留可合并定制并升级到 1.2 |
| 1.2，有效收据 | 收据 | 无 | 无 | `already-current` |
| 未知/损坏来源 | 收据或参数 | 不执行 | 无法形成合法结构链 | fail closed |

## Documentation Design

- README 保持短入口定位：版本矩阵、最短命令、1.2 能力摘要、资产目录、安全边界与指南链接。
- `docs/接入指南.md` 承担完整操作手册：首次接入、两类来源升级、三平台准备/验证、冲突材料、恢复、幂等与上游 Trellis 独立更新。
- `TEMPLATE-CONTENTS.md` 作为维护者清单，更新 1.2 收据/manifest/结构链并保留 OpenCode 文件树说明。
- `.trellis/spec/main/tooling/overlay-upgrade.md` 从“当前 1.1/唯一一步”改为版本无关合同，并记录相邻步骤组合规则。

## Test Design

- 更新 `tests/test_overlay_tools.py` 的版本常量、断言和夹具，新增 1.1 下游夹具及 1.1->1.2、1.0->1.2 两条升级路径；分别断言正文只从各自来源 canonical 直接合并到 1.2，并断言只有结构迁移按相邻步骤加载。
- 1.1 夹具由不可变 1.1 manifest/canonical 对象渲染，并生成真实 schema 1 receipt；不能使用当前安装器伪造旧版。
- 对新增 OpenCode 文件覆盖缺失新增、已存在一致、已存在冲突；对已有受管文件覆盖无定制、非重叠定制、冲突和 LF/CRLF。
- 继续覆盖 live/manifest 漂移、对象缺失/哈希错误、结构链断裂/非法动作/非法转换、参数冲突、预检零写入、备份与写入失败回滚。
- 资产校验另行证明 1.0/1.1 不变、1.2 完整、对象去重及无孤儿。

## Risks And Rollback Points

- 最大风险是把旧 manifest 或 canonical 对象误写为当前模板。先保存旧资产哈希清单，生成后逐字节复核；任何变化立即停止，不继续工具修改。
- 第二风险是链组合只在 1.0->1.2 通过、却破坏 1.1->1.2 或未来断链拒绝。用来源矩阵和损坏夹具分别锁定。
- OpenCode 新增文件数量多，安装/升级清单遗漏会导致 live/manifest 漂移；manifest 生成与测试均从同一个模板枚举规则取得文件集。
- 文档最后更新，以最终 CLI 输出和测试事实为准。若工具行为变化，先返回设计与测试，再同步文档。
- 所有回滚均按文件组进行；不重写 Git 历史，不删除历史 manifest/对象，不运行未经授权的提交或发布操作。
