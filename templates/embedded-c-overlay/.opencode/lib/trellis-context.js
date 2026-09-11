/**
 * Trellis Context Manager (OpenCode adapter)
 *
 * Shared foundation for the OpenCode plugins: session-key resolution that is
 * byte-compatible with `.trellis/scripts/common/active_task.py`
 * (platform="opencode"), fail-closed task-pointer resolution, workspace
 * boundary checks, JSONL parsing, context materialization, and the
 * `.trellis/config.yaml` context-injection budget.
 *
 * TrellisForge customization notes (vs upstream Trellis 0.6.10):
 *   - Context-key precedence mirrors the Python resolver exactly:
 *     TRELLIS_CONTEXT_ID override -> platform-input session/conversation/
 *     transcript ids -> OPENCODE_SESSION_ID / OPENCODE_SESSIONID /
 *     OPENCODE_RUN_ID environment keys.
 *   - Main-session resolution never borrows another window's task: an exact
 *     session file without a pointer is authoritative `no_task`; other session
 *     files present without an exact key are reported as "ambiguous".
 *   - The single-session compatibility fallback is only exposed to Task
 *     sub-agent dispatch resolution, never to the main session.
 *   - All candidate task refs must resolve inside the workspace and the
 *     directory must exist for hint/fallback paths.
 *   - Notice texts stay byte-identical with the Python hooks so tests can
 *     compare materials across platforms.
 */

import { existsSync, readFileSync, appendFileSync, readdirSync, statSync } from "fs"
import { isAbsolute, join, resolve as resolvePath, relative as relativePath, sep } from "path"
import { platform, tmpdir } from "os"
import { createHash } from "crypto"
import { Buffer, isUtf8 } from "buffer"
import process from "process"

export const PYTHON_CMD = platform() === "win32" ? "python" : "python3"

// Debug logging (best-effort; never fatal).
const DEBUG_LOG = join(tmpdir(), "trellis-opencode-plugin-debug.log")

export function debugLog(prefix, ...args) {
  const timestamp = new Date().toISOString()
  const msg = `[${timestamp}] [${prefix}] ${args.map(a => typeof a === "object" ? JSON.stringify(a) : a).join(" ")}\n`
  try {
    appendFileSync(DEBUG_LOG, msg)
  } catch {
    // ignore
  }
}

export function stringValue(value) {
  return typeof value === "string" && value.trim() ? value.trim() : null
}

/** Mirror of Python `active_task._sanitize_key`. */
export function sanitizeKey(raw) {
  const safe = String(raw).trim().replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^[._-]+|[._-]+$/g, "")
  return safe ? safe.slice(0, 160) : ""
}

/** Mirror of Python `active_task._hash_value` (sha256 hex, first 24 chars). */
export function hashValue(raw) {
  return createHash("sha256").update(String(raw), "utf8").digest("hex").slice(0, 24)
}

function lookupString(data, keys) {
  if (!data || typeof data !== "object") return null
  for (const key of keys) {
    const value = stringValue(data[key])
    if (value) return value
  }
  for (const nestedKey of ["input", "properties", "event", "hook_input", "hookInput"]) {
    const nested = data[nestedKey]
    if (nested && typeof nested === "object") {
      const value = lookupString(nested, keys)
      if (value) return value
    }
  }
  return null
}

/** Mirror of Python `active_task._context_key` for the opencode platform. */
export function buildContextKey(platformName, kind, value) {
  if (kind === "transcript") {
    return `${platformName}_transcript_${hashValue(value)}`
  }
  const safeValue = sanitizeKey(value)
  return safeValue ? `${platformName}_${safeValue}` : `${platformName}_${hashValue(value)}`
}

/** Convenience for cross-language fixed-vector tests. */
export function contextKeyForSessionId(sessionId) {
  return buildContextKey("opencode", "session", sessionId)
}

// Environment session-identity keys, matching Python `_ENV_SESSION_KEYS["opencode"]`
// in the same priority order.
const OPENCODE_ENV_SESSION_KEYS = ["OPENCODE_SESSION_ID", "OPENCODE_SESSIONID", "OPENCODE_RUN_ID"]

// Matches `trellis-implement`, `trellis-check`, `trellis-research` exactly.
// Used by chat.message plugins to skip injection inside Trellis sub-agent turns.
const TRELLIS_SUBAGENT_RE = /^trellis-(implement|check|research)$/

/**
 * Return true when the OpenCode `chat.message` input represents a Trellis
 * sub-agent turn (`input.agent` is set by OpenCode for Task-spawned children).
 */
