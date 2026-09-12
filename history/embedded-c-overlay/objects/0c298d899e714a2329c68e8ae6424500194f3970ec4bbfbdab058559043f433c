/* global process */
/**
 * Trellis Session Utilities (OpenCode adapter)
 *
 * Pure, testable helpers used by the OpenCode plugins:
 *   - compact SessionStart context construction (mirrors the template
 *     `.claude/hooks/session-start.py` payload shape and wording);
 *   - per-turn `<workflow-state>` breadcrumb parsing/building (mirrors the
 *     template `.claude/hooks/inject-workflow-state.py`: workflow.md
 *     `[workflow-state:STATUS]` tag blocks are the single source of truth,
 *     no hardcoded routing table, explicit degradation when tags are absent);
 *   - Shell `TRELLIS_CONTEXT_ID` environment bridge helpers (PowerShell and
 *     POSIX/Git-Bash forms, no double-injection);
 *   - execution-plan display bridge that delegates to the template Python
 *     `common/execution_plan.py` so both platforms render identical text;
 *   - SessionStart history-detection helpers for injection dedup.
 *
 * All executable gates (task.py / plan.py) remain authoritative; this lib
 * only carries context into the OpenCode conversation.
 */

import { existsSync, readFileSync, readdirSync, statSync } from "fs"
import { join, isAbsolute, resolve as resolvePath } from "path"
import { platform } from "os"
import { execFileSync } from "child_process"
import process from "process"
import { PYTHON_CMD, debugLog, stringValue } from "./trellis-context.js"

export { PYTHON_CMD }

export const FIRST_REPLY_NOTICE = `<first-reply-notice>
On the first visible assistant reply in this session, briefly acknowledge that Trellis SessionStart context loaded.
Choose the acknowledgment language in this order:
1. Use the language of the user's current request (the user message that triggered this reply).
2. If that request has no clear natural language, use an explicitly established project communication language.
3. If neither provides a language, output the language-neutral fallback exactly: \`Trellis SessionStart ✓\`.
Continue directly with the user's request after the acknowledgment.
The acknowledgment must not alter the language used for the remainder of the response.
This notice is one-shot: do not repeat it after the first visible assistant reply in this session.
</first-reply-notice>`

// ---------------------------------------------------------------------------
// workflow.md breadcrumb tag blocks (single source of truth)
// ---------------------------------------------------------------------------

// Supports STATUS values with letters, digits, underscores, hyphens
// (so "in-review" / "blocked-by-team" work alongside "in_progress").
const TAG_RE = /\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n([\s\S]*?)\n\s*\[\/workflow-state:\1\]/g

/**
 * Parse workflow.md for [workflow-state:STATUS] blocks. Returns {status: body}.
 * Missing workflow.md or unreadable file returns {} so the breadcrumb
 * degrades visibly ("Refer to workflow.md for current step.") instead of the
 * plugin silently masking a broken workflow.
 */
export function loadBreadcrumbs(directory) {
  const workflowPath = join(directory, ".trellis", "workflow.md")
  if (!existsSync(workflowPath)) return {}
  let content
  try {
    content = readFileSync(workflowPath, "utf-8")
  } catch {
    return {}
  }
  const result = {}
  for (const match of content.matchAll(TAG_RE)) {
    const status = match[1]
    const body = match[2].trim()
    if (body) result[status] = body
  }
  return result
}

/**
 * Build the <workflow-state>...</workflow-state> block.
 * - Known status (tag present in workflow.md) -> detailed body
 * - Unknown status (no tag, or workflow.md missing) -> explicit degradation line
 * - no_task pseudo-status (taskId === null) -> header omits task info
 * - optional `note` -> appended after the body (e.g. session-ambiguity warning)
 */
export function buildBreadcrumb(taskId, status, templates, note = null) {
  let body = templates[status]
  if (body === undefined) {
    body = "Refer to workflow.md for current step."
  }
  const header = taskId === null ? `Status: ${status}` : `Task: ${taskId} (${status})`
  let block = `<workflow-state>\n${header}\n${body}\n</workflow-state>`
  if (note) {
    block += `\n\n<workflow-ambiguity>\n${note}\n</workflow-ambiguity>`
  }
  return block
}

