import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { Table, Column, TableDataResponse } from '@/lib/database.types'
import { useProject } from '@/contexts/ProjectContext'

export function useTables() {
  const { activeProjectId } = useProject()
  
  return useQuery({
    queryKey: ['tables', activeProjectId],
    queryFn: async (): Promise<Table[]> => {
      if (!activeProjectId) return []
      const { data } = await api.get(`/baas/projects/${activeProjectId}/tables`)
      return data
    },
    enabled: !!activeProjectId
  })
}

export function useCreateTable() {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async ({ name, columns }: { name: string, columns: Column[] }) => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/tables`, { name, columns })
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tables', activeProjectId] })
    }
  })
}

export function useTableData(tableName: string, limit: number = 50, offset: number = 0) {
  const { activeProjectId } = useProject()

  return useQuery({
    queryKey: ['tableData', activeProjectId, tableName, limit, offset],
    queryFn: async (): Promise<TableDataResponse> => {
      if (!activeProjectId || !tableName) return { data: [], total: 0, limit, offset }
      const { data } = await api.get(`/baas/projects/${activeProjectId}/data/${tableName}`, {
        params: { limit, offset }
      })
      return data
    },
    enabled: !!activeProjectId && !!tableName
  })
}

export function useInsertRow(tableName: string) {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (rowData: Record<string, any>) => {
      const { data } = await api.post(`/baas/projects/${activeProjectId}/data/${tableName}`, rowData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tableData', activeProjectId, tableName] })
    }
  })
}

export function useUpdateRow(tableName: string) {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async ({ rowId, rowData }: { rowId: string | number, rowData: Record<string, any> }) => {
      const { data } = await api.put(`/baas/projects/${activeProjectId}/data/${tableName}/${rowId}`, rowData)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tableData', activeProjectId, tableName] })
    }
  })
}

export function useDeleteRow(tableName: string) {
  const queryClient = useQueryClient()
  const { activeProjectId } = useProject()

  return useMutation({
    mutationFn: async (rowId: string | number) => {
      // The backend requires the PK ID
      await api.delete(`/baas/projects/${activeProjectId}/data/${tableName}/${rowId}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tableData', activeProjectId, tableName] })
    }
  })
}
