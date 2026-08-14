import { useState } from "react"
import { 
  useProjectHealth, 
  useProjectStatus, 
  useProjectLogs, 
  useOperationHistory,
  useDeployProject,
  useStopProject,
  useRestartProject,
  useBackupProject,
  useRestoreProject
} from "@/hooks/useDeployment"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Activity, Server, ShieldAlert, Play, Square, RotateCw, DatabaseBackup, ListRestart, Terminal, Clock, CheckCircle2, AlertCircle } from "lucide-react"

export function DeploymentDashboard() {
  const { data: health, isLoading: isHealthLoading } = useProjectHealth()
  const { data: status, isLoading: isStatusLoading } = useProjectStatus()
  
  // Only poll logs while this tab/component is mounted
  const { data: logsData, isLoading: isLogsLoading } = useProjectLogs(true)
  
  const { data: historyData, isLoading: isHistoryLoading } = useOperationHistory()

  const deploy = useDeployProject()
  const stop = useStopProject()
  const restart = useRestartProject()
  const backup = useBackupProject()
  const restore = useRestoreProject()

  const [actionError, setActionError] = useState<string | null>(null)
  const [confirmAction, setConfirmAction] = useState<'deploy' | 'stop' | 'restart' | 'backup' | null>(null)
  
  const [isRestoreOpen, setIsRestoreOpen] = useState(false)
  const [restoreBackupId, setRestoreBackupId] = useState("")

  const handleAction = async () => {
    if (!confirmAction) return
    setActionError(null)
    
    try {
      if (confirmAction === 'deploy') await deploy.mutateAsync({})
      if (confirmAction === 'stop') await stop.mutateAsync()
      if (confirmAction === 'restart') await restart.mutateAsync()
      if (confirmAction === 'backup') await backup.mutateAsync({})
      setConfirmAction(null)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setActionError(`Permission denied to ${confirmAction}.`)
      } else {
        setActionError(err.response?.data?.detail || `Failed to ${confirmAction}.`)
      }
    }
  }

  const handleRestore = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!restoreBackupId) return
    setActionError(null)

    try {
      await restore.mutateAsync({ backup_id: restoreBackupId })
      setIsRestoreOpen(false)
      setRestoreBackupId("")
    } catch (err: any) {
      if (err.response?.status === 403) {
        setActionError("Permission denied to restore.")
      } else {
        setActionError(err.response?.data?.detail || "Failed to initiate restore.")
      }
    }
  }

  const isLoadingGlobal = deploy.isPending || stop.isPending || restart.isPending || backup.isPending

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Platform Operations</h2>
          <p className="text-muted-foreground">Manage deployments, health, and operation history.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Status Card */}
        <Card>
          <CardHeader className="pb-3 border-b bg-muted/20">
            <CardTitle className="text-lg flex items-center gap-2">
              <Server className="h-5 w-5 text-primary" /> Lifecycle Status
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            {isStatusLoading ? (
              <div className="space-y-2"><Skeleton className="h-6 w-1/2" /><Skeleton className="h-4 w-1/3" /></div>
            ) : status ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-muted-foreground">Lifecycle State</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-semibold capitalize ${
                    status.lifecycle_state === 'deployed' ? 'bg-green-500/20 text-green-600 dark:text-green-400' :
                    status.lifecycle_state === 'stopped' ? 'bg-amber-500/20 text-amber-600 dark:text-amber-400' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {status.lifecycle_state}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-muted-foreground">Deployment Status</span>
                  <span className="text-sm">{status.deployment_status}</span>
                </div>
                {status.simulated && (
                  <div className="bg-blue-500/10 text-blue-600 dark:text-blue-400 p-2 text-xs rounded border border-blue-500/20">
                    <strong>Note:</strong> Platform layer is currently simulated. No real containers are managed.
                  </div>
                )}
                <div className="text-sm text-muted-foreground pt-2 border-t">
                  {status.message}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Status unavailable.</div>
            )}
          </CardContent>
        </Card>

        {/* Health Card */}
        <Card>
          <CardHeader className="pb-3 border-b bg-muted/20">
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" /> Health Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 space-y-4">
            {isHealthLoading ? (
              <div className="space-y-2"><Skeleton className="h-6 w-1/2" /><Skeleton className="h-4 w-1/3" /></div>
            ) : health ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-muted-foreground">Overall State</span>
                  <span className={`flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold ${
                    health.success ? 'bg-green-500/20 text-green-600 dark:text-green-400' : 'bg-destructive/20 text-destructive'
                  }`}>
                    {health.success ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
                    {health.state}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-muted-foreground">Status Code</span>
                  <span className="text-sm font-mono">{health.status}</span>
                </div>
                <div className="text-sm text-muted-foreground pt-2 border-t">
                  {health.message}
                </div>
              </div>
            ) : (
              <div className="text-sm text-muted-foreground">Health data unavailable.</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Operations Toolbar */}
      <Card>
        <div className="p-4 flex flex-wrap gap-3 items-center bg-muted/10 border-b">
          <Button variant="default" size="sm" onClick={() => setConfirmAction('deploy')} disabled={isLoadingGlobal}>
            <Play className="mr-2 h-4 w-4" /> Deploy
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setConfirmAction('restart')} disabled={isLoadingGlobal}>
            <RotateCw className="mr-2 h-4 w-4" /> Restart
          </Button>
          <Button variant="outline" size="sm" className="text-amber-600 hover:text-amber-700 hover:bg-amber-50 dark:hover:bg-amber-950" onClick={() => setConfirmAction('stop')} disabled={isLoadingGlobal}>
            <Square className="mr-2 h-4 w-4" /> Stop
          </Button>
          
          <div className="h-6 w-px bg-border mx-2 hidden sm:block"></div>
          
          <Button variant="outline" size="sm" onClick={() => setConfirmAction('backup')} disabled={isLoadingGlobal}>
            <DatabaseBackup className="mr-2 h-4 w-4" /> Backup
          </Button>
          <Button variant="outline" size="sm" onClick={() => setIsRestoreOpen(true)} disabled={isLoadingGlobal}>
            <ListRestart className="mr-2 h-4 w-4" /> Restore
          </Button>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Logs Viewer */}
        <Card className="h-[400px] flex flex-col">
          <CardHeader className="py-3 px-4 border-b bg-muted/20 shrink-0">
            <CardTitle className="text-sm flex items-center justify-between">
              <span className="flex items-center gap-2"><Terminal className="h-4 w-4 text-primary" /> Platform Operation Logs</span>
              {isLogsLoading && <span className="text-xs text-muted-foreground animate-pulse">Polling...</span>}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 overflow-auto flex-1 bg-muted/5 font-mono text-xs">
            {isLogsLoading && !logsData ? (
              <div className="p-4 space-y-2"><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-3/4" /></div>
            ) : logsData?.logs.length ? (
              <div className="divide-y divide-border/50">
                {logsData.logs.map((log) => (
                  <div key={log.audit_id} className="p-2 flex gap-3 hover:bg-muted/30 transition-colors">
                    <span className="text-muted-foreground shrink-0 w-[140px]">{new Date(log.timestamp).toLocaleTimeString(undefined, {hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit'})}</span>
                    <span className={`shrink-0 w-16 uppercase font-semibold ${
                      log.severity === 'ERROR' ? 'text-destructive' : 
                      log.severity === 'WARN' ? 'text-amber-500' : 'text-blue-500'
                    }`}>{log.severity}</span>
                    <span className="text-foreground break-words">{log.message}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-muted-foreground">No platform logs recorded.</div>
            )}
          </CardContent>
        </Card>

        {/* Operation History */}
        <Card className="h-[400px] flex flex-col">
          <CardHeader className="py-3 px-4 border-b bg-muted/20 shrink-0">
            <CardTitle className="text-sm flex items-center gap-2">
              <Clock className="h-4 w-4 text-primary" /> Operation History
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 overflow-auto flex-1">
            {isHistoryLoading ? (
              <div className="p-4 space-y-2"><Skeleton className="h-8 w-full" /><Skeleton className="h-8 w-full" /></div>
            ) : historyData?.history.length ? (
              <table className="w-full text-sm text-left">
                <thead className="bg-muted/30 border-b sticky top-0">
                  <tr>
                    <th className="px-4 py-2 font-medium text-muted-foreground">Operation ID</th>
                    <th className="px-4 py-2 font-medium text-muted-foreground">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {historyData.history.map((op, i) => (
                    <tr key={`${op.operation_id}-${i}`} className="hover:bg-muted/10 transition-colors">
                      <td className="px-4 py-2 font-mono text-xs">{op.operation_id.split('-')[0]}...</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-semibold ${
                          op.status === 'completed' ? 'bg-green-500/20 text-green-600 dark:text-green-400' :
                          op.status === 'failed' ? 'bg-destructive/20 text-destructive' :
                          'bg-blue-500/20 text-blue-600 dark:text-blue-400'
                        }`}>
                          {op.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="p-6 text-center text-muted-foreground text-sm">No operations recorded yet.</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Confirmation Dialog */}
      <Dialog open={!!confirmAction} onOpenChange={(o) => !o && setConfirmAction(null)}>
        <DialogHeader>
          <DialogTitle className="capitalize">{confirmAction} Project</DialogTitle>
          <DialogDescription>
            Are you sure you want to {confirmAction} this project?
          </DialogDescription>
        </DialogHeader>
        
        {actionError && (
          <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0" />
            {actionError}
          </div>
        )}

        <DialogFooter className="pt-4 border-t">
          <Button variant="outline" onClick={() => setConfirmAction(null)} disabled={isLoadingGlobal}>
            Cancel
          </Button>
          <Button variant={confirmAction === 'stop' ? 'destructive' : 'default'} onClick={handleAction} disabled={isLoadingGlobal}>
            {isLoadingGlobal ? "Processing..." : `Confirm ${confirmAction}`}
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Restore Dialog */}
      <Dialog open={isRestoreOpen} onOpenChange={setIsRestoreOpen}>
        <DialogHeader>
          <DialogTitle>Restore from Backup</DialogTitle>
          <DialogDescription>
            Provide the Backup ID to restore the project state.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleRestore} className="space-y-4">
          {actionError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              {actionError}
            </div>
          )}
          <div className="space-y-2 pt-2">
            <Label htmlFor="backupId">Backup ID</Label>
            <Input 
              id="backupId" 
              placeholder="e.g. op-12345678" 
              value={restoreBackupId}
              onChange={e => setRestoreBackupId(e.target.value)}
              required
            />
          </div>
          <DialogFooter className="pt-4 border-t">
            <Button type="button" variant="outline" onClick={() => setIsRestoreOpen(false)} disabled={restore.isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={restore.isPending}>
              {restore.isPending ? "Restoring..." : "Restore Backup"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  )
}