export const DEFAULT_PROMPT_INJECTION_SKIP_KEYWORD = "no-trellis"

function stripInlineComment(value) {
  let inQuote = null
  for (let idx = 0; idx < value.length; idx++) {
    const ch = value[idx]
    if (inQuote) {
      if (ch === inQuote) inQuote = null
      continue
    }
    if (ch === '"' || ch === "'") {
      inQuote = ch
      continue
    }
    if (ch === "#" && (idx === 0 || /\s/.test(value[idx - 1]))) return value.slice(0, idx)
  }
  return value
}

function unquoteYaml(s) {
  if (s.length >= 2 && s[0] === s[s.length - 1] && (s[0] === '"' || s[0] === "'")) return s.slice(1, -1)
  return s
}

/**
 * Line-based parser for ONLY the `prompt_injection:` block of
 * `.trellis/config.yaml`. Mirrors the shared Python hook's
 * `_resolve_skip_keyword()` semantics (missing key keeps default; the
 * default is "no-trellis"; "" disables the escape hatch).
 */
export function readSkipKeyword(directory) {
  const path = join(directory, ".trellis", "config.yaml")
  if (!existsSync(path)) return DEFAULT_PROMPT_INJECTION_SKIP_KEYWORD
  let text
  try {
    text = readFileSync(path, "utf-8")
  } catch {
    return DEFAULT_PROMPT_INJECTION_SKIP_KEYWORD
  }

  let inSection = false
  let sectionIndent = -1
  for (const rawLine of text.split(/\r?\n/)) {
    const trimmed = rawLine.trim()
    if (!inSection) {
      if (/^prompt_injection\s*:\s*(#.*)?$/.test(trimmed)) {
        inSection = true
        sectionIndent = rawLine.length - rawLine.trimStart().length
      }
      continue
    }
    if (!trimmed || trimmed.startsWith("#")) continue
    const indent = rawLine.length - rawLine.trimStart().length
    if (indent <= sectionIndent) break
    const m = trimmed.match(/^skip_keyword\s*:\s*(.*)$/)
    if (!m) continue
    return unquoteYaml(stripInlineComment(m[1]).trim())
  }
  return DEFAULT_PROMPT_INJECTION_SKIP_KEYWORD
}

/**
 * Case-insensitive, word-boundary match of `keyword` in `text`. Hyphen
 * counts as a word char so "no-trellisx" / "xno-trellis" don't match, but
 * punctuation/whitespace boundaries do. Empty keyword never matches.
 */
export function promptHasSkipKeyword(text, keyword) {
  if (!keyword || typeof text !== "string") return false
  const escaped = keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  const pattern = new RegExp(`(?<![\\w-])${escaped}(?![\\w-])`, "i")
  return pattern.test(text)
}

// ---------------------------------------------------------------------------
// Task status (SessionStart / <task-status>)
// ---------------------------------------------------------------------------

export function hasCuratedJsonlEntry(jsonlPath) {
  try {
    const content = readFileSync(jsonlPath, "utf-8")
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim()
      if (!line) continue
      try {
        const row = JSON.parse(line)
        if (row && typeof row === "object" && typeof row.file === "string" && row.file) {
          return true
        }
      } catch {
        // Ignore malformed line
      }
    }
  } catch {
    return false
  }
  return false
}

/**
 * Compact active-task status for the main session. Uses the fail-closed
 * main resolution: never borrows another window's task. An ambiguous
 * runtime state is reported explicitly instead of guessed.
 */
