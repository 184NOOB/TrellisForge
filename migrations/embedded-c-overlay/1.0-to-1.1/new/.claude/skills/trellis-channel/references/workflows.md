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
  --file "$TASK/prd.md" --file "$TASK/design.md" --file "$TASK/implement.md" `
  --jsonl "$TASK/implement.jsonl" --cwd (Get-Location) --timeout 30m
"实施 brief：写明验收条件、范围与验证命令。" `
  | trellis channel send impl-foo --as main --to impl-cx --stdin
trellis channel wait impl-foo --as main --from impl-cx --kind done,error --timeout 30m
```

### Standard Check Dispatch

```powershell
$TASK = ".trellis/tasks/05-12-foo"
trellis channel create check-foo --task $TASK --by main
trellis channel spawn check-foo --agent check --provider claude --as check-claude `
  --file "$TASK/prd.md" --file "$TASK/design.md" --file "$TASK/implement.md" `
  --jsonl "$TASK/check.jsonl" --cwd (Get-Location) --timeout 30m
"审查 brief：写明任务 diff 范围、验收项与已运行的验证。" `
  | trellis channel send check-foo --as main --to check-claude --stdin
trellis channel wait check-foo --as main --from check-claude --kind done,error --timeout 30m
```

The implement and check flows differ only in `--agent`, provider / `--as`
choice, and the brief content; the lifecycle (one spawn, one wait) is
identical. After `wait` exits on `done` / `error`, read only the final result
needed to decide the next step (e.g. `messages --from <worker> --last 1
--raw`). Do not start a second `wait`, a duplicate channel, or progress
inspection while the first wait is still running.

## Pattern C: Parallel Reviewers

Use one channel and distinct worker names.

```bash
trellis channel create cr-feature --by main --ephemeral

trellis channel spawn cr-feature --agent check \
  --jsonl "$TASK/check.jsonl" --file "$TASK/prd.md" --file "$TASK/design.md" \
  --timeout 15m

trellis channel spawn cr-feature --agent check --provider codex --as check-cx \
  --jsonl "$TASK/check.jsonl" --file "$TASK/prd.md" --file "$TASK/design.md" \
  --timeout 15m

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
