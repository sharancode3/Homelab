import { useState } from "react"
import { useProject } from "@/contexts/ProjectContext"
import { useProjects, useDeleteProject } from "@/hooks/useProjects"
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { AlertTriangle, AlertCircle } from "lucide-react"

export function ProjectSettings() {
  const { activeProjectId } = useProject()
  const { data: projects } = useProjects()
  const deleteProject = useDeleteProject()
  
  const [isDeleteOpen, setIsDeleteOpen] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const activeProject = projects?.find(p => p.project_id === activeProjectId)

  if (!activeProject) {
    return null
  }

  const handleDelete = async () => {
    setDeleteError(null)
    try {
      await deleteProject.mutateAsync(activeProject.project_id)
      setIsDeleteOpen(false)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setDeleteError("You do not have permission to delete this project. Only owners can delete projects.")
      } else {
        setDeleteError(err.response?.data?.detail || "Failed to delete project")
      }
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Project Settings</h2>
        <p className="text-muted-foreground">Manage your project configuration and lifecycle.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>General Information</CardTitle>
          <CardDescription>Basic details about your project</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Project Name</div>
              <div className="text-base font-semibold">{activeProject.name}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Project ID</div>
              <div className="text-sm font-mono bg-muted px-2 py-1 rounded-md w-fit">{activeProject.project_id}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-muted-foreground mb-1">Created</div>
              <div className="text-sm">{new Date(activeProject.created_at).toLocaleString()}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader>
          <CardTitle className="text-destructive flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" /> Danger Zone
          </CardTitle>
          <CardDescription>
            Irreversible destructive actions. Please be certain.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-destructive/20 pb-4">
            <div>
              <h4 className="font-semibold text-sm">Delete Project</h4>
              <p className="text-sm text-muted-foreground">
                Permanently remove your project and all its resources (Database, Storage, Auth users). This action cannot be undone.
              </p>
            </div>
            <Button variant="destructive" onClick={() => setIsDeleteOpen(true)}>
              Delete Project
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogHeader>
          <DialogTitle className="text-destructive">Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete the project 
            <strong className="mx-1 text-foreground">{activeProject.name}</strong> 
            and all associated data, including users, tables, files, and API keys.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          {deleteError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {deleteError}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setIsDeleteOpen(false)} disabled={deleteProject.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleteProject.isPending}>
            {deleteProject.isPending ? "Deleting..." : "Yes, delete project"}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