export function getTaskStatus(ctx, platformInput = null) {
  const active = ctx.resolveMainTask(platformInput)
  const taskRef = active.taskPath
  if (!taskRef) {
    const base =
      "Status: NO ACTIVE TASK\n" +
      "Next-Action: Classify the current turn before creating any Trellis task. " +
      "Simple conversation / small task asks only whether this turn should create a Trellis task. " +
      "Complex task asks whether task creation and planning are allowed."
    if (active.source === "ambiguous") {
      return (
        base +
        "\nSession state: AMBIGUOUS — session runtime pointers exist but none is bound to this OpenCode session. " +
        "Do not borrow another window's task; tell the user and resolve the session identity or start the task in its own window."
      )
    }
    return base
  }

  const taskDir = ctx.resolveTaskDir(taskRef)

  if (active.stale || !taskDir || !existsSync(taskDir)) {
    return (
      `Status: STALE POINTER\nTask: ${taskRef}\n` +
      "Next-Action: Run `python ./.trellis/scripts/task.py finish` to clear the stale pointer, " +
      "then ask the user what to work on next."
    )
  }

  let taskData = {}
  const taskJsonPath = join(taskDir, "task.json")
  if (existsSync(taskJsonPath)) {
    try {
      taskData = JSON.parse(readFileSync(taskJsonPath, "utf-8"))
    } catch {
      // Ignore parse errors
    }
  }

  const taskTitle = taskData.title || taskRef
  const taskStatus = taskData.status || "unknown"

  if (taskStatus === "completed") {
    return `Status: COMPLETED\nTask: ${taskTitle}\nNext-Action: Run /trellis:finish-work. If the working tree is dirty, return to Phase 3.4 first.`
  }

  const hasPrd = existsSync(join(taskDir, "prd.md"))
  const hasDesign = existsSync(join(taskDir, "design.md"))
  const hasImplementPlan = existsSync(join(taskDir, "implement.md"))
  const artifactNames = ["prd.md", "design.md", "implement.md", "implement.jsonl", "check.jsonl"]
  const present = artifactNames.filter(name => existsSync(join(taskDir, name)))
  if (existsSync(join(taskDir, "research"))) present.push("research/")
  const presentLine = present.length > 0 ? present.join(", ") : "(none)"
  const implementJsonl = join(taskDir, "implement.jsonl")
  const checkJsonl = join(taskDir, "check.jsonl")
  const jsonlReady =
    (!existsSync(implementJsonl) || hasCuratedJsonlEntry(implementJsonl)) &&
    (!existsSync(checkJsonl) || hasCuratedJsonlEntry(checkJsonl))

  if (taskStatus === "planning" && !hasPrd) {
    return `Status: PLANNING\nTask: ${taskTitle}\nPresent: ${presentLine}\nNext-Action: Load \`trellis-brainstorm\` and write \`prd.md\`. Stay in planning.`
  }

  if (taskStatus === "planning") {
    const missingComplex = []
    if (!hasDesign) missingComplex.push("design.md")
    if (!hasImplementPlan) missingComplex.push("implement.md")
    const nextBits = []
    if (missingComplex.length > 0) {
      nextBits.push(
        `Lightweight task can request start review with PRD-only; complex task must add ${missingComplex.join(", ")} before start`,
      )
    } else {
      nextBits.push("Planning artifacts are present; ask for review before `task.py start`")
    }
    if (!jsonlReady) {
      nextBits.push("curate `implement.jsonl` and `check.jsonl` before sub-agent mode start")
    }
    return `Status: PLANNING\nTask: ${taskTitle}\nPresent: ${presentLine}\nNext-Action: ${nextBits.join("; ")}. Do not enter implementation until the user confirms start.`
  }

  return (
    `Status: ${String(taskStatus).toUpperCase()}\nTask: ${taskTitle}\n` +
    `Present: ${presentLine}\n` +
    "Next-Action: Follow the matching per-turn workflow-state. " +
    "Implementation/check context order is jsonl entries -> `prd.md` -> `design.md if present` -> `implement.md if present`."
  )
}

// ---------------------------------------------------------------------------
// Config / spec index discovery (mirrors template session-start.py)
// ---------------------------------------------------------------------------

export function loadTrellisConfig(directory, contextKey = null) {
  const scriptPath = join(directory, ".trellis", "scripts", "get_context.py")
  if (!existsSync(scriptPath)) {
    return { isMonorepo: false, packages: {}, specScope: null, activeTaskPackage: null, defaultPackage: null }
  }
  try {
    const output = execFileSync(PYTHON_CMD, [scriptPath, "--mode", "packages", "--json"], {
      cwd: directory,
      timeout: 5000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        ...(contextKey ? { TRELLIS_CONTEXT_ID: contextKey } : {}),
      },
    })
    const data = JSON.parse(output)
    if (data.mode !== "monorepo") {
      return { isMonorepo: false, packages: {}, specScope: null, activeTaskPackage: null, defaultPackage: null }
    }
    const pkgDict = {}
    for (const pkg of (data.packages || [])) {
      pkgDict[pkg.name] = pkg
    }
    return {
      isMonorepo: true,
      packages: pkgDict,
      specScope: data.specScope || null,
      activeTaskPackage: data.activeTaskPackage || null,
      defaultPackage: data.defaultPackage || null,
    }
  } catch (e) {
    debugLog("session", "loadTrellisConfig error:", e instanceof Error ? e.message : String(e))
    return { isMonorepo: false, packages: {}, specScope: null, activeTaskPackage: null, defaultPackage: null }
  }
}

