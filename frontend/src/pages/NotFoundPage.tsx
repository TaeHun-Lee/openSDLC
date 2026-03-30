import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"

export function NotFoundPage() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <h1 className="text-6xl font-bold text-muted-foreground">404</h1>
      <p className="text-muted-foreground">Page not found</p>
      <Button asChild variant="outline">
        <Link to="/">Go to Dashboard</Link>
      </Button>
    </div>
  )
}
