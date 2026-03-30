import { useEffect, useRef, useState, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { parseSSEStream } from "@/api/sse"
import { useSSEStore } from "@/stores/sse-store"
import { useNarrativeStore } from "@/stores/narrative-store"
import type { EventInfo } from "@/api/types"

export type ConnectionState = "connected" | "reconnecting" | "disconnected"

const MAX_RECONNECTS = 10
const BASE_RECONNECT_DELAY = 1000
const MAX_RECONNECT_DELAY = 30000
const STALLED_TIMEOUT = 60000 // no data for 60s → consider stalled

export function useSSEStream(runId: string, enabled: boolean) {
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected")
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const abortRef = useRef<AbortController | null>(null)
  const reconnectsRef = useRef(0)
  const lastDataRef = useRef<number>(Date.now())
  const stalledTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  // Track whether the hook is still mounted to prevent reconnect after cleanup
  const mountedRef = useRef(true)
  const queryClient = useQueryClient()

  const sseStore = useSSEStore
  const narrativeStore = useNarrativeStore

  const processEvent = useCallback(
    (event: EventInfo) => {
      const store = sseStore.getState()
      const narrative = narrativeStore.getState()

      store.setLastEventId(event.id)

      // Helper: extract structured data from event.
      // Live SSE events have data in event.data (Record); DB replay events
      // may encode it as a JSON string in event.message.
      const eventData = event.data ?? {}
      const parseMessage = (): Record<string, unknown> => {
        if (event.message) {
          try { return JSON.parse(event.message) } catch { /* not JSON */ }
        }
        return {}
      }

      switch (event.event_type) {
        case "pipeline_started": {
          store.setStatus("running")
          const d = { ...eventData, ...parseMessage() }
          if (d.steps_total) store.setStepsTotal(Number(d.steps_total))
          break
        }
        case "step_started": {
          const d = { ...eventData, ...parseMessage() }
          const stepNum = d.step_num != null ? Number(d.step_num) : 0
          const agentName = (d.agent_name as string) ?? event.agent_name ?? ""
          store.setCurrentStep(stepNum, agentName)
          const iterNum = d.iteration_num != null ? Number(d.iteration_num) : null
          if (iterNum) store.setCurrentIteration(iterNum)
          if (event.iteration_num) store.setCurrentIteration(event.iteration_num)
          break
        }
        case "step_completed": {
          // Invalidate artifacts query on step complete
          queryClient.invalidateQueries({ queryKey: ["runs", runId, "artifacts"] })
          queryClient.invalidateQueries({ queryKey: ["runs", runId] })
          break
        }
        case "pipeline_completed": {
          store.setStatus("completed")
          queryClient.invalidateQueries({ queryKey: ["runs", runId] })
          queryClient.invalidateQueries({ queryKey: ["runs"] })
          break
        }
        case "pipeline_error": {
          const msg = event.message ?? (eventData.message as string) ?? ""
          if (msg.includes("cancelled") || msg.includes("cancel")) {
            store.setStatus("cancelled")
          } else {
            store.setStatus("failed")
          }
          store.setError(msg)
          queryClient.invalidateQueries({ queryKey: ["runs", runId] })
          queryClient.invalidateQueries({ queryKey: ["runs"] })
          break
        }
        // agent_narrative, validation_result, rework_triggered — all go to narrative
        default:
          break
      }

      // Add all events to narrative store
      narrative.addEvent(event)
    },
    [runId, queryClient, sseStore, narrativeStore],
  )

  const connect = useCallback(async () => {
    if (!runId || !enabled || !mountedRef.current) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const lastId = sseStore.getState().lastEventId
    const apiKey = localStorage.getItem("opensdlc_api_key") || ""
    // null = never received any event → omit param (backend defaults to 0 = start)
    // number = resume from this index
    const url = lastId != null
      ? `/api/runs/${runId}/events?last_event_id=${lastId}`
      : `/api/runs/${runId}/events`
    const headers: Record<string, string> = {
      Accept: "text/event-stream",
    }
    if (apiKey) headers["X-API-Key"] = apiKey

    try {
      const response = await fetch(url, { headers, signal: controller.signal })

      // Client errors (4xx) are not recoverable — do not retry
      if (response.status >= 400 && response.status < 500) {
        const body = await response.text()
        console.error(`SSE request failed with ${response.status}:`, body)
        sseStore.getState().setError(`Request error: ${response.status}`)
        setConnectionState("disconnected")
        return
      }

      const contentType = response.headers.get("Content-Type") ?? ""

      if (contentType.includes("text/event-stream")) {
        // Live SSE stream
        setConnectionState("connected")
        reconnectsRef.current = 0
        setReconnectAttempt(0)
        lastDataRef.current = Date.now()

        // Start stalled connection detection
        stalledTimerRef.current = setInterval(() => {
          if (Date.now() - lastDataRef.current > STALLED_TIMEOUT) {
            // No data received for too long — force reconnect
            controller.abort()
          }
        }, 10000)

        if (!response.body) return

        try {
          // onChunk callback: update lastDataRef whenever raw bytes arrive
          // (including SSE heartbeats that don't yield events). This prevents
          // the stalled timer from firing during long LLM calls.
          for await (const event of parseSSEStream(response.body, () => {
            lastDataRef.current = Date.now()
          })) {
            if (controller.signal.aborted) break
            processEvent(event)
          }
        } finally {
          if (stalledTimerRef.current) {
            clearInterval(stalledTimerRef.current)
            stalledTimerRef.current = null
          }
        }

        // Stream ended naturally (run completed/cancelled/failed)
        setConnectionState("disconnected")
      } else {
        // JSON replay for completed runs
        const events: EventInfo[] = await response.json()
        narrativeStore.getState().loadFromReplay(events)

        // Update SSE store from final events
        for (const event of events) {
          if (event.event_type === "pipeline_completed") {
            sseStore.getState().setStatus("completed")
          } else if (event.event_type === "pipeline_error") {
            const msg = event.message ?? ""
            if (msg.includes("cancelled")) {
              sseStore.getState().setStatus("cancelled")
            } else {
              sseStore.getState().setStatus("failed")
            }
            sseStore.getState().setError(msg)
          }
        }

        setConnectionState("disconnected")
        return // No reconnection needed for completed runs
      }
    } catch (err) {
      if (!mountedRef.current) return
      setConnectionState("disconnected")
    }

    // Reconnect if still active and hook is still mounted
    if (!mountedRef.current) return
    const currentStatus = sseStore.getState().status
    if (
      currentStatus === "running" &&
      reconnectsRef.current < MAX_RECONNECTS
    ) {
      reconnectsRef.current++
      setReconnectAttempt(reconnectsRef.current)
      setConnectionState("reconnecting")
      // Exponential backoff with jitter
      const delay = Math.min(
        BASE_RECONNECT_DELAY * 2 ** (reconnectsRef.current - 1) + Math.random() * 500,
        MAX_RECONNECT_DELAY,
      )
      await new Promise((r) => setTimeout(r, delay))
      if (mountedRef.current) {
        connect()
      }
    } else if (reconnectsRef.current >= MAX_RECONNECTS) {
      setConnectionState("disconnected")
    }
  }, [runId, enabled, processEvent, sseStore, narrativeStore])

  useEffect(() => {
    if (!enabled || !runId) return

    mountedRef.current = true

    // Reset stores on new connection
    sseStore.getState().reset()
    narrativeStore.getState().clear()

    connect()

    return () => {
      mountedRef.current = false
      abortRef.current?.abort()
      if (stalledTimerRef.current) {
        clearInterval(stalledTimerRef.current)
        stalledTimerRef.current = null
      }
    }
  }, [runId, enabled, connect, sseStore, narrativeStore])

  // Reconnect on tab visibility change
  useEffect(() => {
    if (!enabled || !runId) return

    function handleVisibility() {
      if (
        document.visibilityState === "visible" &&
        sseStore.getState().status === "running"
      ) {
        reconnectsRef.current = 0
        connect()
      }
    }

    document.addEventListener("visibilitychange", handleVisibility)
    return () => document.removeEventListener("visibilitychange", handleVisibility)
  }, [runId, enabled, connect, sseStore])

  const manualReconnect = useCallback(() => {
    reconnectsRef.current = 0
    setReconnectAttempt(0)
    connect()
  }, [connect])

  return { connectionState, reconnectAttempt, manualReconnect }
}