export function checkLegacySpec(directory, config) {
  if (!config.isMonorepo || Object.keys(config.packages).length === 0) {
    return null
  }

  const specDir = join(directory, ".trellis", "spec")
  if (!existsSync(specDir)) return null

  let hasLegacy = false
  for (const name of ["backend", "frontend"]) {
    if (existsSync(join(specDir, name, "index.md"))) {
      hasLegacy = true
      break
    }
  }
  if (!hasLegacy) return null

  const pkgNames = Object.keys(config.packages).sort()
  const missing = pkgNames.filter(name => !existsSync(join(specDir, name)))

  if (missing.length === 0) return null

  if (missing.length === pkgNames.length) {
    return (
      `[!] Legacy spec structure detected: found \`spec/backend/\` or \`spec/frontend/\` ` +
      `but no package-scoped \`spec/<package>/\` directories.\n` +
      `Monorepo packages: ${pkgNames.join(", ")}\n` +
      `Please reorganize: \`spec/backend/\` -> \`spec/<package>/backend/\``
    )
  }
  return (
    `[!] Partial spec migration detected: packages ${missing.join(", ")} ` +
    `still missing \`spec/<pkg>/\` directory.\n` +
    `Please complete migration for all packages.`
  )
}

export function resolveSpecScope(config) {
  if (!config.isMonorepo || Object.keys(config.packages).length === 0) {
    return null
  }

  const { specScope, activeTaskPackage, defaultPackage, packages } = config
  if (specScope == null) return null

  if (specScope === "active_task") {
    if (activeTaskPackage && activeTaskPackage in packages) return new Set([activeTaskPackage])
    if (defaultPackage && defaultPackage in packages) return new Set([defaultPackage])
    return null
  }

  if (Array.isArray(specScope)) {
    const valid = new Set()
    for (const entry of specScope) {
      if (entry in packages) {
        valid.add(entry)
      }
    }
    if (valid.size > 0) return valid
    if (activeTaskPackage && activeTaskPackage in packages) return new Set([activeTaskPackage])
    if (defaultPackage && defaultPackage in packages) return new Set([defaultPackage])
    return null
  }

  return null
}

export function collectSpecIndexPaths(directory, allowedPkgs) {
  const specDir = join(directory, ".trellis", "spec")
  const paths = []

  const guidesIndex = join(specDir, "guides", "index.md")
  if (existsSync(guidesIndex)) {
    paths.push(".trellis/spec/guides/index.md")
  }

  if (!existsSync(specDir)) return paths

  try {
    const subs = readdirSync(specDir).filter(name => {
      if (name.startsWith(".") || name === "guides") return false
      try {
        return statSync(join(specDir, name)).isDirectory()
      } catch {
        return false
      }
    }).sort()

    for (const sub of subs) {
      const indexFile = join(specDir, sub, "index.md")
      if (existsSync(indexFile)) {
        paths.push(`.trellis/spec/${sub}/index.md`)
      } else {
        if (allowedPkgs !== null && !allowedPkgs.has(sub)) continue
        try {
          const nested = readdirSync(join(specDir, sub)).filter(name => {
            try {
              return statSync(join(specDir, sub, name)).isDirectory()
            } catch {
              return false
            }
          }).sort()
          for (const layer of nested) {
            const nestedIndex = join(specDir, sub, layer, "index.md")
            if (existsSync(nestedIndex)) {
              paths.push(`.trellis/spec/${sub}/${layer}/index.md`)
            }
          }
        } catch {
          // Ignore directory read errors
        }
      }
    }
  } catch {
    // Ignore spec directory read errors
  }

  return paths
}

