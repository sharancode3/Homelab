import { useState } from "react"
import { useProjects, useCreateProject } from "@/hooks/useProjects"
import { useProject } from "@/contexts/ProjectContext"
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Plus, Folder, ArrowRight, AlertCircle } from "lucide-react"

export function ProjectsDashboard() {
  const { data: projects, isLoading, isError } = useProjects()
  const { setActiveProjectId } = useProject()
  const createProject = useCreateProject()

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState("")
  const [createError, setCreateError] = useState<string | null>(null)

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    if (!newProjectName.trim()) return

    try {
      const p = await createProject.mutateAsync(newProjectName)
      setIsCreateOpen(false)
      setNewProjectName("")
      setActiveProjectId(p.project_id)
    } catch (err: any) {
      setCreateError(err.response?.data?.detail || "Failed to create project")
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Projects</h2>
            <p className="text-muted-foreground">Loading your projects...</p>
          </div>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-destructive/15 text-destructive p-4 rounded-md flex items-center gap-2">
        <AlertCircle className="h-5 w-5" />
        <p>Failed to load projects. Please try again later.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Projects</h2>
          <p className="text-muted-foreground">Select a project to manage its databases, storage, and settings.</p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" /> New Project
        </Button>
      </div>

      {!projects || projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-12 text-center border rounded-xl border-dashed bg-muted/20">
          <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center mb-4">
            <Folder className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No projects found</h3>
          <p className="text-sm text-muted-foreground max-w-sm mb-4">
            You don't have any projects yet. Create your first project to start building with Antigravity BaaS.
          </p>
          <Button onClick={() => setIsCreateOpen(true)}>Create Project</Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Card key={project.project_id} className="hover:border-primary/50 transition-colors flex flex-col cursor-pointer group" onClick={() => setActiveProjectId(project.project_id)}>
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="h-10 w-10 rounded-md bg-primary/10 flex items-center justify-center text-primary mb-2">
                    <Folder className="h-5 w-5" />
                  </div>
                </div>
                <CardTitle className="group-hover:text-primary transition-colors">{project.name}</CardTitle>
                <CardDescription>ID: {project.project_id}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <p className="text-sm text-muted-foreground">Created {new Date(project.created_at).toLocaleDateString()}</p>
              </CardContent>
              <CardFooter className="pt-4 border-t">
                <div className="text-sm font-medium text-primary flex items-center">
                  Manage Project <ArrowRight className="ml-1 h-4 w-4 opacity-0 -translate-x-2 transition-all group-hover:opacity-100 group-hover:translate-x-0" />
                </div>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogDescription>
            Enter a name for your new project. You can change this later.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleCreate} className="space-y-4">
          {createError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4" />
              {createError}
            </div>
          )}
          <div className="space-y-2 pt-2">
            <Label htmlFor="projectName">Project Name</Label>
            <Input 
              id="projectName" 
              placeholder="e.g. Production Backend" 
              value={newProjectName}
              onChange={e => setNewProjectName(e.target.value)}
              required
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={createProject.isPending}>
              {createProject.isPending ? "Creating..." : "Create Project"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  )
}
