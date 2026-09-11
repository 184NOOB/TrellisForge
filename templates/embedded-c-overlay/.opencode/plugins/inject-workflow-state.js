/* global process */
/**
 * Trellis Workflow State Injection Plugin (OpenCode)
 *
 * Per-turn <workflow-state> breadcrumb — the OpenCode equivalent of the
 * template `.claude/hooks/inject-workflow-state.py` (UserPromptSubmit).
 *
 * Contract parity points:
 *   - Breadcrumb body is pulled exclusively from the project's
 *     `.trellis/workflow.md` `[workflow-state:STATUS]` tag blocks;
 *     workflow.md is the single source of truth. There is no second routing
 *     table in this plugin: a missing tag or missing workflow.md degrades to
 *     "Refer to workflow.md for current step." so the broken state is visible
 *     to the user instead of being masked.
 *   - Main-session resolution is fail-closed (exact session pointer only);
 *     an ambiguous runtime state emits the no_task breadcrumb plus an
 *     explicit <workflow-ambiguity> note and never borrows another window.
 *   - Stale pointers surface as `stale_session` (unknown tag -> explicit
 *     degradation), matching the Python hook.
 *   - A display-only <execution-plan> supplement is appended through the
 *     template's own Python `plan_breadcrumb` renderer (identical text across
 *     platforms; never a gate — plan.py stays the only state advancer).
 *   - Sub-agent turns, TRELLIS_HOOKS=0 / TRELLIS_DISABLE_HOOKS=1,
 *     OPENCODE_NON_INTERACTIVE=1, non-Trellis projects, and the configurable
 *     `no-trellis` standalone-word escape hatch are all skipped.
 *
 * Unlike session-start, this plugin does NOT dedupe — the breadcrumb must
 * surface on every turn so long conversations don't drift.
 *
 * Export shape: exactly one default export (OpenCode 1.2.x calls every
 * module export as a plugin factory).
 */

import { existsSync, readFileSync } from "fs"
import { join, resolve as resolvePath } from "path"
import { TrellisContext, debugLog, isTrellisSubagent } from "../lib/trellis-context.js"
import {
  buildBreadcrumb,
  loadBreadcrumbs,
  planBreadcrumb,
  promptHasSkipKeyword,
  readSkipKeyword,
} from "../lib/session-utils.js"

/**
 * Resolve (taskId, statusKey) for the breadcrumb from the fail-closed main
 * resolution. Returns null when there is no active task (including stale
 * pointers, which report the "stale_session" pseudo-status).
 */
function getActiveTaskState(ctx, input) {
  const active = ctx.resolveMainTask(input)
  const taskRef = active.taskPath
  if (!taskRef) return { taskId: null, status: "no_task", ambiguous: active.source === "ambiguous" }

  const taskDir = ctx.resolveTaskDir(taskRef)
  if (active.stale || !taskDir || !existsSync(taskDir)) {
    // Mirror Python `get_active_task`: stale -> f"stale_{source_type}"
    return { taskId: taskRef.split("/").pop(), status: "stale_session", ambiguous: false }
  }
  const taskJsonPath = join(taskDir, "task.json")
  if (!existsSync(taskJsonPath)) return { taskId: null, status: "no_task", ambiguous: false }
  try {
    const data = JSON.parse(readFileSync(taskJsonPath, "utf-8"))
    const status = typeof data.status === "string" ? data.status : ""
    if (!status) return { taskId: null, status: "no_task", ambiguous: false }
    const id = data.id || taskRef.split("/").pop()
    return { taskId: id, status, ambiguous: false }
  } catch {
    return { taskId: null, status: "no_task", ambiguous: false }
  }
}

export default async ({ directory }) => {
  const ctx = new TrellisContext(directory)
  debugLog("workflow-state", "Plugin loaded, directory:", directory)

  return {
    "chat.message": async (input, output) => {
      try {
        // Sub-agent turns get no main-session breadcrumb.
        if (isTrellisSubagent(input)) {
          debugLog("workflow-state", "Skipping trellis subagent turn:", input?.agent)
          return
        }
        if (process.env.TRELLIS_HOOKS === "0" || process.env.TRELLIS_DISABLE_HOOKS === "1") {
          return
        }
        if (process.env.OPENCODE_NON_INTERACTIVE === "1") {
          return
        }
        if (!ctx.isTrellisProject()) {
          return
        }

        const parts = output?.parts || []
        const textPartIndex = parts.findIndex(
          p => p.type === "text" && p.text !== undefined,
        )
        const originalText = textPartIndex !== -1 ? (parts[textPartIndex].text || "") : ""

        // Escape hatch: standalone skip keyword suppresses this turn only.
        if (promptHasSkipKeyword(originalText, readSkipKeyword(directory))) {
          debugLog("workflow-state", "Skipping turn: skip keyword present in prompt")
          return
        }

        const templates = loadBreadcrumbs(directory)
        const task = getActiveTaskState(ctx, input)
        const ambiguityNote = task.ambiguous
          ? "Session runtime pointers exist for other sessions, but none is bound to this OpenCode session. " +
            "Do not borrow another window's task: run task.py with the correct session identity (TRELLIS_CONTEXT_ID) " +
            "or start the task in this session."
          : null
        let breadcrumb = buildBreadcrumb(
          task.taskId,
          task.status,
          templates,
          ambiguityNote,
        )

        // Display-only execution-plan supplement (never a gate; identical
        // renderer as the Python hook via the plan_breadcrumb bridge).
        const active = ctx.resolveMainTask(input)
        if (active.taskPath && !active.stale) {
          const taskDir = ctx.resolveTaskDir(active.taskPath)
          const planCtx = taskDir ? planBreadcrumb(directory, resolvePath(taskDir), active.contextKey) : ""
          if (planCtx) {
            breadcrumb = `${breadcrumb}\n\n${planCtx}`
          }
        }

        if (textPartIndex !== -1) {
          parts[textPartIndex].text = `${breadcrumb}\n\n${originalText}`
        } else {
          parts.unshift({ type: "text", text: breadcrumb })
        }
        debugLog(
          "workflow-state",
          "Injected breadcrumb for task",
          task.taskId ?? "none",
          "status",
          task.status,
        )
      } catch (error) {
        debugLog(
          "workflow-state",
          "Error in chat.message:",
          error instanceof Error ? error.message : String(error),
        )
      }
    },
  }
}
