import { useQuery } from "@tanstack/react-query"
import { api } from "../client"
import type { AgentInfo } from "../types"

export function useAgents() {
  return useQuery({
    queryKey: ["agents"],
    queryFn: () => api.get<AgentInfo[]>("/agents"),
  })
}

export function useAgent(agentId: string) {
  return useQuery({
    queryKey: ["agents", agentId],
    queryFn: () => api.get<AgentInfo>(`/agents/${agentId}`),
    enabled: !!agentId,
  })
}
