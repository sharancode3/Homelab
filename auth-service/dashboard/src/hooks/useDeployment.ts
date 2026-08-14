import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useProject } from '@/contexts/ProjectContext'
import type { 
  HealthResponse, 
  ProjectStatusResponse, 
  LogsResponse, 
  OperationHistoryResponse,
  DeployRequest,
  BackupRequest,
  RestoreRequest,
  OperationResponse
} from '@/lib/deployment.types'

export function useProjectHealth() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['projectHealth', activeProjectId],
    queryFn: async (): Promise<HealthResponse> => {
      const { data } = await api.get(`/baas/projects/${activeProjectId}/health`)
      return data
    },
    enabled: !!activeProjectId
  })
}

export function useProjectStatus() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['projectStatus', activeProjectId],
    queryFn: async (): Promise<ProjectStatusResponse> => {
      const { data } = await api.get(`/baas/projects/${activeProjectId}/status`)
      return data
    },
    enabled: !!activeProjectId
  })
}

// Bounded polling only while component is mounted
export function useProjectLogs(enabled: boolean = true) {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['projectLogs', activeProjectId],
    queryFn: async (): Promise<LogsResponse> => {
      const { data } = await api.get(`/baas/projects/${activeProjectId}/logs`)
      return data
    },
    enabled: !!activeProjectId && enabled,
    refetchInterval: enabled ? 3000 : false, // Poll every 3 seconds if active
  })
}

export function useOperationHistory() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['projectHistory', activeProjectId],
    queryFn: async (): Promise<OperationHistoryResponse> => {
      const { data } = await api.get(`/baas/projects/${activeProjectId}/history`, { params: { limit: 50 } })
      return data
    },
    enabled: !!activeProjectId
  })
}

export function useDeployProject() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (req: DeployRequest = {}): Promise<OperationResponse> => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/deploy`, req)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectStatus', activeProjectId] })
      queryClient.invalidateQueries({ queryKey: ['projectHistory', activeProjectId] })
    }
  })
}

export function useStopProject() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (): Promise<OperationResponse> => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/stop`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectStatus', activeProjectId] })
      queryClient.invalidateQueries({ queryKey: ['projectHistory', activeProjectId] })
    }
  })
}

export function useRestartProject() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (): Promise<OperationResponse> => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/restart`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectStatus', activeProjectId] })
      queryClient.invalidateQueries({ queryKey: ['projectHistory', activeProjectId] })
    }
  })
}

export function useBackupProject() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (req: BackupRequest = { backup_type: 'full' }): Promise<OperationResponse> => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/backup`, req)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectHistory', activeProjectId] })
    }
  })
}

export function useRestoreProject() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (req: RestoreRequest): Promise<OperationResponse> => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/restore`, req)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projectStatus', activeProjectId] })
      queryClient.invalidateQueries({ queryKey: ['projectHistory', activeProjectId] })
    }
  })
}
