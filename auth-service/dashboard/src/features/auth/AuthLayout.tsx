import type { ReactNode } from "react"
import { Shield } from "lucide-react"

export function AuthLayout({ children, title, subtitle }: { children: ReactNode, title: string, subtitle: string }) {
  return (
    <div className="min-h-screen bg-muted/40 flex items-center justify-center p-4">
      <div className="w-full max-w-md space-y-6">
        <div className="flex flex-col items-center space-y-2 text-center">
          <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center text-primary-foreground mb-2">
            <Shield className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  )
}
