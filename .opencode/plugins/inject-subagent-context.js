/* global process */
/**
 * Trellis Sub-Agent Context Injection Plugin (OpenCode)
 *
 * OpenCode equivalent of the template `.claude/hooks/inject-subagent-context.py`
 * (PreToolUse). Two responsibilities on `tool.execute.before`:
 *
 * 1. Shell identity bridge — prefix shell tool commands with the current
 *    session's `TRELLIS_CONTEXT_ID` (PowerShell form on native Windows
 *    shells, POSIX export under Git Bash / MSYS) so `task.py` / `plan.py`
 *    hit this window's session pointer. Commands that already set the
 *    variable explicitly are never double-injected.
 *
 * 2. Native Task context injection — for `trellis-research`,
 *    `trellis-implement`, and `trellis-check` dispatches:
 *      - resolve the task fail-closed: exact session pointer -> first valid
 *        `Active task: <path>` line (existing, in-workspace) -> restricted
 *        single-session fallback;
 *      - materialize context in template order: JSONL Spec/Research entries ->
 *        prd.md -> design.md (if present) -> implement.md (if present) ->
 *        current schema-3 execution-plan protocol (implement only), sharing
 *        the `.trellis/config.yaml` context-injection budget;
 *      - normalize the implement dispatch prompt by calling the template's
 *        Python `subagent_prompt_policy.py --json` bridge (single source of
 *        normalization semantics; no JavaScript copy of the regex tables);
 *      - when Implement/Check cannot resolve a task, INJECTION IS BLOCKED and
 *        the child prompt carries an explicit "stop and report" notice —
 *        the plugin never fakes context and never borrows another session's
 *        task.
 *
 * The plugin is a context carrier, not a security gate: task.py and plan.py
 * keep enforcing the gates even when this plugin is disabled.
 *
 * Export shape: exactly one default export (OpenCode 1.2.x calls every
 * module export as a plugin factory).
 */

import { existsSync, readdirSync } from "fs"
import { join, resolve as resolvePath } from "path"
import {
  TrellisContext,
  ContextBudget,
  debugLog,
  materializeArtifact,
  readContextInjectionLimits,
} from "../lib/trellis-context.js"
import {
  injectTrellisContextIntoShell,
  normalizePromptViaPython,
  planProtocolBlock,
  STATIC_EXECUTION_CONTRACT,
} from "../lib/session-utils.js"

const AGENTS_ALL = ["trellis-research", "trellis-implement", "trellis-check"]
const AGENTS_REQUIRE_TASK = ["trellis-implement", "trellis-check"]

const HOOK_MARKER = "<!-- trellis-hook-injected -->"

// ---------------------------------------------------------------------------
// Context materialization (template order + shared budget)
// ---------------------------------------------------------------------------

function materializeTaskArtifacts(ctx, taskRef, limits, budget) {
  const parts = []

  // 1. Agent JSONL entries (Spec/Research manifests)
  const agentJsonl = taskRef.agentKind === "check" ? "check.jsonl" : "implement.jsonl"
  const blocks = ctx.readJsonlWithFiles(join(taskRef.taskDirFull, agentJsonl), limits, budget)
  if (blocks.length > 0) parts.push(ctx.buildContextFromEntries(blocks))

  // 2. Requirements document
  const prdBlock = materializeArtifact(
    ctx.directory, `${taskRef.display}/prd.md`, `${taskRef.display}/prd.md (Requirements)`,
    "Requirements document", limits, budget,
  )
  if (prdBlock) parts.push(prdBlock)

  // 3. Technical design for complex tasks
  const designBlock = materializeArtifact(
    ctx.directory, `${taskRef.display}/design.md`, `${taskRef.display}/design.md (Technical Design)`,
    "Technical design document", limits, budget,
  )
  if (designBlock) parts.push(designBlock)

  // 4. Execution plan for complex tasks
  const implementPlanBlock = materializeArtifact(
    ctx.directory, `${taskRef.display}/implement.md`, `${taskRef.display}/implement.md (Execution Plan)`,
    "Execution plan document", limits, budget,
  )
  if (implementPlanBlock) parts.push(implementPlanBlock)

  return { parts, blocks }
}

