# 优化 Trellis Channel 上下文加载

## Workflow Settings

- Review level: standard

## Goal

优化下游项目的 Trellis Channel 上下文与等待效率：system prompt 只承载稳定的 Channel 协议、Agent 角色、工作边界和上下文读取契约；当前任务的 PRD、设计、实施计划及 Spec/Research 正文由 worker 启动后从共享工作区主动读取。Codex 主会话进入同步等待后，以五分钟读取窗口复用唯一 wait session，避免短周期空轮询反复触发完整上下文模型请求。

该调整应降低重复上下文和启动参数体积，同时保留 fail-closed 的“必读上下文”门禁，避免通过缩短提示词换来漏读、读取陈旧内容或静默降级。

## Confirmed Facts

- Channel worker 与主会话共享同一工作区，能够在启动后读取活动任务及其 manifest 引用的文件。
- 当前模板的标准实施/审查示例通过 `--file` 和 `--jsonl` 把任务文档与 Spec 全文拼入 worker system prompt。
- 模板内 Implement Agent 和 Check Agent 已要求 worker 根据活动任务路径读取 `implement.jsonl` / `check.jsonl`、`prd.md`、`design.md` 和 `implement.md`，因此当前同时存在全文 push 与 Agent pull 两套路径。
- `implement.jsonl` 和 `check.jsonl` 是 Spec/Research 清单，不替代任务文档；现有规划门禁要求子代理模式在启动实施前完成有效清单配置。
- 全文注入保存的是 spawn 时快照；worker 启动后从磁盘读取可以获得执行时的当前内容。
- 现有 Codex 等待规则只把单次 `write_stdin` 窗口描述为“当前上界约 300 秒”，没有要求正常路径实际使用 `yield_time_ms=300000`；现有契约测试也只验证复用同一 `session_id`，因此 `30000` 等短窗口仍会被视为合规。
- 已分析的真实会话中，30 秒窗口在约 39 分钟等待内触发 44 次主模型请求并累计约 760 万 token；空等时间本身不计 token，消耗来自每次 `write_stdin` 返回后重新调用主模型并重复携带大体量上下文。
- 本任务面向 `templates/embedded-c-overlay/` 发布给下游项目的工作流。根目录自用 Trellis 和全局安装的 `@mindfoldhq/trellis` 只作为现状证据，不是本任务的功能修改目标。

## Requirements

- 下游模板的标准 Implement/Check Channel 派发必须采用混合上下文模型：
  - system prompt 保留 Channel 协议、Agent 角色、禁止操作、安全边界、上下文读取顺序和完成/失败报告契约；
  - 任务 PRD、设计、实施计划、Spec 和 Research 正文不再作为标准任务派发的 system prompt 内容；
  - 首次任务 brief 传递活动任务路径、对应 manifest 名称、本轮目标、范围和验证要求，不复制上述文件正文。
- Implement worker 必须读取活动任务的 `implement.jsonl`、其中每个有效 Spec/Research 文件、`prd.md`、存在时的 `design.md` 和 `implement.md`，完成上下文预检后才可修改交付文件。
- Check worker 必须读取活动任务的 `check.jsonl`、其中每个有效 Spec/Research 文件、`prd.md`、存在时的 `design.md` 和 `implement.md`，完成上下文预检后才可开始审查或自修复。
- 上下文预检必须验证活动任务路径和 manifest 引用处于允许的工作区信任边界内，并确认所有当前阶段必需文件存在且可读取；不得跳过无效条目后继续工作。
- 上下文缺失、不可读、越过信任边界、manifest 格式无效或必读文件加载不完整时，worker 必须在任何交付文件写入前停止，并通过 Channel 报告阻塞原因；不得回退到未加载完整上下文的实施或审查。
- worker 必须在开始实施或审查前读取磁盘中的当前任务上下文，不得依赖 spawn 时生成的任务正文快照。
- 正常加载成功时不发送单独的文件读取回执，也不记录文件列表、内容哈希或其他内容指纹；读取要求属于 worker 的执行前置契约，不包装成无法独立验证的审计证据。
- `implement.jsonl` / `check.jsonl` 的规划期配置、验证和 readiness gate 必须保留；本任务只改变 Channel worker 获取正文的时机和方式，不削弱 manifest 的选材职责。
- `--file` / `--jsonl` 作为 Trellis Channel 通用显式注入能力不在本任务中删除。模板应说明它们适用于 worker 无法访问源文件、需要固定不可变快照或其他明确要求全文注入的场景，而不是共享工作区任务的默认路径。
- Codex 主会话通过终端 session 同步等待 Channel worker 时，首次 `exec_command` 仍使用短 `yield_time_ms` 取得即时终态或仍在运行的 `session_id`；一旦取得 `session_id`，正常等待路径后续每次 `write_stdin` 必须固定使用 `yield_time_ms=300000` 并复用同一 ID，直到 wait 进程完成、失败、达到 Channel CLI 总超时或被用户新指令中断。
- `300000` 是 Codex 工具单次读取窗口，不是 worker 或 `trellis channel wait --timeout` 的总运行上限。不得因为五分钟窗口结束但 wait 进程仍在运行，就创建新的 channel、worker 或 wait 进程。
- `30000` 等短周期 `write_stdin` 只允许用于有明确原因的诊断或交互场景，并且必须在当轮说明原因；不得作为正常实施或审查等待路径的默认值，也不得以发送周期性“仍在运行”状态为由缩短窗口。
- 模板中的 Channel Skill、Implement/Check Agent、Claude/Codex 相关派发说明和契约测试必须对混合加载行为保持一致，不能仍有标准示例无条件全文注入任务上下文。
- 所有功能实现必须限定在 `templates/embedded-c-overlay/`。不得因本任务修改根目录 `.trellis/`、`.agents/skills/`、`.claude/`、`.codex/` 或全局 npm Trellis CLI 的运行逻辑。
- 本子任务不更新 `VERSION`、历史 canonical 对象、版本 manifest、结构迁移链、README 或接入指南；这些内容由父任务固定最后一项 `09-10-readme-integration-guide-upgrade-patch` 在全部 1.2 功能子任务完成后统一处理。

