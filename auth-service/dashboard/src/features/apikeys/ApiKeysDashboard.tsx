import { useState, useEffect } from "react"
import { useApiKeys, useCreateApiKey, useRevokeApiKey } from "@/hooks/useApiKeys"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { Key, Plus, ShieldAlert, Copy, Check, AlertTriangle } from "lucide-react"

export function ApiKeysDashboard() {
  const { data: keys, isLoading, isError } = useApiKeys()
  const createKey = useCreateApiKey()
  const revokeKey = useRevokeApiKey()

  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [keyName, setKeyName] = useState("")
  const [createError, setCreateError] = useState<string | null>(null)
  
  // Transient state for the newly generated secret
  const [newSecret, setNewSecret] = useState<string | null>(null)
  const [hasCopied, setHasCopied] = useState(false)

  const [revokeConfirmId, setRevokeConfirmId] = useState<{ id: string, name: string } | null>(null)
  const [revokeError, setRevokeError] = useState<string | null>(null)

  // Reset copied state when closing modal
  useEffect(() => {
    if (!isCreateOpen) {
      setHasCopied(false)
      // We purposefully DO NOT clear newSecret here yet, so it can animate out nicely.
      // But we will clear it when reopening.
    }
  }, [isCreateOpen])

  const handleOpenCreate = () => {
    setNewSecret(null)
    setKeyName("")
    setCreateError(null)
    setIsCreateOpen(true)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setCreateError(null)
    
    try {
      const response = await createKey.mutateAsync(keyName)
      // Assume the backend returns the raw secret upon creation in response.secret_key
      if (response.secret_key) {
        setNewSecret(response.secret_key)
      } else {
        // Fallback or handle appropriately if backend doesn't return it
        setCreateError("Key was created, but secret could not be retrieved from the response.")
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setCreateError("Only Admins and Owners can manage API Keys.")
      } else {
        setCreateError(err.response?.data?.detail || "Failed to create API key.")
      }
    }
  }

  const handleCopy = () => {
    if (newSecret) {
      navigator.clipboard.writeText(newSecret)
      setHasCopied(true)
      setTimeout(() => setHasCopied(false), 2000)
    }
  }

  const handleRevoke = async () => {
    if (!revokeConfirmId) return
    setRevokeError(null)
    try {
      await revokeKey.mutateAsync(revokeConfirmId.id)
      setRevokeConfirmId(null)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setRevokeError("Permission denied.")
      } else {
        setRevokeError(err.response?.data?.detail || "Failed to revoke API key.")
      }
    }
  }

  const handleDismissNewKey = () => {
    setIsCreateOpen(false)
    // Destroy secret from memory immediately upon explicit dismissal
    setNewSecret(null)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">API Keys</h2>
          <p className="text-muted-foreground">Loading your API keys...</p>
        </div>
        <Card>
          <CardContent className="p-6">
            <Skeleton className="h-10 w-full mb-4" />
            <Skeleton className="h-10 w-full mb-4" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-destructive/15 text-destructive p-4 rounded-md flex items-center gap-2">
        <ShieldAlert className="h-4 w-4" />
        Failed to load API keys. Ensure you have the proper permissions.
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">API Keys</h2>
          <p className="text-muted-foreground">Manage keys for accessing your project programmatically.</p>
        </div>
        <Button onClick={handleOpenCreate} className="shrink-0">
          <Plus className="mr-2 h-4 w-4" /> Generate New Key
        </Button>
      </div>

      <Card>
        <div className="rounded-md border">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="px-4 py-3 font-medium text-muted-foreground">Name</th>
                <th className="px-4 py-3 font-medium text-muted-foreground">Prefix</th>
                <th className="px-4 py-3 font-medium text-muted-foreground">Created</th>
                <th className="px-4 py-3 font-medium text-muted-foreground text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {keys?.map((keyItem) => (
                <tr key={keyItem.key_id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-medium flex items-center gap-2">
                    <Key className="h-4 w-4 text-muted-foreground" />
                    {keyItem.name}
                  </td>
                  <td className="px-4 py-3 font-mono text-muted-foreground">
                    antigravity_{keyItem.key_id.substring(0, 8)}...
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(keyItem.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => setRevokeConfirmId({ id: keyItem.key_id, name: keyItem.name })}
                    >
                      Revoke
                    </Button>
                  </td>
                </tr>
              ))}
              {keys?.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-muted-foreground">
                    <div className="flex flex-col items-center gap-2">
                      <Key className="h-8 w-8 text-muted-foreground/50 mb-2" />
                      <p>No API keys generated yet.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Create / Display Secret Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogHeader>
          <DialogTitle>{newSecret ? "Save Your API Key" : "Generate New API Key"}</DialogTitle>
          <DialogDescription>
            {newSecret 
              ? "Please copy this key immediately. You will not be able to see it again."
              : "Create a new secret key to access your project programmatically."}
          </DialogDescription>
        </DialogHeader>

        {newSecret ? (
          <div className="space-y-4 pt-2">
            <div className="bg-amber-500/15 text-amber-600 dark:text-amber-500 p-3 rounded-md text-sm flex items-start gap-2 border border-amber-500/20">
              <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="font-medium">This is the only time this key will be shown.</p>
                <p>If you lose this key, you will need to generate a new one.</p>
              </div>
            </div>
            
            <div className="flex gap-2 items-center">
              <Input 
                value={newSecret}
                readOnly
                className="font-mono text-sm bg-muted"
                onFocus={(e) => e.target.select()}
              />
              <Button variant="secondary" onClick={handleCopy} className="shrink-0 w-24">
                {hasCopied ? (
                  <><Check className="mr-2 h-4 w-4" /> Copied</>
                ) : (
                  <><Copy className="mr-2 h-4 w-4" /> Copy</>
                )}
              </Button>
            </div>
            
            <DialogFooter className="pt-4 border-t mt-4">
              <Button onClick={handleDismissNewKey}>I've saved it securely</Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleCreate} className="space-y-4">
            {createError && (
              <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 shrink-0" />
                {createError}
              </div>
            )}
            <div className="space-y-2 pt-2">
              <Label htmlFor="keyName">Key Name</Label>
              <Input 
                id="keyName" 
                placeholder="e.g. Production Frontend Server" 
                value={keyName}
                onChange={e => setKeyName(e.target.value)}
                required
                autoFocus
              />
            </div>
            <DialogFooter className="pt-4 border-t mt-4">
              <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createKey.isPending}>
                {createKey.isPending ? "Generating..." : "Generate Key"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </Dialog>

      {/* Revoke Confirmation Modal */}
      <Dialog open={!!revokeConfirmId} onOpenChange={(o) => !o && setRevokeConfirmId(null)}>
        <DialogHeader>
          <DialogTitle className="text-destructive flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" /> Revoke API Key
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to revoke the key <strong className="text-foreground">{revokeConfirmId?.name}</strong>?
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <p className="text-sm">
            Any applications or scripts using this key will immediately lose access and requests will fail. This action cannot be undone.
          </p>
          
          {revokeError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 shrink-0" />
              {revokeError}
            </div>
          )}
        </div>

        <DialogFooter className="pt-4 border-t mt-2">
          <Button variant="outline" onClick={() => setRevokeConfirmId(null)} disabled={revokeKey.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleRevoke} disabled={revokeKey.isPending}>
            {revokeKey.isPending ? "Revoking..." : "Revoke Key"}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
