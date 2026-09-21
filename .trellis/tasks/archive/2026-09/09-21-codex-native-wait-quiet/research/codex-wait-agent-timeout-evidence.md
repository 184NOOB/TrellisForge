# Codex `wait_agent` 等待窗口实测证据（只读取证）

取证时间：2026-09-22。证据源（仓库外，只读）：
`C:\Users\10671\.codex\sessions\2026\09\21\rollout-2026-09-21T20-21-50-01a0c3ea-56f0-7ce3-9974-482a8f5526e2.jsonl`
（6,761,895 字节；Smart Community 目标仓库，使用 TrellisForge 1.2 模板）。

## 1. 用途

`prd.md` R1 与 `design.md` 3.3 要求"单次等待窗口取该工具允许的最大值（分钟级）"、
禁用 30000 级短窗口。该数值锚点此前只有"观测到连续 30000"这一条反面证据，
无法排除"30000 就是工具上限"。本文件用同一份 JSONL 正面验证分钟级窗口可行。

## 2. 调用分布（正则统计）

`wait_agent`（namespace `collaboration`）的 `timeout_ms` 实参分布：

| `timeout_ms` | 次数 |
|---|---|
| 1280 | 2 |
| 10000 | 1 |
| 30000 | 8 |
| 60000 | 2 |
| 120000 | 1 |

其他统计：`wait_agent` 字符串出现 31 次（含输出与引用），`spawn_agent` 出现 27 次；
`yield_time_ms` 分布为 1000×6、10000×52（属 `exec_command` 终端读取窗口，
与 `wait_agent` 的 `timeout_ms` 不是同一上限）。
带 `timeout_ms` 实参的工具调用只有 `wait_agent`（14 次）。

## 3. 分钟级窗口被工具接受且等满（关键结论）

- `call_qeXS05WADT6kh4N6J8JIoIdA`：`wait_agent {"timeout_ms":120000}`，
  调用 `create_time = 1790006910.587692`，对应 `function_call_output`
  `create_time = 1790007032.7737355` → 实际等待约 **122 秒**，
  输出 `{"message":"Wait timed out.","timed_out":true}`。
- `call_1keQhJgqKL4yOdKbmTZ9Qv2P`：`wait_agent {"timeout_ms":60000}` →
  输出同为 `{"message":"Wait timed out.","timed_out":true}`。
- `call_s4MeSmNaMVO4YbGQF0hECMN8`：`wait_agent {"timeout_ms":60000}` →
  输出同为 `{"message":"Wait timed out.","timed_out":true}`。

结论：

1. `timeout_ms = 120000`（2 分钟）被 Codex 工具接受并等满窗口，未被截断或报错。
   → "分钟级窗口"是可满足的合同锚点，30000 是模型自选而非工具上限。
2. 窗口到期而 agent 仍在运行时，返回体是 `{"message":"Wait timed out.","timed_out":true}`，
   语义是"仍在运行"，不是失败；正确动作是复用同一 agent/thread 继续等待。
3. 未观测到 >120000 的调用，因此 300000 之类更大值属**未验证**；
   合同锚点应写成"≥120000（实测可行）"，不得把未验证值写成事实。

## 4. 无关噪声（已排除）

`{"timeout_ms":120000}` 还出现在一次 `name":"wait"`（终端 cell 等待工具）调用
`call_EFtmjAdJDnFGTCgp46MaUc4n` 上，其输出为
`failed to parse function arguments: missing field \`cell_id\` at line 1 column 21`，
属参数缺失错误，与 `wait_agent` 的窗口上限无关，不作为反面证据。

## 5. 对合同文本的约束

- 允许写：`timeout_ms` 取工具允许的最大值；实测 120000 可行；正常路径按分钟级；
  `{"timed_out":true}` 表示仍在运行，复用同一 agent 继续等待。
- 禁止写：`"timeout_ms":30000` 形式的 JSON 示例；把 300000 或任何未实测值
  写成工具上限；把 `timed_out:true` 描述为失败。