export function readDeveloper(directory) {
  try {
    const content = readFileSync(join(directory, ".trellis", ".developer"), "utf-8")
    for (const line of content.split(/\r?\n/)) {
      if (line.startsWith("name=")) return line.slice("name=".length).trim()
    }
  } catch {
    // Ignore missing developer file
  }
  return "(not initialized)"
}

export function runGit(directory, args) {
  try {
    return execFileSync("git", args, {
      cwd: directory,
      timeout: 3000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    }).trim()
  } catch {
    return ""
  }
}

export function buildCompactCurrentState(ctx, platformInput, specIndexPaths) {
  const directory = ctx.directory
  const lines = []
  lines.push(`Developer: ${readDeveloper(directory)}`)

  const branch = runGit(directory, ["branch", "--show-current"]) || "(detached)"
  const dirtyCount = runGit(directory, ["status", "--porcelain"])
    .split(/\r?\n/)
    .filter(line => line.trim()).length
  lines.push(`Git: branch ${branch}; ${dirtyCount === 0 ? "clean" : `dirty ${dirtyCount} paths`}.`)

  const active = ctx.resolveMainTask(platformInput)
  if (active.taskPath) {
    const taskDir = ctx.resolveTaskDir(active.taskPath)
    let status = "unknown"
    if (taskDir) {
      try {
        const data = JSON.parse(readFileSync(join(taskDir, "task.json"), "utf-8"))
        status = data.status || "unknown"
      } catch {
        // Ignore parse errors
      }
    }
    lines.push(`Current task: ${active.taskPath}; status=${status}.`)
  } else {
    lines.push("Current task: none.")
  }

  const tasksDir = join(directory, ".trellis", "tasks")
  if (existsSync(tasksDir)) {
    try {
      const activeTasks = readdirSync(tasksDir, { withFileTypes: true })
        .filter(entry => entry.isDirectory() && entry.name !== "archive" && existsSync(join(tasksDir, entry.name, "task.json")))
      lines.push(`Active tasks: ${activeTasks.length} total. Use \`python ./.trellis/scripts/task.py list --mine\` only if needed.`)
    } catch {
      // Ignore task list errors
    }
  }

  const developer = readDeveloper(directory)
  const workspaceDir = join(directory, ".trellis", "workspace", developer)
  if (developer !== "(not initialized)" && existsSync(workspaceDir)) {
    try {
      const journals = readdirSync(workspaceDir)
        .filter(name => /^journal-\d+\.md$/.test(name))
        .sort((a, b) => Number(a.match(/\d+/)?.[0] || 0) - Number(b.match(/\d+/)?.[0] || 0))
      const journal = journals[journals.length - 1]
      if (journal) {
        const journalPath = join(workspaceDir, journal)
        const lineCount = readFileSync(journalPath, "utf-8").split(/\r?\n/).length
        lines.push(`Journal: .trellis/workspace/${developer}/${journal}, ${lineCount} / 2000 lines.`)
      }
    } catch {
      // Ignore journal errors
    }
  }

  if (specIndexPaths.length > 0) {
    lines.push(`Spec indexes: ${specIndexPaths.length} available.`)
  }

  return lines.join("\n")
}

// ---------------------------------------------------------------------------
// Execution-plan display bridge (delegates to the template Python helper so
// every platform renders identical plan state; never mutates anything)
// ---------------------------------------------------------------------------

const PLAN_BREADCRUMB_PY =
  "import sys\n" +
  "from pathlib import Path\n" +
  "sys.path.insert(0, str(Path('.trellis') / 'scripts'))\n" +
  "from common.execution_plan import plan_breadcrumb\n" +
  "text = plan_breadcrumb(Path.cwd(), Path(sys.argv[1]))\n" +
  "if text:\n" +
  "    sys.stdout.write(text + '\\n')\n"

const PLAN_PROTOCOL_PY =
  "import sys\n" +
  "from pathlib import Path\n" +
  "sys.path.insert(0, str(Path('.trellis') / 'scripts'))\n" +
  "from common.execution_plan import plan_protocol_block\n" +
  "sys.stdout.write(plan_protocol_block(Path.cwd(), Path(sys.argv[1])) + '\\n')\n"