/** Implement context: JSONL -> prd -> design -> implement -> plan protocol + state. */
function getImplementContext(ctx, taskRef) {
  const limits = readContextInjectionLimits(ctx.directory)
  const budget = new ContextBudget(limits.max_total_bytes)
  const { parts } = materializeTaskArtifacts(ctx, taskRef, limits, budget)

  // 5. Execution-plan protocol + current plan state. The template Python
  // helper builds the identical text for every platform; this bridge never
  // mutates anything (plan.py remains the only state advancer).
  try {
    const planBlock = planProtocolBlock(ctx.directory, taskRef.taskDirFull, taskRef.contextKey)
    if (planBlock) parts.push(planBlock)
  } catch {
    // A plan problem must not strand the dispatch; the agent files carry the protocol too.
  }
  return parts.join("\n\n")
}

/** Check context: JSONL -> prd -> design -> implement (mirrors template hook). */
function getCheckContext(ctx, taskRef) {
  const limits = readContextInjectionLimits(ctx.directory)
  const budget = new ContextBudget(limits.max_total_bytes)
  const { parts } = materializeTaskArtifacts(ctx, taskRef, limits, budget)
  return parts.join("\n\n")
}

/** Research context: spec directory tree + search tips (template wording). */
function getResearchContext(ctx) {
  const specPath = ".trellis/spec"
  const specFull = join(ctx.directory, specPath)

  const treeLines = [`${specPath}/`]
  if (existsSync(specFull)) {
    try {
      const pkgDirs = readdirSync(specFull, { withFileTypes: true })
        .filter(d => d.isDirectory() && !d.name.startsWith("."))
        .map(d => d.name)
        .sort()
      for (const pkg of pkgDirs) {
        let layers = []
        try {
          layers = readdirSync(join(specFull, pkg), { withFileTypes: true })
            .filter(d => d.isDirectory())
            .map(d => d.name)
            .sort()
        } catch {
          // Ignore nested read errors
        }
        const layerInfo = layers.length > 0 ? ` (${layers.join(", ")})` : ""
        treeLines.push(`├── ${pkg}/${layerInfo}`)
      }
    } catch {
      // Ignore read errors
    }
  }

  const projectStructure = `## Project Spec Directory Structure

\`\`\`
${treeLines.join("\n")}
\`\`\`

To get structured package info, run: \`python ./.trellis/scripts/get_context.py --mode packages\`

## Search Tips

- Spec files: \`${specPath}/**/*.md\`
- Code search: Use Glob and Grep tools
- Tech solutions: Use mcp__exa__web_search_exa or mcp__exa__get_code_context_exa`

  return projectStructure
}

// ---------------------------------------------------------------------------
// Prompt builders (shapes mirrored from the template Python hook)
// ---------------------------------------------------------------------------

function buildImplementPrompt(ctx, originalPrompt, context, degradationNote = null) {
  let normalized
  let contract
  try {
    const bridge = normalizePromptViaPython(ctx.directory, originalPrompt, context)
    normalized = bridge.normalized_prompt
    contract = bridge.execution_contract
  } catch (error) {
    debugLog("inject", "prompt-policy bridge degraded:", error instanceof Error ? error.message : String(error))
    // Keep the raw business requirements; attach the static contract
    // explicitly instead of silently dropping the policy.
    normalized =
      "## Business requirements (preserved; tool wording is not a mandatory order)\n" +
      originalPrompt.trim() +
      `\n\n${STATIC_EXECUTION_CONTRACT}`
    contract = STATIC_EXECUTION_CONTRACT
    degradationNote = degradationNote || "[Trellis: prompt normalization degraded — the Python policy bridge was unavailable; the dispatch prompt was kept verbatim and the static execution contract applies.]"
  }

  return `${HOOK_MARKER}
# Implement Agent Task

You are the Implement Agent in the Multi-Agent Pipeline.

## Your Context

Trellis has injected the available task context for you:

${context}

---

## Trellis execution contract (applies to the task below)

${contract}

## Task requirements (normalized from the dispatch request)

${normalized}${degradationNote ? `\n\n${degradationNote}` : ""}

The context above was prepared by Trellis and should be used first, but the
marker does not guarantee that every task file or applicable Spec was included.
Do not reread a file merely because it is mentioned in the task-specific
instructions. Read it when the injected content is missing, truncated, stale,
or when a precise uncached line is required.

## Important Constraints

- Do NOT execute git commit, only code modifications
- Follow all dev specs injected above
- Report list of modified/created files when done`
}