export function isTrellisSubagent(input) {
  if (!input || typeof input !== "object") return false
  const agent = typeof input.agent === "string" ? input.agent.trim() : ""
  return TRELLIS_SUBAGENT_RE.test(agent)
}

// ============================================================
// Context Injection Limits
//
// Notice text and behavior mirrored from the template Python hook
// `.claude/hooks/inject-subagent-context.py` — changing wording here
// requires changing it there too (covered by cross-platform tests).
// ============================================================

export const DEFAULT_CONTEXT_INJECTION_LIMITS = {
  max_file_bytes: 32768,
  max_artifact_bytes: 65536,
  max_total_bytes: 131072,
}

/**
 * Truncate `buf` to at most `cap` bytes without splitting a UTF-8
 * multi-byte sequence. `cap <= 0` means "no limit".
 */
export function truncateUtf8(buf, cap) {
  if (cap <= 0 || buf.length <= cap) return buf
  let i = cap
  // Back off over continuation bytes (10xxxxxx) to find the lead byte.
  while (i > 0 && (buf[i - 1] & 0xc0) === 0x80) i--
  if (i === 0) return Buffer.alloc(0)
  const lead = buf[i - 1]
  if (lead & 0x80) {
    let seqLen = 1
    if ((lead & 0xe0) === 0xc0) seqLen = 2
    else if ((lead & 0xf0) === 0xe0) seqLen = 3
    else if ((lead & 0xf8) === 0xf0) seqLen = 4
    // Drop the lead byte too if its full sequence didn't fit.
    if (i - 1 + seqLen > cap) i--
  }
  return buf.subarray(0, i)
}

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
    if (ch === "#" && (idx === 0 || /\s/.test(value[idx - 1]))) {
      return value.slice(0, idx)
    }
  }
  return value
}

function unquoteYaml(s) {
  if (s.length >= 2 && s[0] === s[s.length - 1] && (s[0] === '"' || s[0] === "'")) {
    return s.slice(1, -1)
  }
  return s
}

/**
 * Line-based parser for ONLY the `context_injection:` block of
 * `.trellis/config.yaml`. Not a general YAML parser — mirrors
 * `common.config.get_context_injection_limits()` semantics for this
 * section only (missing keys keep the default; invalid/negative values
 * fall back to the default for that key).
 */
export function readContextInjectionLimits(repoRoot) {
  const limits = { ...DEFAULT_CONTEXT_INJECTION_LIMITS }
  let text = null
  try {
    text = readFileSync(join(repoRoot, ".trellis", "config.yaml"), "utf-8")
  } catch {
    return limits
  }
  if (!text) return limits

  let inSection = false
  let sectionIndent = -1
  for (const rawLine of text.split(/\r?\n/)) {
    const trimmed = rawLine.trim()
    if (!inSection) {
      if (/^context_injection\s*:\s*(#.*)?$/.test(trimmed)) {
        inSection = true
        sectionIndent = rawLine.length - rawLine.trimStart().length
      }
      continue
    }
    if (!trimmed || trimmed.startsWith("#")) continue
    const indent = rawLine.length - rawLine.trimStart().length
    if (indent <= sectionIndent) break
    const m = trimmed.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$/)
    if (!m) continue
    const key = m[1]
    if (!(key in limits)) continue
    const raw = unquoteYaml(stripInlineComment(m[2]).trim()).trim()
    if (!/^-?\d+$/.test(raw) || parseInt(raw, 10) < 0) {
      debugLog("context", `invalid context_injection.${key} value: ${raw}; using default ${limits[key]}`)
      continue
    }
    limits[key] = parseInt(raw, 10)
  }
  return limits
}

/** Tracks the running total of bytes emitted into the sub-agent context. */
export class ContextBudget {
  constructor(maxTotalBytes) {
    this.maxTotalBytes = maxTotalBytes
    this.used = 0
  }

  hasRoom(size) {
    if (this.maxTotalBytes <= 0) return true
    return this.used + size <= this.maxTotalBytes
  }

  add(size) {
    this.used += size
  }
}

export function truncateNotice(path, cap) {
  return `\n[Trellis: truncated at ${cap} bytes — read ${path} for the full content]`
}

function isBinaryContent(data) {
  return data.includes(0) || !isUtf8(data)
}

function binaryNotice(path, size, reason) {
  return `[Trellis: not inlined (binary file) — ${path} (${size} bytes): ${reason}]`
}

function indexNotice(path, size, reason) {
  return `[Trellis: not inlined (total context limit reached) — ${path} (${size} bytes): ${reason}]`
}

/**
 * Return an inlined `=== header ===` block, or degrade to an index
 * notice once the total context budget is exhausted.
 */
