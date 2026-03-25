import { create } from "zustand"

interface SSEState {
  status: "idle" | "running" | "completed" | "failed" | "cancelled"
  currentIteration: number | null
  currentStep: number | null
  currentAgent: string | null
  stepsTotal: number | null
  error: string | null
  lastEventId: number
  setStatus: (status: SSEState["status"]) => void
  setCurrentStep: (step: number, agent: string) => void
  setCurrentIteration: (iteration: number) => void
  setStepsTotal: (total: number) => void
  setError: (error: string | null) => void
  setLastEventId: (id: number) => void
  reset: () => void
}

const initialState = {
  status: "idle" as const,
  currentIteration: null,
  currentStep: null,
  currentAgent: null,
  stepsTotal: null,
  error: null,
  lastEventId: 0,
}

export const useSSEStore = create<SSEState>()((set) => ({
  ...initialState,
  setStatus: (status) => set({ status }),
  setCurrentStep: (currentStep, currentAgent) => set({ currentStep, currentAgent }),
  setCurrentIteration: (currentIteration) => set({ currentIteration }),
  setStepsTotal: (stepsTotal) => set({ stepsTotal }),
  setError: (error) => set({ error }),
  setLastEventId: (lastEventId) => set({ lastEventId }),
  reset: () => set(initialState),
}))