function buildCheckPrompt(originalPrompt, context) {
  return `${HOOK_MARKER}
# Check Agent Task

You are the Check Agent in the Multi-Agent Pipeline (code and cross-layer checker).

## Your Context

Trellis has injected the available check and development context:

${context}

---

## Task-specific instructions

${originalPrompt}

The context above was prepared by Trellis and should be used first, but the
marker does not guarantee that every task file or applicable Spec was included.
Do not reread a file merely because it is mentioned in the task-specific
instructions. Read it when the injected content is missing, truncated, stale,
or when a precise uncached line is required.

## Review execution

1. Inspect the task change set and diff first.
2. Check every acceptance criterion against implementation or validation evidence.
3. Read additional Specs when the diff, call graph, acceptance criteria,
   selected review profile, or project rules prove they are relevant.
4. Fix only mechanical, small, and determinate in-scope issues and rerun only
   checks affected by each fix.
5. Report findings, checks not run, and residual risks before stopping.

## Finding handling

Fix only issues that are simultaneously mechanical, small, and determinate and
inside the current task scope, and record each fix and its verification in the
report. Design/judgment issues, implementation blocking defects, planning
defects, or out-of-task-scope findings are report-only: record location,
severity, evidence, and reason instead of silently rewriting them. You are a
reviewer, not an implementer: never dispatch or resume the Implement Agent,
and fix routing itself never schedules a review round. Review scheduling
follows the selected review profile and the task's evidence invalidation rules.

## Important Constraints

- Follow the finding-handling boundary above; never silently rewrite report-only findings.
- Follow the selected review profile and task-specific checks.
- Do not scan unrelated repository areas without evidence of impact.`
}

function buildFinishPrompt(originalPrompt, context) {
  return `${HOOK_MARKER}
# Finish Agent Task

You are performing the final check before creating a PR.

## Your Context

Finish checklist and requirements:

${context}

---

## Your Task

${originalPrompt}

---

## Workflow

1. **Review changes** - Run \`git diff --name-only\` to see all changed files
2. **Verify task artifacts** - Check requirements in prd.md and, when present, design.md / implement.md
3. **Spec sync** - Analyze whether changes introduce new patterns, contracts, or conventions
   - If new pattern/convention found: read target spec file -> update it -> update index.md if needed
   - If infra/cross-layer change: follow the 7-section mandatory template from update-spec.md
   - If pure code fix with no new patterns: skip this step
4. **Run final checks** - Execute only affected static checks, tests, and installer smoke checks defined by the task or project; report unavailable categories and downstream validation separately
5. **Confirm ready** - Ensure code is ready for PR

## Important Constraints

- You MAY update spec files when gaps are detected (use update-spec.md as guide)
- MUST read the target spec file BEFORE editing (avoid duplicating existing content)
- Do NOT update specs for trivial changes (typos, formatting, obvious fixes)
- If critical CODE issues found, report them clearly (fix specs, not code)
- Verify all acceptance criteria in prd.md are met
- Verify design.md and implement.md constraints when those files are present`
}

function buildResearchPrompt(originalPrompt, context, taskRef) {
  const taskLine = taskRef
    ? `Active task: ${taskRef.display}\nPersist research findings only under \`${taskRef.display}/research/\`.`
    : "No active task was resolved for this dispatch. Perform only non-persisting lookups, or ask the main session to bind a task; do NOT guess a research output directory."
  return `${HOOK_MARKER}
# Research Agent Task

You are the Research Agent in the Multi-Agent Pipeline (search researcher).

## Core Principle

**You do one thing: find and explain information.**

You are a documenter, not a reviewer.

## Project Info

${context}

## Task Binding

${taskLine}

---

## Your Task

${originalPrompt}

---

## Workflow

1. **Understand query** - Determine search type (internal/external) and scope
2. **Plan search** - List search steps for complex queries
3. **Execute search** - Execute multiple independent searches in a batch
4. **Organize results** - Output structured report

## Search Tools

| Tool | Purpose |
|------|---------|
| Glob | Search by filename pattern |
| Grep | Search by content |
| Read | Read file content |
| mcp__exa__web_search_exa | External web search |
| mcp__exa__get_code_context_exa | External code/doc search |

## Strict Boundaries

**Only allowed**: Describe what exists, where it is, how it works; write research notes only into the current task's \`research/\` directory when a task is bound.

**Forbidden** (unless explicitly asked):
- Suggest improvements
- Criticize implementation
- Recommend refactoring
- Modify product, template, Spec, or platform files
- Execute git commit / push / merge

## Report Format

Provide structured search results including:
- List of files found (with paths)
- Code pattern analysis (if applicable)
- Related spec documents
- External references (if any)`
}

/** Fail-closed notice when Implement/Check dispatch has no resolvable task. */
function buildBlockedPrompt(agentName, originalPrompt) {
  return `<!-- trellis-hook-note: context injection blocked -->
# Trellis context injection blocked

The OpenCode hook could not resolve an active task for this \`${agentName}\`
dispatch (no exact session pointer, no valid \`Active task: <path>\` line
inside this workspace, and the session runtime state is absent or ambiguous).

Follow your agent protocol: determine the task explicitly from the dispatch
facts below, or STOP and report the missing task binding to the main session.
Do NOT guess or borrow another session's task, and do NOT fabricate context.

## Original dispatch (unchanged)

${originalPrompt}`
}

