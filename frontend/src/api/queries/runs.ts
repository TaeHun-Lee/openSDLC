import { useQuery } from "@tanstack/react-query"
import { api } from "../client"
import type { RunSummary, RunDetail, RunArtifacts, RunUsage, ProgressInfo } from "../types"

export function useRuns(projectId?: string) {
  const params = projectId ? `?project_id=${projectId}` : ""
  return useQuery({
    queryKey: ["runs", { projectId }],
    queryFn: () => api.get<RunSummary[]>(`/runs${params}`),
  })
}

export function useRun(runId: string) {
  return useQuery({
    queryKey: ["runs", runId],
    queryFn: () => api.get<RunDetail>(`/runs/${runId}`),
    enabled: !!runId,
  })
}

export function useRunArtifacts(runId: string, iteration?: number) {
  const params = iteration != null ? `?iteration=${iteration}` : ""
  return useQuery({
    queryKey: ["runs", runId, "artifacts", { iteration }],
    queryFn: () => api.get<RunArtifacts>(`/runs/${runId}/artifacts${params}`),
    enabled: !!runId,
  })
}

export function useRunUsage(runId: string) {
  return useQuery({
    queryKey: ["runs", runId, "usage"],
    queryFn: () => api.get<RunUsage>(`/runs/${runId}/usage`),
    enabled: !!runId,
  })
}

export function useRunProgress(runId: string, enabled = false) {
  return useQuery({
    queryKey: ["runs", runId, "progress"],
    queryFn: () => api.get<ProgressInfo>(`/runs/${runId}/progress`),
    enabled: enabled && !!runId,
    refetchInterval: 2_000,
  })
}
