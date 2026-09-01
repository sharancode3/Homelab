import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ProjectProvider } from './contexts/ProjectContext'
import { ProtectedRoute } from './components/layout/ProtectedRoute'
import { AppShell } from './components/layout/AppShell'
import { Login } from './features/auth/Login'
import { Signup } from './features/auth/Signup'

import { ProjectsDashboard } from './features/projects/ProjectsDashboard'
import { ProjectSettings } from './features/projects/ProjectSettings'
import { TeamDashboard } from './features/team/TeamDashboard'
import { DatabaseDashboard } from './features/database/DatabaseDashboard'
import { TableDetail } from './features/database/TableDetail'
import { ApiKeysDashboard } from './features/apikeys/ApiKeysDashboard'
import { StorageDashboard } from './features/storage/StorageDashboard'
import { DeploymentDashboard } from './features/deployment/DeploymentDashboard'
import { useProject } from './contexts/ProjectContext'

const DashboardHome = () => {
  const { activeProjectId } = useProject()
  
  if (!activeProjectId) {
    return <ProjectsDashboard />
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Project Overview</h1>
      <p className="text-muted-foreground mt-2">Managing project: {activeProjectId}</p>
    </div>
  )
}

function App() {
  return (
    <AuthProvider>
      <ProjectProvider>
        <Router>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<AppShell />}>
                <Route index element={<DashboardHome />} />
                <Route path="settings" element={<ProjectSettings />} />
                <Route path="team" element={<TeamDashboard />} />
                <Route path="database" element={<DatabaseDashboard />} />
                <Route path="database/:tableName" element={<TableDetail />} />
                <Route path="apikeys" element={<ApiKeysDashboard />} />
                <Route path="storage" element={<StorageDashboard />} />
                <Route path="deploy" element={<DeploymentDashboard />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </ProjectProvider>
    </AuthProvider>
  )
}

export default App
