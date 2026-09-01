import { useState, useRef } from "react"
import { useStorageFiles, useUploadFile, useDeleteFile, downloadFile } from "@/hooks/useStorage"
import { useProject } from "@/contexts/ProjectContext"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog"
import { UploadCloud, File as FileIcon, Trash2, Download, AlertCircle, HardDrive, Image as ImageIcon, FileText, Film, Archive } from "lucide-react"

const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5 MB

function formatBytes(bytes: number, decimals = 2) {
  if (!+bytes) return '0 Bytes'
  const k = 1024
  const dm = decimals < 0 ? 0 : decimals
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`
}

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith('image/')) return ImageIcon
  if (mimeType.startsWith('video/')) return Film
  if (mimeType.startsWith('text/')) return FileText
  if (mimeType.includes('zip') || mimeType.includes('tar') || mimeType.includes('gzip')) return Archive
  return FileIcon
}

export function StorageDashboard() {
  const { activeProjectId } = useProject()
  const { data: files, isLoading, isError } = useStorageFiles()
  
  const uploadFile = useUploadFile()
  const deleteFile = useDeleteFile()

  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const [deleteConfirmId, setDeleteConfirmId] = useState<{id: string, name: string} | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const validateAndUpload = async (file: File) => {
    if (file.size > MAX_FILE_SIZE) {
      setUploadError(`File too large. Maximum size is 5 MB. (${formatBytes(file.size)} attempted)`)
      return
    }

    setIsUploading(true)
    setUploadProgress(0)
    setUploadError(null)

    try {
      await uploadFile.mutateAsync({
        file,
        onProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            setUploadProgress(percentCompleted)
          }
        }
      })
    } catch (err: any) {
      if (err.response?.status === 413) {
        setUploadError("Payload Too Large: Quota exceeded or file too big.")
      } else if (err.response?.status === 403) {
        setUploadError("Permission denied.")
      } else {
        setUploadError(err.response?.data?.detail || "Failed to upload file.")
      }
    } finally {
      setIsUploading(false)
      setUploadProgress(0)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await validateAndUpload(e.dataTransfer.files[0])
    }
  }

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault()
    if (e.target.files && e.target.files[0]) {
      await validateAndUpload(e.target.files[0])
    }
  }

  const handleDownload = async (fileId: string, filename: string) => {
    setActionError(null)
    try {
      await downloadFile(activeProjectId!, fileId, filename)
    } catch (err: any) {
      setActionError("Failed to download file.")
    }
  }

  const handleDelete = async () => {
    if (!deleteConfirmId) return
    setActionError(null)
    try {
      await deleteFile.mutateAsync(deleteConfirmId.id)
      setDeleteConfirmId(null)
    } catch (err: any) {
      if (err.response?.status === 403) {
        setActionError("Permission denied.")
      } else {
        setActionError("Failed to delete file.")
      }
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Storage</h2>
          <p className="text-muted-foreground">Loading your files...</p>
        </div>
        <Card>
          <CardContent className="p-6">
            <Skeleton className="h-10 w-full mb-4" />
            <Skeleton className="h-32 w-full mb-4" />
            <Skeleton className="h-10 w-full" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-destructive/15 text-destructive p-4 rounded-md flex items-center gap-2">
        <AlertCircle className="h-4 w-4" />
        Failed to load storage files. Ensure you have the proper permissions.
      </div>
    )
  }

  const totalUsage = files?.reduce((acc, f) => acc + f.size_bytes, 0) || 0

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Storage</h2>
          <p className="text-muted-foreground">Manage media, documents, and assets for your project.</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 px-3 py-1.5 rounded-md border border-border">
          <HardDrive className="h-4 w-4" />
          <span className="font-medium">{formatBytes(totalUsage)}</span> 
          <span>used</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardContent className="p-4 flex flex-col items-center justify-center text-center">
              <form 
                className={`relative w-full h-48 border-2 border-dashed rounded-lg transition-colors flex flex-col items-center justify-center space-y-2 p-4 cursor-pointer ${
                  dragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/30"
                } ${isUploading ? "opacity-50 pointer-events-none" : ""}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !isUploading && fileInputRef.current?.click()}
              >
                <input 
                  ref={fileInputRef}
                  type="file" 
                  className="hidden" 
                  onChange={handleChange}
                  disabled={isUploading}
                />
                
                {isUploading ? (
                  <div className="space-y-3 w-full px-4">
                    <div className="flex items-center justify-between text-xs font-medium text-muted-foreground">
                      <span>Uploading...</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-primary transition-all duration-300"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="bg-primary/10 p-3 rounded-full text-primary">
                      <UploadCloud className="h-6 w-6" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium">Click or drag file here</p>
                      <p className="text-xs text-muted-foreground">Max file size: 5 MB</p>
                    </div>
                  </>
                )}
              </form>
              
              {uploadError && (
                <div className="mt-4 text-xs text-destructive text-left w-full bg-destructive/10 p-2 rounded flex gap-2 items-start">
                  <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                  <span>{uploadError}</span>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="lg:col-span-3">
          <Card className="h-[calc(100vh-14rem)] flex flex-col">
            <div className="overflow-auto flex-1">
              <table className="w-full text-sm text-left">
                <thead className="bg-muted/50 border-b sticky top-0 z-10">
                  <tr>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Name</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Type</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Size</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground">Uploaded</th>
                    <th className="px-4 py-3 font-medium text-muted-foreground text-right w-24">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {files?.map((file) => {
                    const Icon = getFileIcon(file.mime_type)
                    return (
                      <tr key={file.id} className="hover:bg-muted/30 transition-colors group">
                        <td className="px-4 py-3 font-medium flex items-center gap-3">
                          <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="truncate max-w-[200px] md:max-w-[300px]" title={file.filename}>{file.filename}</span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground truncate max-w-[150px]" title={file.mime_type}>
                          {file.mime_type}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {formatBytes(file.size_bytes)}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">
                          {new Date(file.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-4 py-2 text-right">
                          <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-7 w-7 text-muted-foreground hover:text-primary"
                              onClick={() => handleDownload(file.id, file.filename)}
                              title="Download"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </Button>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-7 w-7 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                              onClick={() => setDeleteConfirmId({ id: file.id, name: file.filename })}
                              title="Delete"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                  {files?.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-20 text-center text-muted-foreground">
                        <div className="flex flex-col items-center gap-2">
                          <FileIcon className="h-8 w-8 text-muted-foreground/50 mb-2" />
                          <p>No files uploaded yet.</p>
                          <p className="text-xs">Drag and drop a file on the left to get started.</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            
            <div className="border-t bg-muted/20 px-4 py-2 text-xs text-muted-foreground flex justify-between items-center shrink-0">
              <span>{files?.length || 0} items</span>
            </div>
          </Card>
        </div>
      </div>

      <Dialog open={!!deleteConfirmId} onOpenChange={(o) => !o && setDeleteConfirmId(null)}>
        <DialogHeader>
          <DialogTitle className="text-destructive flex items-center gap-2">
            <AlertCircle className="h-5 w-5" /> Delete File
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete <strong className="text-foreground">{deleteConfirmId?.name}</strong>?
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4">
          <p className="text-sm">
            This action cannot be undone. Links to this file will immediately break.
          </p>
          
          {actionError && (
            <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {actionError}
            </div>
          )}
        </div>

        <DialogFooter className="pt-4 border-t mt-2">
          <Button variant="outline" onClick={() => setDeleteConfirmId(null)} disabled={deleteFile.isPending}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleteFile.isPending}>
            {deleteFile.isPending ? "Deleting..." : "Delete File"}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  )
}
