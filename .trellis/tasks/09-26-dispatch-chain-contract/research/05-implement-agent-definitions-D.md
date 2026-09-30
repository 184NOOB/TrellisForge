# Research: D — 三平台 trellis-implement 代理定义（条目 4）

- **Query**: 三份代理定义相关章节行号与文本要点；mirror-parity 测试；Codex TOML 结构约束
- **Scope**: internal
- **Date**: 2026-09-26

路径相对 `templates/embedded-c-overlay/`。注意：除三平台文件外，还有第 4 份同族文本
`.trellis/agents/implement.md`（channel runtime worker 卡），它被多个测试与三平台文件并列锁定，改 D 时不可遗漏。

## 1. 各文件章节行号与要点

### 1.1 `.claude/agents/trellis-implement.md`（共 207 行）

| 章节 | 行号 | 要点 |
|---|---|---|
| frontmatter | 1-6 | `name/description/tools: Read, Write, Edit, Bash, Glob, Grep` |
| Recursion Guard | 11-17 | 不得再 spawn implement/check |
| Trellis Context Loading Protocol | 19-24 | marker 有/无两分支 |
| Context | 26-37 | 读序 |
| **Execution Plan Protocol (mandatory)** | **39-107** | 44-52 live plan 布局与两级验证；53-64 Round 1 建计划；**65-71 `**Executing:** per phase: plan.py start <id> → batch read/edit/check → record → done`**；72-76 final report phase；77-87 Small patch 硬规则；88-95 Same-task sequel；96-98 status/崩溃恢复；99-102 Never hand-edit + block/revise；103-104 审计损坏；106-107 所有命令带 `--task` |
| **Mandatory execution batches** | **109-125** | 1 Discover in batches；2 Edit by phase；3 Validate by phase；**4 Stop on completion（122-125 行：“once scope, acceptance evidence, required verification, and the report are complete, stop.”）** |
| Core Responsibilities | 127-133 | — |
| Forbidden Operations | 135-141 | git commit/push/merge |
| Workflow | 145-174 | — |
| **Report Format** | **178-198** | `## Implementation Complete` / `### Files Modified` / `### Implementation Summary` / `### Verification Results`（4 行 pass|fail|not run|not applicable） |

### 1.2 `.opencode/agents/trellis-implement.md`（共 220 行）

| 章节 | 行号 | 要点 |
|---|---|---|
| frontmatter | 1-13 | `mode: subagent`、`permission: task: deny`（被平台合同测试锁定，见 §2） |
| Recursion Guard | 18-24 | 同构 |
| Context Loading Protocol | 26-31 | 含 injection blocked 分支 |
| Session Identity | 33-35 | `TRELLIS_CONTEXT_ID` |
| **Execution Plan Protocol (mandatory)** | **50-120** | 55-63 布局；64-75 Round 1；**76-82 Executing（per phase 循环）**；83-87 final report phase；88-98 Small patch；99-106 sequel；107-111 status/崩溃恢复（“Plugin context is a carrier, not a gate”）；112-115 Never hand-edit；116-117 审计损坏；119-120 `--task` |
| **Mandatory execution batches** | **122-138** | 第 4 条 **Stop on completion 在 135-138 行** |
| Forbidden Operations | 148-154 | — |
| **Report Format** | **191-211** | 与 Claude 版同构 |

### 1.3 `.codex/agents/trellis-implement.toml`（共 57 行）

| 结构 | 行号 | 要点 |
|---|---|---|
| 顶层键 | 1-5 | `name`、`description`、`sandbox_mode = "workspace-write"`、注释掉的 model 两行 |
| **prompt 载体** | **7-57** | 全部正文放在 **`developer_instructions` 键**，值为 **TOML 三引号多行基本字符串 `"""..."""`**（7 行开始、57 行闭合） |
| Recursion guard | 10-14 | 含 Git 禁令 |
| Context Loading Protocol | 20-25 | 含 `Full hook output saved to:` 截断分支 |
| **Execution Plan Protocol (mandatory)** | **27-35** | 28 布局；29 Round 1；**30 Executing（单行长句：per phase start→record→done + fail 永久 + terminal report phase + 崩溃恢复）**；31 Small patch；32 sequel；33 Never hand-edit + block/revise；34 审计损坏；35 `--task` |
| Rules + **Mandatory execution batches** | 37-51 | 39-43 四条批次规则（**第 4 条 Stop on completion 在 43 行**）；**51 行独立停止句 “Stop when the declared scope, acceptance evidence, verification, and report are complete unless new evidence expands the scope.”** |
| **报告段（无 Report Format 标题）** | 53-56 | “Before finishing, summarize: Files changed / Tests-checks run / Remaining risks or follow-ups” |