// ---------------------------------------------------------------------------
// Task tool helpers
// ---------------------------------------------------------------------------

function extractSubagentName(args) {
  if (!args || typeof args !== "object") return ""
  for (const key of ["subagent_type", "subagentType", "agent_type", "agentType", "name"]) {
    const value = args[key]
    if (typeof value === "string" && value.trim()) {
      const name = value.trim()
      if (AGENTS_ALL.includes(name)) return name
      // Tolerate callers that pass the role without the trellis- prefix.
      const prefixed = `trellis-${name.replace(/^trellis-/, "")}`
      if (AGENTS_ALL.includes(prefixed)) return prefixed
      return name
    }
  }
  return ""
}

// ---------------------------------------------------------------------------
// Plugin factory (single default export)
// ---------------------------------------------------------------------------

export default async ({ directory, platform: hostPlatform = process.platform, env = process.env }) => {
  const ctx = new TrellisContext(directory)
  debugLog("inject", "Plugin loaded, directory:", directory)

  return {
    "tool.execute.before": async (input, output) => {
      try {
        if (process.env.TRELLIS_HOOKS === "0" || process.env.TRELLIS_DISABLE_HOOKS === "1") {
          return
        }
        if (!ctx.isTrellisProject()) return
        debugLog("inject", "tool.execute.before called, tool:", input?.tool)

        const toolName = String(input?.tool || "").toLowerCase()

        // 1) Shell identity bridge.
        if (toolName === "bash" || toolName === "shell") {
          if (injectTrellisContextIntoShell(ctx, input, output, hostPlatform, env)) {
            debugLog("inject", "Injected TRELLIS_CONTEXT_ID into shell command")
          }
          return
        }

        // 2) Native Task context injection.
        if (toolName !== "task") return
        const args = output?.args
        if (!args) return

        const agentName = extractSubagentName(args)
        if (!AGENTS_ALL.includes(agentName)) {
          debugLog("inject", "Skipping - unsupported subagent:", agentName || "(none)")
          return
        }

        const originalPrompt = typeof args.prompt === "string" ? args.prompt : ""
        debugLog("inject", "Task tool called, agent:", agentName)

        const resolved = ctx.resolveTaskForSubagent(input, originalPrompt, env)
        let taskRef = null
        if (resolved) {
          const taskDirFull = resolvePath(ctx.resolveTaskDir(resolved.taskPath))
          if (ctx.isWithinWorkspace(taskDirFull) && existsSync(taskDirFull)) {
            taskRef = {
              display: resolved.taskPath,
              taskDirFull,
              contextKey: ctx.getContextKey(input, env),
              source: resolved.source,
              agentKind: agentName === "trellis-check" ? "check" : "implement",
            }
          }
        }

        if (AGENTS_REQUIRE_TASK.includes(agentName) && !taskRef) {
          // Fail closed: block injection, require reporting, never guess.
          args.prompt = buildBlockedPrompt(agentName, originalPrompt)
          debugLog("inject", "Blocked - no resolvable active task for", agentName)
          return
        }

        const isFinish = agentName === "trellis-check" && originalPrompt.toLowerCase().includes("[finish]")

        let context = ""
        let newPrompt = ""
        if (agentName === "trellis-implement") {
          context = getImplementContext(ctx, taskRef)
          newPrompt = buildImplementPrompt(ctx, originalPrompt, context)
        } else if (agentName === "trellis-check") {
          context = getCheckContext(ctx, taskRef)
          newPrompt = isFinish
            ? buildFinishPrompt(originalPrompt, context)
            : buildCheckPrompt(originalPrompt, context)
        } else {
          context = getResearchContext(ctx)
          newPrompt = buildResearchPrompt(originalPrompt, context, taskRef)
        }

        if (!context) {
          debugLog("inject", "No context to inject")
          return
        }

        // Mutate args in-place — whole-object replacement does NOT work for
        // the task tool because the runtime holds a local reference.
        args.prompt = newPrompt
        debugLog("inject", "Injected context for", agentName, "prompt length:", newPrompt.length)
      } catch (error) {
        debugLog("inject", "Error in tool.execute.before:", error instanceof Error ? error.message : String(error), error instanceof Error ? error.stack : "")
      }
    },
  }
}