function budgetedBlock(budget, header, plainPath, content, reason, sizeForIndex) {
  const block = `=== ${header} ===\n${content}`
  const blockBytes = Buffer.byteLength(block, "utf-8")
  if (!budget.hasRoom(blockBytes)) {
    const notice = indexNotice(plainPath, sizeForIndex, reason)
    budget.add(Buffer.byteLength(notice, "utf-8"))
    return notice
  }
  budget.add(blockBytes)
  return block
}

/** Read raw file bytes, return null if file doesn't exist. */
function readFileBytes(basePath, filePath) {
  const fullPath = isAbsolute(filePath) ? filePath : join(basePath, filePath)
  try {
    if (!statSync(fullPath).isFile()) return null
  } catch {
    return null
  }
  try {
    return readFileSync(fullPath)
  } catch {
    return null
  }
}

/** Read a JSONL-referenced file, apply the per-file cap, then budget it. */
export function materializeFile(basePath, filePath, reason, limits, budget) {
  const data = readFileBytes(basePath, filePath)
  if (data === null) return null

  const size = data.length
  if (isBinaryContent(data)) {
    const notice = binaryNotice(filePath, size, reason)
    budget.add(Buffer.byteLength(notice, "utf-8"))
    return notice
  }
  const cap = limits.max_file_bytes
  const truncated = truncateUtf8(data, cap)
  let content = truncated.toString("utf-8")
  if (truncated.length < size) content += truncateNotice(filePath, cap)

  return budgetedBlock(budget, filePath, filePath, content, reason, size)
}

/**
 * Read all .md files in a directory, applying the same per-file and
 * total caps as a single-file JSONL entry.
 */
export function materializeDirectory(basePath, dirPath, reason, limits, budget, maxFiles = 20) {
  const blocks = []
  const fullPath = isAbsolute(dirPath) ? dirPath : join(basePath, dirPath)

  let files
  try {
    if (!statSync(fullPath).isDirectory()) return blocks
    files = readdirSync(fullPath)
      .filter(f => f.endsWith(".md") && statSync(join(fullPath, f)).isFile())
      .sort()
  } catch {
    return blocks
  }

  for (const filename of files.slice(0, maxFiles)) {
    const relative = dirPath.split(sep).join("/") + "/" + filename
    const block = materializeFile(basePath, relative, reason, limits, budget)
    if (block) blocks.push(block)
  }
  return blocks
}

/**
 * Read a task artifact (prd/design/implement.md), apply the per-artifact
 * cap, then budget it.
 */
export function materializeArtifact(basePath, filePath, headerLabel, reason, limits, budget) {
  const data = readFileBytes(basePath, filePath)
  if (data === null) return null

  const size = data.length
  const cap = limits.max_artifact_bytes
  const truncated = truncateUtf8(data, cap)
  let content = truncated.toString("utf-8")
  if (truncated.length < size) content += truncateNotice(filePath, cap)

  return budgetedBlock(budget, headerLabel, filePath, content, reason, size)
}

// ============================================================
// Trellis Context Manager
// ============================================================

export class TrellisContext {
  constructor(directory) {
    this.directory = directory
    debugLog("context", "TrellisContext initialized", { directory })
  }

  // ----------------------------------------------------------
  // Trellis project detection
  // ----------------------------------------------------------

  isTrellisProject() {
    return existsSync(join(this.directory, ".trellis"))
  }

  /**
   * Resolve the session context key with the same precedence as Python
   * `active_task.resolve_context_key(..., platform="opencode")`:
   *   1. TRELLIS_CONTEXT_ID explicit override
   *   2. platform-input session / conversation / transcript ids
   *   3. OPENCODE_SESSION_ID / OPENCODE_SESSIONID / OPENCODE_RUN_ID env keys
   */
  getContextKey(platformInput = null, env = process.env) {
    const override = stringValue(env.TRELLIS_CONTEXT_ID)
    if (override) {
      return sanitizeKey(override) || hashValue(override)
    }

    const input = platformInput && typeof platformInput === "object" ? platformInput : null
    if (input) {
      const sessionID = lookupString(input, ["session_id", "sessionId", "sessionID"])
      if (sessionID) return buildContextKey("opencode", "session", sessionID)

      const conversationID = lookupString(input, ["conversation_id", "conversationId", "conversationID"])
      if (conversationID) return buildContextKey("opencode", "conversation", conversationID)

      const transcriptPath = lookupString(input, ["transcript_path", "transcriptPath", "transcript"])
      if (transcriptPath) return buildContextKey("opencode", "transcript", transcriptPath)
    }

    for (const key of OPENCODE_ENV_SESSION_KEYS) {
      const value = stringValue(env[key])
      if (value) return buildContextKey("opencode", "session", value)
    }

    return null
  }

