import { useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { useProject } from "@/contexts/ProjectContext"
import { useTableData, useInsertRow, useDeleteRow, useUpdateRow } from "@/hooks/useDatabase"
import type { Table } from "@/lib/database.types"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Plus, Trash2, Edit, AlertCircle, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react"

export function TableDetail() {
  const { tableName } = useParams<{ tableName: string }>()
  const navigate = useNavigate()
  const { activeProjectId } = useProject()
  
  const [page, setPage] = useState(0)
  const pageSize = 50

  // Fetch schema
  const { data: tableSchema, isLoading: isSchemaLoading, isError: isSchemaError } = useQuery({
    queryKey: ['tableSchema', activeProjectId, tableName],
    queryFn: async (): Promise<Table> => {
      const { data } = await api.get(`/baas/projects/${activeProjectId}/tables/${tableName}`)
      return data
    },
    enabled: !!activeProjectId && !!tableName
  })

  // Fetch data
  const { data: tableData, isLoading: isDataLoading, isError: isDataError, refetch } = useTableData(tableName!, pageSize, page * pageSize)

  const insertRow = useInsertRow(tableName!)
  const updateRow = useUpdateRow(tableName!)
  const deleteRow = useDeleteRow(tableName!)

  const [isInsertOpen, setIsInsertOpen] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [editRowId, setEditRowId] = useState<string | number | null>(null)
  const [insertData, setInsertData] = useState<Record<string, string>>({})
  const [actionError, setActionError] = useState<string | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const handleInsert = async (e: React.FormEvent) => {
    e.preventDefault()
    setActionError(null)

    // Convert values appropriately
    const parsedData: Record<string, any> = {}
    tableSchema?.columns?.forEach(col => {
      const val = insertData[col.name]
      if (val !== undefined && val !== "") {
        if (col.type === 'INTEGER') parsedData[col.name] = parseInt(val, 10)
        else if (col.type === 'REAL') parsedData[col.name] = parseFloat(val)
        else if (col.type === 'BOOLEAN') parsedData[col.name] = val === 'true'
        else if (col.type === 'JSON') {
          try {
            parsedData[col.name] = JSON.parse(val)
          } catch (e) {
            parsedData[col.name] = val
          }
        }
        else parsedData[col.name] = val
      }
    })

    try {
      if (isEditMode && editRowId !== null) {
        await updateRow.mutateAsync({ rowId: editRowId, rowData: parsedData })
      } else {
        await insertRow.mutateAsync(parsedData)
      }
      setIsInsertOpen(false)
      setInsertData({})
      setIsEditMode(false)
      setEditRowId(null)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setActionError("Permission denied.")
      } else {
        setActionError(err.response?.data?.detail || "Failed to save row.")
      }
    }
  }

  const handleDelete = async () => {
    if (!deleteConfirmId) return
    setActionError(null)
    try {
      await deleteRow.mutateAsync(deleteConfirmId)
      setDeleteConfirmId(null)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setActionError("Permission denied.")
      } else {
        setActionError(err.response?.data?.detail || "Failed to delete row.")
      }
    }
  }

  const handleNextPage = () => {
    if (tableData && tableData.data.length === pageSize) {
      setPage(p => p + 1)
    }
  }

  const handlePrevPage = () => {
    if (page > 0) setPage(p => p - 1)
  }

  if (isSchemaLoading) {
    return <div className="p-8 text-center text-muted-foreground animate-pulse">Loading table schema...</div>
  }

  if (isSchemaError || !tableSchema) {
    return (
      <div className="bg-destructive/15 text-destructive p-4 rounded-md flex items-center gap-2">
        <AlertCircle className="h-4 w-4" />
        Failed to load table schema.
      </div>
    )
  }

  const columns = tableSchema.columns || []
  const pkCol = columns.find(c => c.is_primary_key)?.name || columns[0]?.name

  return (
    <div className="space-y-4 max-w-full overflow-hidden flex flex-col h-[calc(100vh-6rem)]">
      <div className="flex items-center gap-4 shrink-0">
        <Button variant="outline" size="icon" onClick={() => navigate('/database')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h2 className="text-xl font-bold tracking-tight">{tableName}</h2>
          <p className="text-sm text-muted-foreground">{columns.length} columns defined</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isDataLoading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isDataLoading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button size="sm" onClick={() => {
            setInsertData({})
            setIsEditMode(false)
            setEditRowId(null)
            setIsInsertOpen(true)
          }}>
            <Plus className="mr-2 h-4 w-4" /> Insert Row
          </Button>
        </div>
      </div>

      <Card className="flex-1 flex flex-col min-h-0 overflow-hidden border-border rounded-lg shadow-sm">
        <div className="overflow-auto flex-1 relative bg-background">
          {isDataLoading && (
            <div className="absolute inset-0 bg-background/50 z-10 flex items-center justify-center">
              <div className="animate-pulse font-medium text-muted-foreground">Loading data...</div>
            </div>
          )}
          {isDataError ? (
             <div className="p-4 text-destructive flex items-center justify-center h-full">
               Failed to load data rows.
             </div>
          ) : (
            <table className="w-full text-sm text-left border-collapse">
              <thead className="bg-muted/50 sticky top-0 z-20 shadow-sm border-b">
                <tr>
                  {columns.map(col => (
                    <th key={col.name} className="px-4 py-2 font-medium text-muted-foreground border-r last:border-r-0 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {col.name}
                        {col.is_primary_key && <span className="text-[10px] uppercase bg-primary/20 text-primary px-1 rounded">PK</span>}
                        <span className="text-[10px] text-muted-foreground">{col.type}</span>
                      </div>
                    </th>
                  ))}
                  <th className="px-4 py-2 w-16 sticky right-0 bg-muted/50 border-l shadow-sm text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {tableData?.data.map((row, i) => {
                  const rId = pkCol ? row[pkCol] : i
                  return (
                  <tr key={rId} className="hover:bg-muted/30 transition-colors">
                    {columns.map(col => {
                      const val = row[col.name]
                      const isNull = val === null || val === undefined
                      return (
                        <td key={col.name} className="px-4 py-1.5 border-r last:border-r-0 max-w-[300px] truncate">
                          {isNull ? (
                            <span className="text-muted-foreground italic text-xs">null</span>
                          ) : (
                            <span className="truncate" title={String(val)}>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                          )}
                        </td>
                      )
                    })}
                    <td className="px-2 py-1 sticky right-0 bg-background border-l text-center shadow-sm">
                      <div className="flex items-center justify-center gap-1">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-6 w-6 text-muted-foreground hover:text-primary"
                          onClick={() => {
                            if (!pkCol) return
                            setEditRowId(rId)
                            setIsEditMode(true)
                            // convert all vals to string for input
                            const mapped: Record<string, string> = {}
                            for (const c of columns) {
                              const v = row[c.name]
                              if (v !== null && v !== undefined) {
                                mapped[c.name] = typeof v === 'object' ? JSON.stringify(v) : String(v)
                              }
                            }
                            setInsertData(mapped)
                            setIsInsertOpen(true)
                          }}
                          disabled={!pkCol}
                          title={!pkCol ? "Cannot edit without PK" : "Edit row"}
                        >
                          <Edit className="h-3 w-3" />
                        </Button>
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          className="h-6 w-6 text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => setDeleteConfirmId(rId)}
                          disabled={!pkCol}
                          title={!pkCol ? "Cannot delete row without PK" : "Delete row"}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                  )
                })}
                {tableData?.data.length === 0 && (
                  <tr>
                    <td colSpan={columns.length + 1} className="px-4 py-12 text-center text-muted-foreground bg-muted/10">
                      No rows found in this table.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
        
        {/* Pagination Bar */}
        <div className="flex items-center justify-between px-4 py-2 border-t bg-muted/20 shrink-0">
          <div className="text-xs text-muted-foreground">
            Showing rows {page * pageSize + 1} - {page * pageSize + (tableData?.data.length || 0)}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handlePrevPage} disabled={page === 0}>
              <ChevronLeft className="h-4 w-4 mr-1" /> Prev
            </Button>
            <Button variant="outline" size="sm" onClick={handleNextPage} disabled={!tableData || tableData.data.length < pageSize}>
              Next <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </div>
      </Card>

      <Dialog open={isInsertOpen} onOpenChange={setIsInsertOpen}>
        <DialogHeader>
          <DialogTitle>{isEditMode ? "Edit Row" : "Insert Row"}: {tableName}</DialogTitle>
          <DialogDescription>{isEditMode ? "Modify existing record." : "Add a new record to the table."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleInsert} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {actionError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {actionError}
            </div>
          )}
          <div className="space-y-3 pt-2">
            {columns.map(col => (
              <div key={col.name} className="space-y-1">
                <Label className="flex items-center gap-2">
                  {col.name}
                  {col.is_primary_key && <span className="text-[10px] bg-primary/20 text-primary px-1 rounded uppercase">PK</span>}
                  <span className="text-xs text-muted-foreground font-normal">{col.type}</span>
                </Label>
                <Input 
                  value={insertData[col.name] || ""}
                  onChange={e => setInsertData({...insertData, [col.name]: e.target.value})}
                  placeholder={col.is_nullable ? "NULL" : "Required"}
                  required={!col.is_nullable && !col.is_primary_key} // pk usually auto-increments
                  disabled={col.is_primary_key && isEditMode}
                />
              </div>
            ))}
          </div>
          <DialogFooter className="pt-4 border-t">
            <Button type="button" variant="ghost" onClick={() => setIsInsertOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={isEditMode ? updateRow.isPending : insertRow.isPending}>
              {isEditMode ? (updateRow.isPending ? "Saving..." : "Save Changes") : (insertRow.isPending ? "Inserting..." : "Insert")}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      <Dialog open={!!deleteConfirmId} onOpenChange={(o) => !o && setDeleteConfirmId(null)}>
        <DialogHeader>
          <DialogTitle className="text-destructive">Delete Row</DialogTitle>
          <DialogDescription>
            Are you sure you want to delete row with {pkCol} = <strong className="text-foreground">{deleteConfirmId}</strong>?
          </DialogDescription>
        </DialogHeader>
        {actionError && (
          <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {actionError}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => setDeleteConfirmId(null)} disabled={deleteRow.isPending}>Cancel</Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleteRow.isPending}>
            {deleteRow.isPending ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
