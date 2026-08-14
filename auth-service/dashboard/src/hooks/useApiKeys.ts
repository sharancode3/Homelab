import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useProject } from '@/contexts/ProjectContext'

export interface ApiKey {
  key_id: string
  name: string
  created_at: string
  last_used_at?: string
  created_by: string
  secret_key?: string // Only present immediately after creation
}

export function useApiKeys() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['apiKeys', activeProjectId],
    queryFn: async (): Promise<ApiKey[]> => {
      if (!activeProjectId) return []
      const { data } = await api.get(`/baas/projects/${activeProjectId}/keys`)
      return data
    },
    enabled: !!activeProjectId
  })
}

export function useCreateApiKey() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (name: string) => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/keys`, { name })
      return data as ApiKey
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys', activeProjectId] })
    }
  })
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (keyId: string) => {
      await api.delete(`/baas/projects/${activeProjectId}/keys/${keyId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apiKeys', activeProjectId] })
    }
  })
}
