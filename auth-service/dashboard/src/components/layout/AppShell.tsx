import { Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "@/contexts/AuthContext"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Database, LogOut, Settings, Key, Users, Activity, HardDrive, Server } from "lucide-react"
import { ProjectSwitcher } from "@/features/projects/ProjectSwitcher"
import { useProject } from "@/contexts/ProjectContext"

export function AppShell() {
  const { user, logout } = useAuth()
  const { activeProjectId } = useProject()
  const navigate = useNavigate()

  const handleLogout = async () => {
    try {
      await api.post("/auth/logout")
    } catch (err) {
      console.error("Logout failed on server", err)
    } finally {
      logout()
      navigate("/login")
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 border-r border-border bg-card flex flex-col h-screen overflow-y-auto">
        <div className="p-4 border-b border-border">
          <h2 className="text-lg font-bold tracking-tight text-primary">Antigravity BaaS</h2>
          <ProjectSwitcher />
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          {activeProjectId ? (
            <>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 mt-4 px-2">Data & Storage</div>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={() => navigate('/database')}>
            <Database className="mr-2 h-4 w-4" /> Database
          </Button>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground">
            <HardDrive className="mr-2 h-4 w-4" /> Storage
          </Button>

          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 mt-6 px-2">Access</div>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={() => navigate('/team')}>
            <Users className="mr-2 h-4 w-4" /> Team
          </Button>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={() => navigate('/apikeys')}>
            <Key className="mr-2 h-4 w-4" /> API Keys
          </Button>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={() => navigate('/storage')}>
            <HardDrive className="mr-2 h-4 w-4" /> Storage
          </Button>

          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 mt-6 px-2">Platform</div>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={() => navigate('/deploy')}>
            <Server className="mr-2 h-4 w-4" /> Deployment
          </Button>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground">
            <Activity className="mr-2 h-4 w-4" /> Health
          </Button>
          <Button variant="ghost" className="w-full justify-start text-muted-foreground hover:text-foreground" onClick={() => navigate('/settings')}>
            <Settings className="mr-2 h-4 w-4" /> Settings
          </Button>
            </>
          ) : (
            <div className="p-4 text-sm text-muted-foreground text-center">
              Please select or create a project to view its resources.
            </div>
          )}
        </nav>

        <div className="p-4 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="flex flex-col overflow-hidden">
              <span className="text-sm font-medium truncate">{user?.username}</span>
              <span className="text-xs text-muted-foreground truncate">{user?.email}</span>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout} title="Log out">
              <LogOut className="h-4 w-4 text-muted-foreground" />
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
