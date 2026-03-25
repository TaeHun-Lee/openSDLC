import { useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "../client"
import type { PipelineInfo, CreatePipelineRequest, UpdatePipelineRequest } from "../types"

export function useCreatePipeline() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreatePipelineRequest) =>
      api.post<PipelineInfo>("/pipelines", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] })
    },
  })
}

export function useUpdatePipeline() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ name, body }: { name: string; body: UpdatePipelineRequest }) =>
      api.put<PipelineInfo>(`/pipelines/${name}`, body),
    onSuccess: (_data, { name }) => {
      queryClient.invalidateQueries({ queryKey: ["pipelines", name] })
      queryClient.invalidateQueries({ queryKey: ["pipelines"] })
    },
  })
}

export function useDeletePipeline() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (name: string) =>
      api.delete<void>(`/pipelines/${name}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] })
    },
  })
}
