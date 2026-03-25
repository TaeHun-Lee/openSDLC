import { useQuery } from "@tanstack/react-query"
import { api } from "../client"
import type { PipelineInfo, PipelineListItem, PipelineValidationResult } from "../types"

export function usePipelines() {
  return useQuery({
    queryKey: ["pipelines"],
    queryFn: () => api.get<PipelineListItem[]>("/pipelines"),
  })
}

export function usePipeline(name: string) {
  return useQuery({
    queryKey: ["pipelines", name],
    queryFn: () => api.get<PipelineInfo>(`/pipelines/${name}`),
    enabled: !!name,
  })
}

export function useValidatePipeline(name: string, enabled = false) {
  return useQuery({
    queryKey: ["pipelines", name, "validate"],
    queryFn: () => api.post<PipelineValidationResult>(`/pipelines/${name}/validate`),
    enabled,
  })
}
