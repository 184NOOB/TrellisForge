/* global process */
/**
 * Trellis Session Start Plugin (OpenCode)
 *
 * Injects the compact TrellisForge SessionStart context when the user sends
 * the first message of a main-session conversation. OpenCode has no dedicated
 * session-start hook, so the first `chat.message` is used and the context is
 * persisted in the message parts (marked with metadata.trellis.sessionStart)
 * for history-based deduplication.
 *
 * Behavior contract (matches the template Python session-start hook family):
 *   - one persistent injection per session; `session.compacted` clears the
 *     in-memory flag and history dedup re-checks, so context can be restored
 *     after compaction;
 *   - Trellis sub-agent turns never receive the main-session SessionStart
 *     (their context comes from inject-subagent-context.js);
 *   - silent skip when hooks are disabled (TRELLIS_HOOKS=0 /
 *     TRELLIS_DISABLE_HOOKS=1), in non-interactive mode
 *     (OPENCODE_NON_INTERACTIVE=1), or when the directory is not a Trellis
 *     project.
 *
 * Plugin export shape: OpenCode 1.2.x iterates every module export and calls
 * it as a plugin factory, so this module exposes exactly one default export.
 */

import { TrellisContext, contextCollector, debugLog, isTrellisSubagent } from "../lib/trellis-context.js"
import {
  buildSessionContext,
  hasPersistedInjectedContext,
  markContextInjected,
} from "../lib/session-utils.js"

export default async ({ directory, client }) => {
  const ctx = new TrellisContext(directory)
  debugLog("session", "Plugin loaded, directory:", directory)

  return {
    event: ({ event }) => {
      try {
        if (event?.type === "session.compacted" && event?.properties?.sessionID) {
          const sessionID = event.properties.sessionID
          contextCollector.clear(sessionID)
          debugLog("session", "Cleared processed flag after compaction for session:", sessionID)
        }
      } catch (error) {
        debugLog(
          "session",
          "Error in event hook:",
          error instanceof Error ? error.message : String(error),
        )
      }
    },

    // chat.message - fires on every user message. Only the first main-session
    // turn is enriched; the injected context persists with the message parts.
    "chat.message": async (input, output) => {
      try {
        const sessionID = input.sessionID
        debugLog("session", "chat.message called, sessionID:", sessionID, "agent:", input.agent || "unknown")

        if (!ctx.isTrellisProject()) return

        // Skip Trellis sub-agent turns — their context comes from the
        // parent's tool.execute.before injection.
        if (isTrellisSubagent(input)) {
          debugLog("session", "Skipping trellis subagent turn:", input.agent)
          return
        }

        if (process.env.TRELLIS_HOOKS === "0" || process.env.TRELLIS_DISABLE_HOOKS === "1") {
          debugLog("session", "Skipping - TRELLIS_HOOKS disabled")
          return
        }

        if (process.env.OPENCODE_NON_INTERACTIVE === "1") {
          debugLog("session", "Skipping - non-interactive mode")
          return
        }

        if (contextCollector.isProcessed(sessionID)) {
          debugLog("session", "Skipping - session already processed")
          return
        }

        if (await hasPersistedInjectedContext(client, ctx.directory, sessionID)) {
          contextCollector.markProcessed(sessionID)
          debugLog("session", "Skipping - session already contains persisted Trellis context")
          return
        }

        const context = buildSessionContext(ctx, input)
        debugLog("session", "Built context, length:", context.length)

        const parts = output?.parts || []
        const textPartIndex = parts.findIndex(
          p => p.type === "text" && p.text !== undefined
        )

        if (textPartIndex !== -1) {
          const originalText = parts[textPartIndex].text || ""
          parts[textPartIndex].text = `${context}\n\n---\n\n${originalText}`
          markContextInjected(parts[textPartIndex])
          debugLog("session", "Injected context into chat.message text part, length:", context.length)
        } else {
          const injectedPart = { type: "text", text: context }
          markContextInjected(injectedPart)
          parts.unshift(injectedPart)
          debugLog("session", "Prepended new text part with context, length:", context.length)
        }

        contextCollector.markProcessed(sessionID)
      } catch (error) {
        debugLog("session", "Error in chat.message:", error.message, error.stack)
      }
    },
  }
}