  readContext(contextKey) {
    try {
      const contextPath = join(this.directory, ".trellis", ".runtime", "sessions", `${contextKey}.json`)
      if (!existsSync(contextPath)) return null
      return JSON.parse(readFileSync(contextPath, "utf-8"))
    } catch {
      return null
    }
  }

  listSessionFiles() {
    const sessionsDir = join(this.directory, ".trellis", ".runtime", "sessions")
    if (!existsSync(sessionsDir)) return []
    try {
      return readdirSync(sessionsDir).filter(name => name.endsWith(".json")).sort()
    } catch {
      return []
    }
  }

  // ----------------------------------------------------------
  // Task-ref helpers
  // ----------------------------------------------------------

  normalizeTaskRef(taskRef) {
    if (!taskRef) {
      return ""
    }

    if (isAbsolute(taskRef)) {
      return taskRef.trim()
    }

    let normalized = taskRef.trim().replace(/\\/g, "/")
    while (normalized.startsWith("./")) {
      normalized = normalized.slice(2)
    }

    if (normalized.startsWith("tasks/")) {
      return `.trellis/${normalized}`
    }

    return normalized
  }

  resolveTaskDir(taskRef) {
    const normalized = this.normalizeTaskRef(taskRef)
    if (!normalized) {
      return null
    }

    if (isAbsolute(normalized)) {
      return normalized
    }

    if (normalized.startsWith(".trellis/")) {
      return join(this.directory, normalized)
    }

    return join(this.directory, ".trellis", "tasks", normalized)
  }

