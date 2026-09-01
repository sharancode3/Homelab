import { useState } from "react"
import { useTeamMembers, useInviteMember, useUpdateMemberRole, useRemoveMember } from "@/hooks/useTeam"
import { useAuth } from "@/contexts/AuthContext"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { UserPlus, ShieldAlert, Trash2 } from "lucide-react"

export function TeamDashboard() {
  const { user } = useAuth()
  const { data: members, isLoading, isError } = useTeamMembers()
  const inviteMember = useInviteMember()
  const updateRole = useUpdateMemberRole()
  const removeMember = useRemoveMember()

  const [isInviteOpen, setIsInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteRole, setInviteRole] = useState("developer")
  const [inviteError, setInviteError] = useState<string | null>(null)

  const [deleteConfirmUser, setDeleteConfirmUser] = useState<{userId: string, email: string} | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault()
    setInviteError(null)
    try {
      await inviteMember.mutateAsync({ email: inviteEmail, role: inviteRole })
      setIsInviteOpen(false)
      setInviteEmail("")
      setInviteRole("developer")
    } catch (err: any) {
      if (err.response?.status === 403) {
        setInviteError("Only Owners or Admins can invite new members.")
      } else {
        setInviteError(err.response?.data?.detail || "Failed to invite member.")
      }
    }
  }

  const handleRemove = async () => {
    if (!deleteConfirmUser) return
    setDeleteError(null)
    try {
      await removeMember.mutateAsync(deleteConfirmUser.userId)
      setDeleteConfirmUser(null)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setDeleteError("You do not have permission to remove this member.")
      } else {
        setDeleteError(err.response?.data?.detail || "Failed to remove member.")
      }
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Team Settings</h2>
            <p className="text-muted-foreground">Manage project access.</p>
          </div>
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
      <div className="bg-destructive/15 text-destructive p-4 rounded-md">
        Failed to load team members. Ensure you have the proper permissions.
      </div>
    )
  }

  // Current user's role in this project
  const currentUserRole = members?.find(m => m.user_id === user?.user_id)?.role || "viewer"
  const canManageTeam = currentUserRole === "owner" || currentUserRole === "admin"

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Team</h2>
          <p className="text-muted-foreground">Manage who has access to this project and their permissions.</p>
        </div>
        {canManageTeam && (
          <Button onClick={() => setIsInviteOpen(true)} className="shrink-0">
            <UserPlus className="mr-2 h-4 w-4" /> Invite Member
          </Button>
        )}
      </div>

      <Card>
        <div className="rounded-md border">
          <table className="w-full text-sm text-left">
            <thead className="bg-muted/50 border-b">
              <tr>
                <th className="px-4 py-3 font-medium text-muted-foreground">Member</th>
                <th className="px-4 py-3 font-medium text-muted-foreground">Role</th>
                <th className="px-4 py-3 font-medium text-muted-foreground text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members?.map((member) => (
                <tr key={member.user_id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-medium">
                        {member.username.charAt(0).toUpperCase()}
                      </div>
                      <div className="flex flex-col">
                        <span className="font-medium flex items-center gap-2">
                          {member.username} 
                          {member.user_id === user?.user_id && <span className="text-xs bg-muted px-1.5 py-0.5 rounded-sm text-muted-foreground">You</span>}
                        </span>
                        <span className="text-xs text-muted-foreground">{member.user_id}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {canManageTeam && member.user_id !== user?.user_id ? (
                      <select 
                        className="bg-transparent border rounded px-2 py-1 text-sm outline-none focus:ring-1 focus:ring-primary"
                        value={member.role}
                        onChange={(e) => updateRole.mutate({ userId: member.user_id, role: e.target.value })}
                        disabled={updateRole.isPending}
                      >
                        <option value="owner">Owner</option>
                        <option value="admin">Admin</option>
                        <option value="developer">Developer</option>
                        <option value="viewer">Viewer</option>
                      </select>
                    ) : (
                      <span className="capitalize">{member.role}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {canManageTeam && member.user_id !== user?.user_id && (
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={() => setDeleteConfirmUser({ userId: member.user_id, email: member.username })}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {members?.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">
                    No members found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={isInviteOpen} onOpenChange={setIsInviteOpen}>
        <DialogHeader>
          <DialogTitle>Invite Team Member</DialogTitle>
          <DialogDescription>
            Invite a new member to this project by their email address.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleInvite} className="space-y-4">
          {inviteError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <ShieldAlert className="h-4 w-4" />
              {inviteError}
            </div>
          )}
          <div className="space-y-2 pt-2">
            <Label htmlFor="email">Email Address</Label>
            <Input 
              id="email" 
              type="email"
              placeholder="colleague@example.com" 
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <select 
              id="role"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={inviteRole}
              onChange={e => setInviteRole(e.target.value)}
            >
              <option value="admin">Admin</option>
              <option value="developer">Developer</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setIsInviteOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={inviteMember.isPending}>
              {inviteMember.isPending ? "Inviting..." : "Send Invite"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      <Dialog open={!!deleteConfirmUser} onOpenChange={(open) => !open && setDeleteConfirmUser(null)}>
        <DialogHeader>
          <DialogTitle className="text-destructive">Remove Team Member</DialogTitle>
          <DialogDescription>
            Are you sure you want to remove <strong className="text-foreground">{deleteConfirmUser?.email}</strong> from this project? They will lose all access immediately.
          </DialogDescription>
        </DialogHeader>
        {deleteError && (
          <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
            <ShieldAlert className="h-4 w-4" />
            {deleteError}
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => setDeleteConfirmUser(null)} disabled={removeMember.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleRemove} disabled={removeMember.isPending}>
            {removeMember.isPending ? "Removing..." : "Remove Member"}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
