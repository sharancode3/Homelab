import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Project } from '@/lib/types'
import { useProject } from '@/contexts/ProjectContext'

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async (): Promise<Project[]> => {
      const { data } = await api.get('/baas/projects')
      return data
    }
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (name: string) => {
      const { data } = await api.post('/baas/projects', { name })
      return data as Project
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    }
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  const { activeProjectId, setActiveProjectId } = useProject()

  return useMutation({
    mutationFn: async (projectId: string) => {
      await api.delete(`/baas/projects/${projectId}`)
    },
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
      // Purge everything related to this project
      queryClient.removeQueries({ queryKey: ['members', deletedId] })
      queryClient.removeQueries({ queryKey: ['tables', deletedId] })
      if (activeProjectId === deletedId) {
        setActiveProjectId(null)
      }
    }
  })
}