  /** True when `absPath` resolves inside the workspace (repo root). */
  isWithinWorkspace(absPath) {
    const rel = relativePath(resolvePath(this.directory), resolvePath(absPath))
    return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel))
  }

  /**
   * Resolve a task ref to an existing task directory inside the workspace.
   * Returns { taskPath, taskDir } or null when the ref is missing, stale,
   * outside the workspace, or not a directory.
   */
  resolveExistingTaskDir(taskRef) {
    const normalized = this.normalizeTaskRef(taskRef)
    if (!normalized) return null
    const taskDir = this.resolveTaskDir(normalized)
    if (!taskDir) return null
    if (!this.isWithinWorkspace(taskDir)) return null
    try {
      if (!statSync(taskDir).isDirectory()) return null
    } catch {
      return null
    }
    return { taskPath: normalized, taskDir }
  }

  // ----------------------------------------------------------
  // Fail-closed task resolution (mirrors Python resolve_active_task)
  // ----------------------------------------------------------

  /**
   * Main-session resolution. Never borrows another window's task:
   *   - exact context key with pointer   -> { taskPath, source: "session:<key>" }
   *   - exact context key without pointer -> authoritative no_task
   *   - no context key, session files exist -> { source: "ambiguous" }
   *   - no context key, no session files   -> { source: "none" }
   */
  resolveMainTask(platformInput = null, env = process.env) {
    const contextKey = this.getContextKey(platformInput, env)
    if (contextKey) {
      const context = this.readContext(contextKey)
      const taskRef = this.normalizeTaskRef(context?.current_task || "")
      if (taskRef) {
        const taskDir = this.resolveTaskDir(taskRef)
        return {
          taskPath: taskRef,
          source: `session:${contextKey}`,
          contextKey,
          stale: !taskDir || !existsSync(taskDir),
        }
      }
      return { taskPath: null, source: "none", contextKey, stale: false }
    }

    if (this.listSessionFiles().length > 0) {
      return { taskPath: null, source: "ambiguous", contextKey: null, stale: false }
    }
    return { taskPath: null, source: "none", contextKey: null, stale: false }
  }

  /**
   * Single-session compatibility fallback — restricted by design to Task
   * sub-agent dispatch, never for the main session. Only when exactly one
   * session runtime file exists and its pointer resolves to an existing
   * task directory inside the workspace.
   */
  resolveSingleSessionFallback() {
    const files = this.listSessionFiles()
    if (files.length !== 1) return null

    const sessionFile = join(this.directory, ".trellis", ".runtime", "sessions", files[0])
    let context
    try {
      context = JSON.parse(readFileSync(sessionFile, "utf-8"))
    } catch {
      return null
    }
    const taskRef = this.normalizeTaskRef(context?.current_task || "")
    if (!taskRef) return null

    const resolved = this.resolveExistingTaskDir(taskRef)
    if (!resolved) return null
    const fallbackKey = files[0].replace(/\.json$/, "")
    return { taskPath: resolved.taskPath, source: `session-fallback:${fallbackKey}`, stale: false }
  }

  /**
   * Task sub-agent resolution order (template contract):
   *   1. exact session pointer carried by the parent call event / env keys;
   *   2. first valid `Active task: <path>` line in the dispatch prompt
   *      (must resolve to an existing in-workspace task directory);
   *   3. restricted single-session fallback (exactly one session file).
   * Returns { taskPath, source } or null — callers fail closed for agents
   * that require a task; never borrow another window's task.
   */
  resolveTaskForSubagent(platformInput = null, promptText = "", env = process.env) {
    const contextKey = this.getContextKey(platformInput, env)
    if (contextKey) {
      const context = this.readContext(contextKey)
      const taskRef = this.normalizeTaskRef(context?.current_task || "")
      if (taskRef) {
        return { taskPath: taskRef, source: `session:${contextKey}` }
      }
    }

    const hint = extractFirstActiveTaskHint(promptText)
    if (hint) {
      const resolved = this.resolveExistingTaskDir(hint)
      if (resolved) {
        debugLog("context", "Resolved task from Active task hint:", resolved.taskPath)
        return { taskPath: resolved.taskPath, source: "prompt-hint" }
      }
      debugLog("context", "Ignored Active task hint (not an existing in-workspace task dir):", hint)
    }

    const fallback = this.resolveSingleSessionFallback()
    if (fallback) {
      debugLog("context", "Resolved task via single-session fallback:", fallback.taskPath, "source:", fallback.source)
      return { taskPath: fallback.taskPath, source: fallback.source }
    }

    return null
  }

  // ----------------------------------------------------------
  // File reading utilities
  // ----------------------------------------------------------

  readFile(filePath) {
    try {
      if (existsSync(filePath)) {
        return readFileSync(filePath, "utf-8")
      }
    } catch {
      // Ignore read errors
    }
    return null
  }

  readProjectFile(relativePathArg) {
    return this.readFile(join(this.directory, relativePathArg))
  }

  // ----------------------------------------------------------
  // JSONL reading
  // ----------------------------------------------------------

  /**
   * Read a JSONL file and materialize referenced files/directories into
   * context blocks, applying per-file caps and the shared total budget.
   * Mirrors Python `_materialize_jsonl_entries`:
   *   {"file": "path/to/file.md", "reason": "..."}
   *   {"file": "path/to/dir/", "type": "directory", "reason": "..."}
   *   {"_example": "..."}  seed row — skipped (no `file` field)
   * Missing referenced files are skipped silently.
   */
  readJsonlWithFiles(jsonlPath, limits, budget) {
    const blocks = []
    const content = this.readFile(jsonlPath)
    if (!content) return blocks

    for (const line of content.split("\n")) {
      if (!line.trim()) continue
      try {
        const item = JSON.parse(line)
        const file = item.file || item.path
        const entryType = item.type || "file"
        const reason = item.reason || "-"

        if (!file) continue

        if (entryType === "directory") {
          blocks.push(...materializeDirectory(this.directory, file, reason, limits, budget))
        } else {
          const block = materializeFile(this.directory, file, reason, limits, budget)
          if (block) blocks.push(block)
        }
      } catch {
        // Ignore parse errors for individual lines
      }
    }
    return blocks
  }

  buildContextFromEntries(blocks) {
    return blocks.join("\n\n")
  }
}

// ============================================================
// Active-task prompt hint
// ============================================================

// Match `Active task: <path>` lines in the dispatch prompt. The path may
// contain spaces (Windows workspaces), so capture to end of line.
const ACTIVE_TASK_HINT_RE = /^[ \t]*Active task:[ \t]*(.+?)[ \t]*$/gim

/**
 * Return the first `Active task: <path>` candidate in the prompt text, or
 * null. Validation (exists + inside workspace) happens in
 * `TrellisContext.resolveTaskForSubagent` via `resolveExistingTaskDir`.
 */
export function extractFirstActiveTaskHint(prompt) {
  if (typeof prompt !== "string" || !prompt) return null
  for (const match of prompt.matchAll(ACTIVE_TASK_HINT_RE)) {
    const candidate = (match[1] || "").trim()
    if (candidate) return candidate
  }
  return null
}

// ============================================================
// Context Collector (for session deduplication)
// ============================================================

class ContextCollector {
  constructor() {
    this.processed = new Set()
  }

  markProcessed(sessionID) {
    this.processed.add(sessionID)
  }

  isProcessed(sessionID) {
    return this.processed.has(sessionID)
  }

  clear(sessionID) {
    this.processed.delete(sessionID)
  }
}

// Singleton instance
export const contextCollector = new ContextCollector()