**TOML 转义/长度约束**：三引号基本字符串内 `\` 是转义符（现有文本未使用反斜杠）；`"""` 序列不能出现在正文；
多行正文换行原样保留。现有 43 行含中文全角引号 `“逐项”`（UTF-8 直接内嵌，无需转义）。文件内无长度限制声明；
测试仅以纯文本 normalized assertIn 消费它（无 tomllib 解析，tests 目录 grep `tomllib` 0 命中）。

### 1.4 第 4 份同族文本：`.trellis/agents/implement.md`（channel worker 卡，共 196 行）

| 章节 | 行号 | 要点 |
|---|---|---|
| Mandatory context precheck | 21-54 | fail-closed；45-50 行“stop before the first delivery write … Send an `error` terminal report” |
| **Execution Plan Protocol (mandatory)** | **56-112** | 66-78 Round 1；**79-87 Executing（编号第 2 条）**；88-98 Small patch；99-106 sequel；107-110 Never hand-edit；111-112 审计损坏 |
| **Execution batches (mandatory)** | **121-138** | 第 4 条 **Stop on completion 134-138 行** |
| Forbidden Operations | 140-146 | 含 Trellis lifecycle 写禁令 |
| **Channel Termination Contract** | **148-159** | 155-157 正常完成报告并结束 turn；**158-159 “无法继续:…以失败状态结束 turn,使 supervisor 记录 `error`;不得静默挂起或未完成就结束。”——全模板唯一一处“不得静默”义务，但只覆盖 channel worker，不覆盖三平台原生派发** |
| Report Format | 176-196 | 同构 + `### Open Questions` |

## 2. mirror-parity / 文本锁定测试

**不存在要求三份（或四份）implement 代理定义逐字节相等的测试。** 现有约束是“共享短语集合”式：

| 测试:行号 | 比对什么 | 形态 |
|---|---|---|
| `test_small_patch_and_sequel_contract.py:46-51` | `IMPLEMENT_AGENTS` 四文件清单：`.trellis/agents/implement.md`、`.claude/agents/trellis-implement.md`、`.codex/agents/trellis-implement.toml`、`.opencode/agents/trellis-implement.md` | — |
| `test_small_patch_and_sequel_contract.py:147-158` | 四文件（normalized 空白后）各自 assertIn：`Small patch (hard rule, bypasses plan.py)`、`never \`revise\``、`sequel --reason`、`Blocking`、`default to`、`frozen read-only history`、`Same-task sequel`、`touch no execution-plan file at all` | assertIn，非逐字节 |
| `test_subagent_prompt_contract.py:286-293` | `.trellis/agents/implement.md` assertIn：`Execution batches (mandatory)`、`report granularity`、``call `grep` once per item``、`Stop on completion` | assertIn |
| `test_opencode_platform_contract.py:190-210` | `.opencode/agents/trellis-implement.md`：frontmatter 含 `mode: subagent`、`task: deny`（193、201-202 行）；正文 assertIn `Execution Plan Protocol`（207）、`plan.py`（208）、`Mandatory execution batches`（209）、`git commit`（210） | assertIn |
| `test_trellis_channel_contract.py:259-263` | worker 卡 assertIn `before the first delivery write`、`error` | assertIn |
| `test_review_fix_ownership_contract.py`（§3.5 见 04 文件） | MANAGED_FILES 不含 implement 代理定义（只含 check 侧），但 FORBIDDEN 短语清单对 hook/plugin/workflow 生效 | — |

**D 项含义**：给三份平台定义（+worker 卡，若同步）追加“不得单 phase 返回”、扩写 Stop on completion 的
completion 定义、Report Format 增加 `Plan phases advanced` / `Remaining runnable` 两行，均为**纯新增**，
不触碰上表任何 assertIn 短语；但若新增文字命中 `test_review_fix_ownership_contract.py:95-106` 的 FORBIDDEN
短语（仅当把 hook/plugin/workflow 也纳入同批修改时相关）需回避。注意 Codex TOML 的报告段没有
`## Report Format` 标题（53-56 行是 “Before finishing, summarize” 三行清单），新增两行报告字段需按该文件形态落位。

## 3. 三份文本的对齐机制现状

- Claude 与 OpenCode 两份 md 的 Execution Plan Protocol / batches / Report Format 措辞高度同构但**非逐字**
  （如 OpenCode 版 107-111 行多出 “Plugin context is a carrier, not a gate”；Claude 版 41-42 行多出
  “not by the native TodoWrite/Task tools”）。
- Codex TOML 是压缩单行体（28-35 行），信息与 md 版对齐但句式不同。
- 因此新增 D 项句子时应按“三份（或四份）各自落位、共享关键短语”的既有模式，并建议沿用
  `test_small_patch_and_sequel_contract.py` 的 IMPLEMENT_AGENTS 循环模式为新短语建 parity 断言（该模式已被
  两处测试复用，属仓库既有惯例）。
