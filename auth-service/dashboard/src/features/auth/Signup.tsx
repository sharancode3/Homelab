import { useState } from "react"
import { useNavigate, Link } from "react-router-dom"
import { AuthLayout } from "./AuthLayout"
import { Card, CardContent, CardFooter } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { AlertCircle } from "lucide-react"

export function Signup() {
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    
    try {
      await api.post("/auth/register", { username, email, password })
      navigate("/login")
    } catch (err: any) {
      if (err.response?.status === 409) {
        setError("Email or username already in use.")
      } else {
        setError(err.response?.data?.detail || "An error occurred during signup.")
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout title="Create an account" subtitle="Start building with Antigravity BaaS">
      <Card>
        <form onSubmit={handleSubmit}>
          <CardContent className="pt-6 space-y-4">
            {error && (
              <div className="bg-destructive/15 text-destructive p-3 rounded-md text-sm flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input 
                id="username" 
                type="text" 
                placeholder="johndoe" 
                required 
                value={username}
                onChange={e => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="name@example.com" 
                required 
                value={email}
                onChange={e => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input 
                id="password" 
                type="password" 
                required 
                value={password}
                onChange={e => setPassword(e.target.value)}
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Creating account..." : "Sign up"}
            </Button>
            <div className="text-sm text-center text-muted-foreground">
              Already have an account? <Link to="/login" className="text-primary hover:underline">Sign in</Link>
            </div>
          </CardFooter>
        </form>
      </Card>
    </AuthLayout>
  )
}