function runPythonFragment(directory, code, taskDirAbs, contextKey) {
  try {
    const output = execFileSync(PYTHON_CMD, ["-W", "ignore", "-c", code, taskDirAbs], {
      cwd: directory,
      timeout: 8000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        ...(contextKey ? { TRELLIS_CONTEXT_ID: contextKey } : {}),
      },
    })
    return output.trim()
  } catch (e) {
    debugLog("session", "plan python bridge failed:", e instanceof Error ? e.message : String(e))
    return ""
  }
}

/** Compact <execution-plan> block for the active task, when one exists. */
export function planBreadcrumb(directory, taskDirAbs, contextKey = null) {
  if (!taskDirAbs || !isAbsolute(taskDirAbs)) return ""
  const text = runPythonFragment(directory, PLAN_BREADCRUMB_PY, taskDirAbs, contextKey)
  return text || ""
}

/** Execution-plan protocol + current state for implement prompts. */
export function planProtocolBlock(directory, taskDirAbs, contextKey = null) {
  if (!taskDirAbs || !isAbsolute(taskDirAbs)) return ""
  const text = runPythonFragment(directory, PLAN_PROTOCOL_PY, taskDirAbs, contextKey)
  return text || ""
}

// ---------------------------------------------------------------------------
// Compact SessionStart context
// ---------------------------------------------------------------------------

export function buildSessionContext(ctx, platformInput = null) {
  const directory = ctx.directory
  const contextKey = typeof ctx.getContextKey === "function"
    ? ctx.getContextKey(platformInput)
    : null

  const config = loadTrellisConfig(directory, contextKey)
  const allowedPkgs = resolveSpecScope(config)
  const paths = collectSpecIndexPaths(directory, allowedPkgs)

  const parts = []

  parts.push(`<session-context>
Trellis compact SessionStart context. Use it to orient the session; load details on demand.
</session-context>`)
  parts.push(FIRST_REPLY_NOTICE)

  const legacyWarning = checkLegacySpec(directory, config)
  if (legacyWarning) {
    parts.push(`<migration-warning>\n${legacyWarning}\n</migration-warning>`)
  }

  parts.push("<current-state>")
  parts.push(buildCompactCurrentState(ctx, platformInput, paths))
  parts.push("</current-state>")

  const workflowContent = ctx.readProjectFile(".trellis/workflow.md")
  if (workflowContent) {
    const allLines = workflowContent.split("\n")
    const overviewLines = [
      "# Development Workflow - Session Summary",
      "Full guide: .trellis/workflow.md. Step detail: `python ./.trellis/scripts/get_context.py --mode phase --step <X.Y>`.",
      "",
    ]

    let rangeStart = -1
    let rangeEnd = allLines.length
    for (let i = 0; i < allLines.length; i++) {
      const stripped = allLines[i].trim()
      if (rangeStart === -1 && stripped === "## Phase Index") {
        rangeStart = i
      } else if (rangeStart !== -1 && stripped === "## Phase 1: Plan") {
        rangeEnd = i
        break
      }
    }
    if (rangeStart !== -1) {
      const strippedStateBlocks = allLines
        .slice(rangeStart, rangeEnd)
        .join("\n")
        .replace(/\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n[\s\S]*?\n\s*\[\/workflow-state:\1\]\n?/g, "")
        .replace(/<!--[\s\S]*?-->/g, "")
        .replace(/^\[(?!\/?workflow-state:)\/?[^\]\n]+\]\s*\n?/gm, "")
        .replace(/\n{3,}/g, "\n\n")
      overviewLines.push(strippedStateBlocks.trimEnd())
    }

    parts.push("<trellis-workflow>")
    parts.push(overviewLines.join("\n").trimEnd())
    parts.push("</trellis-workflow>")
  }

  parts.push("<guidelines>")
  parts.push(
    "Task context order for implementation/check: jsonl entries -> `prd.md` -> " +
    "`design.md if present` -> `implement.md if present`. Missing optional artifacts " +
    "are skipped for lightweight tasks.\n"
  )

  if (paths.length > 0) {
    parts.push("## Available indexes (read on demand)")
    for (const p of paths) {
      parts.push(`- ${p}`)
    }
    parts.push("")
  }

  parts.push(
    "Discover more via: " +
    "`python ./.trellis/scripts/get_context.py --mode packages`"
  )
  parts.push("</guidelines>")

  const taskStatus = getTaskStatus(ctx, platformInput)
  parts.push(`<task-status>\n${taskStatus}\n</task-status>`)

  const active = ctx.resolveMainTask(platformInput)
  if (active.taskPath && !active.stale) {
    const taskDir = ctx.resolveTaskDir(active.taskPath)
    const planCtx = taskDir ? planBreadcrumb(directory, resolvePath(taskDir), active.contextKey) : ""
    if (planCtx) {
      parts.push(planCtx)
    }
  }

  parts.push(`<ready>
Context loaded. Follow <task-status>. Load workflow/spec/task details only when needed.
</ready>`)

  return parts.join("\n\n")
}

