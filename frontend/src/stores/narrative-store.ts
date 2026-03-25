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
  }
}

export const useNarrativeStore = create<NarrativeState>()((set) => ({
  messages: [],
  isResume: false,
  addEvent: (event) =>
    set((state) => ({
      messages: [...state.messages, eventToMessage(event)],
      isResume: event.event_type === "pipeline_started" && event.message?.includes("resume")
        ? true
        : state.isResume,
    })),
  loadFromReplay: (events) =>
    set({
      messages: events.map(eventToMessage),
      isResume: events.some(
        (e) => e.event_type === "pipeline_started" && e.message?.includes("resume"),
      ),
    }),
  clear: () => set({ messages: [], isResume: false }),
}))
