import { create } from "zustand"
import type { EventInfo } from "@/api/types"

export interface NarrativeMessage {
  id: number
  eventType: string
  agentName: string | null
  message: string | null
  iterationNum: number | null
  createdAt: number
  data?: Record<string, unknown>
}

interface NarrativeState {
  messages: NarrativeMessage[]
  isResume: boolean
  addEvent: (event: EventInfo) => void
  loadFromReplay: (events: EventInfo[]) => void
  clear: () => void
}

function eventToMessage(event: EventInfo): NarrativeMessage {
  return {
    id: event.id,
    eventType: event.event_type,
    agentName: event.agent_name,
    message: event.message,
    iterationNum: event.iteration_num,
    createdAt: event.created_at,
    ...(event.data ? { data: event.data } : {}),
  }
}

const MAX_MESSAGES = 2000

export const useNarrativeStore = create<NarrativeState>()((set) => ({
  messages: [],
  isResume: false,
  addEvent: (event) =>
    set((state) => {
      // Prevent duplicate messages by ID (e.g. on SSE reconnect replay)
      if (state.messages.some((m) => m.id === event.id)) return state

      const updated = [...state.messages, eventToMessage(event)]
      return {
        messages: updated.length > MAX_MESSAGES ? updated.slice(-MAX_MESSAGES) : updated,
        isResume: event.event_type === "pipeline_resumed" ? true : state.isResume,
      }
    }),
  loadFromReplay: (events) =>
    set({
      messages: events.map(eventToMessage),
      isResume: events.some((e) => e.event_type === "pipeline_resumed"),
    }),
  clear: () => set({ messages: [], isResume: false }),
}))
