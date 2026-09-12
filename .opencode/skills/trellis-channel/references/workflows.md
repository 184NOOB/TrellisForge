# Workflows

Use these patterns by intent. Prefer durable channels for multi-round work and
`channel run` for one-shot questions.

## Pattern A: Multi-round Brainstorm

Use when the user says "和 codex/claude 讨论一下", "brainstorm", or "拉一个 agent
进来一起看".

```bash
trellis channel create brainstorm-storage-layer --by main \
  --task .trellis/tasks/05-XX-storage-adapter

trellis channel spawn brainstorm-storage-layer \
  --agent architect --provider codex \
  --file .trellis/tasks/05-XX-storage-adapter/prd.md \
  --file .trellis/tasks/05-XX-storage-adapter/design.md \
  --as cx-arch --timeout 30m

trellis channel send brainstorm-storage-layer \
  --as main --to cx-arch --text-file /tmp/brainstorm-r1.md

trellis channel wait brainstorm-storage-layer \
  --as main --kind done --from cx-arch --timeout 10m
```

Do not stop after one answer. Read the answer, identify vague areas, send a
new probe, and repeat until the result is executable.

Minimum round structure:

1. Direction split: should this live in an existing mechanism or a new one?
2. MVP boundary: v1, v2, and what would force v2 back into v1.
3. Data contract: events, schema, metadata, state source of truth, compatibility.
4. CLI / UX contract: command names, flags, errors, defaults, ambiguity.
5. Cross-layer risk and tests: shared helpers, drift points, release-blocking tests.

Optional rounds:

- Operations: logs, debugging, stuck workers, kill/restart, recovery.
- Migration/release: breaking status, manifest, changelog, docs-site.
- Opposition review: ask the peer agent to argue against the current plan.

Every probe should request concrete file paths, commands, schema, rejected
alternatives, and release-blocking issues. Reject hedging when a decision is
needed.

## Pattern B: Implement / Check Agent

Use when the user asks to dispatch implementation or review work. One worker
work unit creates one purpose-specific channel, runs exactly one `spawn`, and
blocks on exactly one `wait` for that worker's terminal event (`done` /
`error`). `progress` is process information, never a completion signal — do
not watch or poll it in the normal path. CLI `--timeout` is set from the
worker's expected duration; the 30 分钟 values below are adjustable examples,
not fixed limits.

### Standard Implement Dispatch

```powershell
$TASK = ".trellis/tasks/05-12-foo"
trellis channel create impl-foo --task $TASK --by main
trellis channel spawn impl-foo --agent implement --provider codex --as impl-cx `
  --cwd (Get-Location) --timeout 30m
@"
Active task: $TASK
Context manifest: implement.jsonl
本轮角色: Implement worker。目标: <目标>。范围: <受影响文件>。明确非目标: <非目标>。
验证命令: <任务或工程已经规定的命令>。
先完成上下文预检: 读取 implement.jsonl 全部有效条目与 prd.md、design.md、implement.md,
失败则报告 error 并停止,成功后才可写入交付文件。
"@ | trellis channel send impl-foo --as main --to impl-cx --stdin
trellis channel wait impl-foo --as main --from impl-cx --kind done,error --timeout 30m
```

Task PRD, design, execution-plan, Spec, and research bodies are **not**
injected at spawn time. The task and the worker share the workspace, so the
`spawn` stays lean and the brief locates the context. The worker resolves the
active task path, batch-reads `implement.jsonl` plus the required task docs
from the shared workspace, and only then modifies delivery files. Use
`--file` / `--jsonl` only when the worker cannot access the source files or
an immutable spawn-time snapshot is required. See `workers.md` "Context
Injection".

### Standard Check Dispatch

```powershell
$TASK = ".trellis/tasks/05-12-foo"
trellis channel create check-foo --task $TASK --by main
trellis channel spawn check-foo --agent check --provider claude --as check-claude `
  --cwd (Get-Location) --timeout 30m
@"
Active task: $TASK
Context manifest: check.jsonl
本轮角色: Check worker。目标: 按 <profile> 审查 <范围>。明确非目标: <非目标>。
已运行的验证与验收项: <任务或工程已经规定的命令/验收>。
先完成上下文预检: 读取 check.jsonl 全部有效条目与 prd.md、design.md、implement.md,
失败则报告 error 并停止,成功后才可查看 diff、审查或自修复。
"@ | trellis channel send check-foo --as main --to check-claude --stdin
trellis channel wait check-foo --as main --from check-claude --kind done,error --timeout 30m
```

The check worker pulls `check.jsonl` and the required task docs from the
shared workspace before it starts reviewing; same mix as the implement flow
above.

The implement and check flows differ only in `--agent`, provider / `--as`
choice, and the brief content; the lifecycle (one spawn, one wait) is
identical. After `wait` exits on `done` / `error`, read only the final result
needed to decide the next step (e.g. `messages --from <worker> --last 1
--raw`). Do not start a second `wait`, a duplicate channel, or progress
inspection while the first wait is still running.

## Pattern C: Parallel Reviewers

Use one channel and distinct worker names. Task review workers are
shared-workspace work units: no full-text `--file` / `--jsonl` injection, the
brief locates the active task and manifest.

```bash
TASK=.trellis/tasks/05-12-foo
trellis channel create cr-feature --by main --ephemeral

trellis channel spawn cr-feature --agent check \
  --cwd "$PWD" --timeout 15m

trellis channel spawn cr-feature --agent check --provider codex --as check-cx \
  --cwd "$PWD" --timeout 15m

cat > /tmp/cr-brief.md <<EOF
Active task: $TASK
Context manifest: check.jsonl
目标: 按 <profile> 审查 <范围>。明确非目标: <非目标>。
已运行的验证与验收项: <任务或工程已经规定的命令/验收>。
先完成上下文预检: 读取 check.jsonl 全部有效条目与 prd.md、design.md、implement.md,
失败则报告 error 并停止,成功后才可查看 diff、审查或自修复。
EOF

trellis channel send cr-feature --as main --to check --text-file /tmp/cr-brief.md
trellis channel send cr-feature --as main --to check-cx --text-file /tmp/cr-brief.md
trellis channel wait cr-feature --as main --kind done --from check,check-cx --all --timeout 15m
```

`--all` means every listed worker must emit a matching event.

## Pattern D: One-shot Worker

```bash
trellis channel run --provider codex --message "say hi in 3 words" --timeout 1m
trellis channel run --agent plan --message-file /tmp/plan-question.md --timeout 10m
```

On success, `run` removes the ephemeral channel. On error/timeout/killed, it
keeps the channel and prints the path for inspection.

## Pattern E: Forum Channel

Use for issue forums, topic-style feedback, release todos, agent findings, and
internal changelogs. Read `forum.md` for the full model.

## Pattern F: Take Over Existing Thread

If the user gives a forum/thread name, restore context yourself:

```bash
trellis channel forum <board> --scope global
trellis channel thread <board> <thread> --scope global --raw
trellis channel context list <board> --scope global --thread <thread>
trellis channel messages <board> --scope global --raw --thread <thread>
```

Output a constraint summary, not a transcript dump:

- user-level problem
- context files that affect this repo
- current-version versus future-version requirements
- whether current code/design satisfies it
- next action or comment to append