// ---------------------------------------------------------------------------
// SessionStart dedup helpers (metadata markers on persisted parts)
// ---------------------------------------------------------------------------

function getTrellisMetadata(metadata) {
  if (!metadata || typeof metadata !== "object") {
    return {}
  }

  const trellis = metadata.trellis
  if (!trellis || typeof trellis !== "object") {
    return {}
  }

  return trellis
}

function markPartAsSessionStart(part) {
  const metadata = part.metadata && typeof part.metadata === "object"
    ? part.metadata
    : {}
  part.metadata = {
    ...metadata,
    trellis: {
      ...getTrellisMetadata(metadata),
      sessionStart: true,
    },
  }
}

function hasSessionStartMarker(part) {
  if (!part || part.type !== "text" || typeof part.text !== "string") {
    return false
  }

  return getTrellisMetadata(part.metadata).sessionStart === true
}

export function hasInjectedTrellisContext(messages) {
  if (!Array.isArray(messages)) {
    return false
  }

  return messages.some(message => {
    if (!message?.info || message.info.role !== "user" || !Array.isArray(message.parts)) {
      return false
    }

    return message.parts.some(hasSessionStartMarker)
  })
}

export async function hasPersistedInjectedContext(client, directory, sessionID) {
  try {
    const response = await client.session.messages({
      path: { id: sessionID },
      query: { directory },
      throwOnError: true,
    })
    return hasInjectedTrellisContext(response.data || [])
  } catch (error) {
    debugLog(
      "session",
      "Failed to read session history for dedupe:",
      error instanceof Error ? error.message : String(error),
    )
    return false
  }
}

export function markContextInjected(part) {
  markPartAsSessionStart(part)
}

// ---------------------------------------------------------------------------
// Prompt-policy bridge: reuse the template Python normalizer verbatim.
// ---------------------------------------------------------------------------

/**
 * Call `.trellis/scripts/common/subagent_prompt_policy.py --json` with
 * {"prompt", "injected_context"} on stdin and return
 * {"normalized_prompt", "execution_contract", "policy_marker"}.
 * Throws on process failure, timeout, or invalid response shape so the
 * caller can degrade explicitly (the raw business prompt must never be
 * silently replaced by a JavaScript re-implementation of the rules).
 */
export function normalizePromptViaPython(directory, prompt, injectedContext) {
  const scriptPath = join(directory, ".trellis", "scripts", "common", "subagent_prompt_policy.py")
  if (!existsSync(scriptPath)) {
    throw new Error(`prompt policy script not found: ${scriptPath}`)
  }
  const payload = JSON.stringify({ prompt, injected_context: injectedContext })
  const output = execFileSync(PYTHON_CMD, [scriptPath, "--json"], {
    cwd: directory,
    timeout: 8000,
    input: payload,
    encoding: "utf-8",
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  })
  const data = JSON.parse(output)
  if (
    !data || typeof data !== "object" ||
    typeof data.normalized_prompt !== "string" ||
    typeof data.execution_contract !== "string" ||
    typeof data.policy_marker !== "string"
  ) {
    throw new Error("prompt policy bridge returned an invalid response shape")
  }
  return data
}

// ---------------------------------------------------------------------------
// Static degradation fallback for the prompt-policy bridge.
//
// These strings MUST stay byte-identical with
// `.trellis/scripts/common/subagent_prompt_policy.py`
// (`execution_contract()` / `policy_marker()`); the platform contract test
// asserts equality, so a Python-side wording change fails the test instead
// of silently drifting. They are used ONLY when the Python `--json` bridge
// is unavailable and the raw business prompt must keep an explicit contract.
// ---------------------------------------------------------------------------

