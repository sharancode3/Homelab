import { useState } from "react"
import { useProjects } from "@/hooks/useProjects"
import { useProject } from "@/contexts/ProjectContext"
import { Button } from "@/components/ui/button"
import { Folder, ChevronsUpDown, Check } from "lucide-react"

export function ProjectSwitcher() {
  const { data: projects, isLoading } = useProjects()
  const { activeProjectId, setActiveProjectId } = useProject()
  const [isOpen, setIsOpen] = useState(false)

  if (isLoading) {
    return <div className="h-10 w-full animate-pulse bg-muted rounded-md" />
  }

  if (!projects || projects.length === 0) {
    return null
  }

  const activeProject = projects.find(p => p.project_id === activeProjectId)

  return (
    <div className="relative mt-4 mb-2">
      <Button 
        variant="outline" 
        role="combobox" 
        aria-expanded={isOpen}
        className="w-full justify-between px-3 font-normal"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2 truncate">
          <Folder className="h-4 w-4 shrink-0 text-primary" />
          <span className="truncate">{activeProject?.name || "Select Project"}</span>
        </div>
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>

      {isOpen && (
        <div className="absolute top-12 left-0 w-full z-50 rounded-md border bg-popover text-popover-foreground shadow-md outline-none animate-in fade-in-80">
          <div className="max-h-[300px] overflow-y-auto p-1">
            <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Projects
            </div>
            {projects.map(project => (
              <div 
                key={project.project_id}
                className="relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none hover:bg-accent hover:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50"
                onClick={() => {
                  setActiveProjectId(project.project_id)
                  setIsOpen(false)
                }}
              >
                <span className="truncate">{project.name}</span>
                {activeProjectId === project.project_id && (
                  <span className="absolute right-2 flex h-3.5 w-3.5 items-center justify-center">
                    <Check className="h-4 w-4 text-primary" />
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
