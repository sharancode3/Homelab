import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useProject } from '@/contexts/ProjectContext'
import type { FileMetadata } from '@/lib/storage.types'

export function useStorageFiles() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['storage', activeProjectId],
    queryFn: async (): Promise<FileMetadata[]> => {
      if (!activeProjectId) return []
      const { data } = await api.get(`/baas/projects/${activeProjectId}/storage/`)
      return data
    },
    enabled: !!activeProjectId
  })
}

export function useUploadFile() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async ({ file, onProgress }: { file: File, onProgress?: (progressEvent: any) => void }) => {
      const formData = new FormData()
      formData.append('file', file)

      const { data } = await api.post(`/baas/projects/${activeProjectId}/storage/`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: onProgress
      })
      return data as FileMetadata
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', activeProjectId] })
    }
  })
}

export function useDeleteFile() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (fileId: string) => {
      await api.delete(`/baas/projects/${activeProjectId}/storage/${fileId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['storage', activeProjectId] })
    }
  })
}

export async function downloadFile(activeProjectId: string, fileId: string, filename: string) {
  // We use standard fetch or trigger a window download by fetching a blob
  const response = await api.get(`/baas/projects/${activeProjectId}/storage/${fileId}`, {
    responseType: 'blob'
  })
  
  // Create a temporary link to download the blob
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('href') as unknown as HTMLAnchorElement
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  
  // Cleanup
  link.parentNode?.removeChild(link)
  window.URL.revokeObjectURL(url)
}
