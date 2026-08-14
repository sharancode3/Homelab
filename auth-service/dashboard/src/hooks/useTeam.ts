import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { ProjectMember } from '@/lib/types'
import { useProject } from '@/contexts/ProjectContext'

export function useTeamMembers() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['members', activeProjectId],
    queryFn: async (): Promise<ProjectMember[]> => {
      if (!activeProjectId) return []
      const { data } = await api.get(`/baas/projects/${activeProjectId}/members`)
      return data
    },
    enabled: !!activeProjectId
  })
}

export function useInviteMember() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async ({ email, role }: { email: string, role: string }) => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/members`, { email, role })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', activeProjectId] })
    }
  })
}

export function useUpdateMemberRole() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async ({ userId, role }: { userId: string, role: string }) => {
      const { data } = await api.put(`/baas/projects/${activeProjectId}/members/${userId}`, { role })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', activeProjectId] })
    }
  })
}

export function useRemoveMember() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (userId: string) => {
      await api.delete(`/baas/projects/${activeProjectId}/members/${userId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['members', activeProjectId] })
    }
  })
}
