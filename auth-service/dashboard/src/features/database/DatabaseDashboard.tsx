import { useState } from "react"
import { useTables, useCreateTable } from "@/hooks/useDatabase"
import { Card, CardHeader, CardTitle, CardDescription, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Database as DatabaseIcon, Plus, Table as TableIcon, ArrowRight, ShieldAlert } from "lucide-react"
import { useNavigate } from "react-router-dom"
import type { Column } from "@/lib/database.types"

export function DatabaseDashboard() {
  const { data: tables, isLoading, isError } = useTables()
  const createTable = useCreateTable()
  const navigate = useNavigate()

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [tableName, setTableName] = useState("")
  const [columns, setColumns] = useState<Column[]>([
    { name: "id", type: "INTEGER", is_primary_key: true, is_nullable: false }
  ])
  const [createError, setCreateError] = useState<string | null>(null)

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)

    if (columns.length === 0) {
      setCreateError("Table must have at least one column.")
      return
    }

    try {
      await createTable.mutateAsync({ name: tableName, columns })
      setIsCreateOpen(false)
      setTableName("")
      setColumns([{ name: "id", type: "INTEGER", is_primary_key: true, is_nullable: false }])
      navigate(`/database/${tableName}`)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setCreateError("Only Admins and Owners can create tables.")
      } else {
        setCreateError(err.response?.data?.detail || "Failed to create table.")
      }
    }
  }

  const addColumn = () => {
    setColumns([...columns, { name: "", type: "TEXT", is_primary_key: false, is_nullable: true }])
  }

  const updateColumn = (index: number, field: keyof Column, value: any) => {
    const newCols = [...columns]
    newCols[index] = { ...newCols[index], [field]: value }
    setColumns(newCols)
  }

  const removeColumn = (index: number) => {
    setColumns(columns.filter((_, i) => i !== index))
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Database</h2>
            <p className="text-muted-foreground">Loading your tables...</p>
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-destructive/15 text-destructive p-4 rounded-md">
        Failed to load database tables. Ensure you have the proper permissions.
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Database</h2>
          <p className="text-muted-foreground">Manage your SQLite tables, schema, and rows.</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" /> New Table
        </Button>
      </div>

      {!tables || tables.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl border-dashed bg-muted/20">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <DatabaseIcon className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No tables found</h3>
          <p className="text-sm text-muted-foreground max-w-sm mb-4">
            You don't have any tables in this project. Create one to start storing structured data.
          </p>
          <Button onClick={() => setIsCreateOpen(true)}>Create Table</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tables.map((table) => (
            <Card key={table.name} className="hover:border-primary/50 transition-colors flex flex-col cursor-pointer group" onClick={() => navigate(`/database/${table.name}`)}>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="h-10 w-10 rounded-md bg-primary/10 flex items-center justify-center text-primary mb-2">
                    <TableIcon className="h-5 w-5" />
                  </div>
                </div>
                <CardTitle className="group-hover:text-primary transition-colors">{table.name}</CardTitle>
                <CardDescription>Schema & Data</CardDescription>
              </CardHeader>
              <CardFooter className="pt-4 border-t mt-auto">
                <div className="text-sm font-medium text-primary flex items-center">
                  Browse Table <ArrowRight className="ml-1 h-4 w-4 opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogHeader>
          <DialogTitle>Create New Table</DialogTitle>
          <DialogDescription>
            Define your table schema. Once created, columns cannot be altered.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleCreate} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          {createError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              {createError}
            </div>
          )}
          <div className="space-y-2 pt-2">
            <Label htmlFor="tableName">Table Name</Label>
            <Input 
              id="tableName" 
              placeholder="e.g. users" 
              value={tableName}
              onChange={e => setTableName(e.target.value)}
              required
              autoFocus
              pattern="^[a-zA-Z0-9_]+$"
              title="Only alphanumeric characters and underscores are allowed"
            />
          </div>

          <div className="space-y-2 pt-2 border-t">
            <div className="flex justify-between items-center">
              <Label>Columns</Label>
              <Button type="button" variant="outline" size="sm" onClick={addColumn}>
                <Plus className="h-3 w-3 mr-1" /> Add
              </Button>
            </div>
            
            <div className="space-y-3">
              {columns.map((col, idx) => (
                <div key={idx} className="flex flex-col sm:flex-row gap-2 items-start sm:items-center bg-muted/30 p-2 rounded-md border">
                  <Input 
                    placeholder="column_name" 
                    value={col.name}
                    onChange={e => updateColumn(idx, "name", e.target.value)}
                    required
                    pattern="^[a-zA-Z0-9_]+$"
                    disabled={col.is_primary_key} // Don't allow renaming PK easily here
                    className="w-full sm:w-1/3"
                  />
                  <select
                    className="flex h-10 w-full sm:w-1/4 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
                    value={col.type}
                    onChange={e => updateColumn(idx, "type", e.target.value)}
                    disabled={col.is_primary_key}
                  >
                    <option value="TEXT">TEXT</option>
                    <option value="INTEGER">INTEGER</option>
                    <option value="REAL">REAL</option>
                    <option value="BOOLEAN">BOOLEAN</option>
                    <option value="JSON">JSON</option>
                  </select>
                  <label className="flex items-center gap-2 text-sm shrink-0">
                    <input 
                      type="checkbox" 
                      checked={col.is_nullable}
                      onChange={e => updateColumn(idx, "is_nullable", e.target.checked)}
                      disabled={col.is_primary_key}
                    />
                    Nullable
                  </label>
                  {!col.is_primary_key && (
                    <Button type="button" variant="ghost" size="icon" className="text-destructive sm:ml-auto" onClick={() => removeColumn(idx)}>
                      <span className="sr-only">Remove</span>
                      &times;
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <DialogFooter className="pt-4 border-t">
            <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={createTable.isPending}>
              {createTable.isPending ? "Creating..." : "Create Table"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  )
}
