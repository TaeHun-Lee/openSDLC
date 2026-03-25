import { useQuery } from "@tanstack/react-query"
import { api } from "../client"
import type { ProjectInfo, ProjectDetail, ProjectUsage } from "../types"

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.get<ProjectInfo[]>("/projects"),
  })
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId],
    queryFn: () => api.get<ProjectDetail>(`/projects/${projectId}`),
    enabled: !!projectId,
  })
}

export function useProjectUsage(projectId: string) {
  return useQuery({
    queryKey: ["projects", projectId, "usage"],
    queryFn: () => api.get<ProjectUsage>(`/projects/${projectId}/usage`),
    enabled: !!projectId,
  })
}
