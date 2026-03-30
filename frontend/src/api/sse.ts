import type { EventInfo } from "./types"

/**
 * Parse a ReadableStream of SSE text/event-stream into an async generator of EventInfo.
 *
 * The backend SSE payload format is:
 *   {"id": N, "event_type": "...", "data": {"agent_name": "...", "message": "...", ...}, "timestamp": T}
 *
 * This parser normalizes it to the flat EventInfo shape used throughout the frontend:
 *   {"id": N, "event_type": "...", "agent_name": "...", "message": "...", "created_at": T, ...}
 */
export async function* parseSSEStream(
  body: ReadableStream<Uint8Array>,
  onChunk?: () => void,
): AsyncGenerator<EventInfo> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  // Accumulate fields for current SSE event
  let currentId: number | undefined
  let currentData = ""

  function* flushEvent(): Generator<EventInfo> {
    if (!currentData) {
      currentId = undefined
      currentData = ""
      return
    }
    try {
      const raw = JSON.parse(currentData) as Record<string, unknown>
      const event = normalizeSSEPayload(raw, currentId)
      if (event) yield event
    } catch {
      // skip malformed JSON
    }
    currentId = undefined
    currentData = ""
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      onChunk?.()
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""

      for (const line of lines) {
        const trimmed = line.trim()

        if (!trimmed) {
          yield* flushEvent()
          continue
        }

        if (trimmed.startsWith(":")) continue

        if (trimmed.startsWith("id:")) {
          const val = trimmed.slice(3).trim()
          const parsed = parseInt(val, 10)
          if (!isNaN(parsed)) currentId = parsed
        } else if (trimmed.startsWith("data:")) {
          const val = trimmed.slice(5).trim()
          currentData = currentData ? currentData + "\n" + val : val
        }
      }
    }

    yield* flushEvent()
  } finally {
    reader.releaseLock()
  }
}

/**
 * Normalize a backend SSE payload into the flat EventInfo shape.
 *
 * Backend format: {id, event_type, data: {agent_name, message, ...}, timestamp}
 * Frontend EventInfo: {id, event_type, agent_name, message, iteration_num, created_at, data}
 */
function normalizeSSEPayload(
  raw: Record<string, unknown>,
  sseId?: number,
): EventInfo | null {
  const eventType = raw.event_type as string | undefined
  if (!eventType) return null

  const id = (raw.id as number) ?? sseId ?? 0
  const timestamp = raw.timestamp as number | undefined
  const data = (raw.data ?? {}) as Record<string, unknown>

  return {
    id,
    event_type: eventType,
    agent_name: (data.agent_name as string) ?? (data.agent_id as string) ?? null,
    message: (data.message as string) ?? null,
    iteration_num: (data.iteration_num as number) ?? null,
    created_at: timestamp ?? Date.now() / 1000,
    data,
  }
}