## Acceptance Criteria

- [ ] 下游模板的标准 Implement Channel 派发不再通过 `--file` / `--jsonl` 将任务与 Spec/Research 正文拼入 system prompt，而是通过 brief 提供活动任务路径和 `implement.jsonl` 定位信息。
- [ ] 下游模板的标准 Check Channel 派发采用相同边界，并使用 `check.jsonl` 定位审查上下文。
- [ ] Implement/Check worker 在第一次交付文件写入、审查或自修复前，能够按各自规定顺序读取全部必需任务文档和 manifest 有效条目。
- [ ] 任一必读文件缺失、不可读、路径越界、manifest 无效或加载不完整时，worker 在修改交付文件前报告阻塞并结束失败流程。
- [ ] 正常上下文加载成功时不产生单独的 Channel 回执或文件列表；失败信息仅通过现有 `error` 终态报告具体路径和原因。
- [ ] `implement.jsonl` / `check.jsonl` 仍是必需的 Spec/Research 清单，现有规划门禁不会因取消默认全文注入而被绕过或降级。
- [ ] Channel 的稳定协议、Agent 角色、安全边界、禁止提交规则、执行/审查职责和终止报告契约仍由 system prompt 提供。
- [ ] `--file` / `--jsonl` 通用能力仍被保留，并清楚区分显式快照注入场景与共享工作区的默认主动读取场景。
- [ ] Codex 主会话取得 Channel wait 的 `session_id` 后，正常同步等待示例和规则明确要求复用同一 ID，并将每次 `write_stdin` 的 `yield_time_ms` 固定为 `300000`。
- [ ] 模板契约测试断言正常等待路径包含确切值 `yield_time_ms=300000`，并能够阻止 `30000` 等短轮询重新成为默认流程。
- [ ] 五分钟读取窗口结束但 wait 仍在运行时，主会话只复用原 `session_id`；`done/error`、Channel CLI 总超时和用户中断边界保持明确，且不会把单次读取窗口误当成 worker 总超时。
- [ ] 模板内所有标准 Channel 派发示例和 Agent 说明对混合加载契约保持一致，不再同时要求全文 push 和重复 pull。
- [ ] 功能改动仅位于 `templates/embedded-c-overlay/`；根目录自用 Trellis 与全局 npm 安装没有因本任务发生功能性修改。
- [ ] 模板测试覆盖标准派发参数、必读文件集合、失败前置门禁、成功路径无单独读取回执和显式全文注入保留场景。
- [ ] 项目规定的 Python 单测、Python 语法检查和 `git diff --check` 通过；构建、部署和硬件验证报告为 `not applicable` 并说明本仓库不存在对应目标。

## Out Of Scope

- 在用户批准最新规划摘要前启动任务实施或派发实施/审查 Agent。
- 修改或发布 `@mindfoldhq/trellis` CLI，包括改变 Claude adapter 的 `--append-system-prompt` 参数传递机制或直接修复其 Windows `ENAMETOOLONG` 行为。
- 完全移除 Channel 的 `--file` / `--jsonl` 参数或禁止用户显式创建上下文快照。
- 改变 `implement.jsonl` / `check.jsonl` 的 Spec/Research 定位、规划门禁或任务生命周期。
- 修改 Channel event store、worker inbox、provider adapter、模型选择或 worker 守护进程生命周期。
- 为实现五分钟读取窗口而修改 Codex 工具本身；本任务只约束下游模板中的主会话编排规则、示例和契约测试。
- 提前更新 TrellisForge 版本号、升级资产、README 或接入指南。

## Risks And Deferred Items

- 本任务的主动读取和失败门禁仍由 Agent 指令约束，不能从机制上证明模型执行了读取或正确理解了全部语义；若未来需要强证明，应另行设计由确定性加载器或 provider adapter 执行的机器校验，而不是恢复 worker 自报回执。
- 通用手工派发仍可能显式注入超大正文；本任务优化模板默认工作流，不承诺修复所有自定义命令的操作系统参数上限。
- 固定五分钟窗口会降低主会话获知终态的最坏响应及时性；worker 若在窗口开始后立即完成，工具仍应在进程退出时提前返回，因此该取舍主要影响无终态时的交互中断响应，而不应强制等待满五分钟。

## Planning Convergence

- Status: ready
- Blocking user decisions: 0
- Blocking technical decisions: 0
- Final summary ready: yes
