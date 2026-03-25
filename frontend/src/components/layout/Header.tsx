import { Moon, Sun, Monitor, Activity } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useTheme } from "@/hooks/use-theme"
import { useHealth } from "@/api/queries/health"
import { cn } from "@/lib/utils"

export function Header() {
  const { theme, setTheme } = useTheme()
  const { data: health, isError } = useHealth()

  const cycleTheme = () => {
    const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light"
    setTheme(next)
  }

  return (
    <header className="flex h-14 items-center justify-between border-b px-6">
      <div className="flex items-center gap-3">
        <h1 className="text-lg font-bold">OpenSDLC</h1>
      </div>

      <div className="flex items-center gap-3">
        {/* Health status */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Activity className={cn("h-4 w-4", isError ? "text-red-500" : "text-green-500")} />
          {health ? (
            <span>{health.llm_provider} / {health.model}</span>
          ) : isError ? (
            <span className="text-red-500">Disconnected</span>
          ) : null}
        </div>

        {/* Theme toggle */}
        <Button variant="ghost" size="icon" onClick={cycleTheme}>
          {theme === "light" ? (
            <Sun className="h-4 w-4" />
          ) : theme === "dark" ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Monitor className="h-4 w-4" />
          )}
        </Button>
      </div>
    </header>
  )
}