export const STATIC_POLICY_MARKER = "[Trellis dispatch policy normalized]"

export const STATIC_EXECUTION_CONTRACT =
  "Preserve task scope, acceptance criteria, and required validation commands. " +
  "Treat per-item wording as report granularity, not one tool call per item. " +
  "Batch independent reads and searches; perform targeted follow-up only when " +
  "a batch result proves it is needed. Do not rebuild for comment or historical " +
  "documentation matches. After a real code fix, rerun only affected checks " +
  "and stop when scope, evidence, verification, and report are complete."

// ---------------------------------------------------------------------------
// Shell identity bridge (TRELLIS_CONTEXT_ID) for OpenCode shell tools
// ---------------------------------------------------------------------------

export function shellQuote(value) {
  return `'${String(value).replace(/'/g, "'\\''")}'`
}

export function powershellQuote(value) {
  return `'${String(value).replace(/'/g, "''")}'`
}

export function envValue(env, key) {
  const value = env?.[key]
  return typeof value === "string" && value.trim() ? value.trim() : null
}

export function shellBasename(value) {
  return value.replace(/\\/g, "/").split("/").pop()?.toLowerCase() || ""
}

/** True when a Windows host is running a POSIX-like shell (Git Bash / MSYS). */
export function isWindowsPosixShell(env = process.env) {
  if (envValue(env, "MSYSTEM")) return true
  if (envValue(env, "MINGW_PREFIX")) return true
  if (envValue(env, "OPENCODE_GIT_BASH_PATH")) return true

  const ostype = envValue(env, "OSTYPE")?.toLowerCase() || ""
  if (/(msys|mingw|cygwin)/.test(ostype)) return true

  const shell = shellBasename(envValue(env, "SHELL") || "")
  return /^(bash|sh|zsh)(\.exe)?$/.test(shell)
}

/**
 * Environment prefix that exposes the current Trellis session identity to a
 * shell command: PowerShell form on Windows native shells, POSIX export
 * otherwise.
 */
export function buildTrellisContextPrefix(contextKey, hostPlatform = platform(), env = process.env) {
  if (hostPlatform === "win32" && !isWindowsPosixShell(env)) {
    return `$env:TRELLIS_CONTEXT_ID = ${powershellQuote(contextKey)}; `
  }

  return `export TRELLIS_CONTEXT_ID=${shellQuote(contextKey)}; `
}

/** Which shell-tool argument field carries the command ("command" | "cmd" | null). */
export function getShellCommandKey(args) {
  if (!args || typeof args !== "object") return null
  if (typeof args.command === "string") return "command"
  if (typeof args.cmd === "string") return "cmd"
  return null
}

/** True when the command already sets TRELLIS_CONTEXT_ID explicitly up front. */
export function commandStartsWithTrellisContext(command) {
  const firstCommand = command.trimStart().split(/[;&|]/, 1)[0].trimStart()
  return (
    /^TRELLIS_CONTEXT_ID\s*=/.test(firstCommand) ||
    /^export\s+TRELLIS_CONTEXT_ID\s*=/.test(firstCommand) ||
    /^env\s+(?:(?:-\S+|[A-Za-z_][A-Za-z0-9_]*=\S*)\s+)*TRELLIS_CONTEXT_ID\s*=/.test(firstCommand) ||
    /^\$env:TRELLIS_CONTEXT_ID\s*=/i.test(firstCommand)
  )
}

/**
 * OpenCode TUI does not guarantee session identity in the shell environment.
 * Prefix the shell command with the current session's TRELLIS_CONTEXT_ID so
 * `task.py` / `plan.py` hit the right session pointer. Commands that already
 * set the variable explicitly are left untouched. Returns true when injected.
 */
export function injectTrellisContextIntoShell(ctx, input, output, hostPlatform = platform(), env = process.env) {
  const args = output?.args
  const commandKey = getShellCommandKey(args)
  if (!commandKey) return false

  const command = args[commandKey]
  if (!command.trim()) return false
  if (commandStartsWithTrellisContext(command)) return false

  const contextKey = ctx.getContextKey(input, env)
  if (!contextKey) return false

  args[commandKey] = `${buildTrellisContextPrefix(contextKey, hostPlatform, env)}${command}`
  return true
}
