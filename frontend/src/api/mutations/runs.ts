import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "../client"
import type { RunCreated, StartRunRequest } from "../types"

export function useStartRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: StartRunRequest) =>
      api.post<RunCreated>("/runs", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    },
  })
}

export function useCancelRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) =>
      api.post<void>(`/runs/${runId}/cancel`),
    onSuccess: (_data, runId) => {
      queryClient.invalidateQueries({ queryKey: ["runs", runId] })
    },
  })
}

export function useResumeRun() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) =>
      api.post<RunCreated>(`/runs/${runId}/resume`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] })
    },
  })
}
