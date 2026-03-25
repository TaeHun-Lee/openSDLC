import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { useSettingsStore } from "@/stores/settings-store"
import { useTheme } from "@/hooks/use-theme"
import { useHealth } from "@/api/queries/health"

export function SettingsPage() {
  const { apiKey, setApiKey } = useSettingsStore()
  const { theme, setTheme } = useTheme()
  const { data: health } = useHealth()
  const [keyInput, setKeyInput] = useState(apiKey)

  const handleSaveKey = () => {
    setApiKey(keyInput)
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">Settings</h2>

      {/* Theme */}
      <Card>
        <CardHeader>
          <CardTitle>Theme</CardTitle>
          <CardDescription>Choose your preferred theme.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            {(["light", "dark", "system"] as const).map((t) => (
              <Button
                key={t}
                variant={theme === t ? "default" : "outline"}
                size="sm"
                onClick={() => setTheme(t)}
              >
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* API Key */}
      <Card>
        <CardHeader>
          <CardTitle>API Key</CardTitle>
          <CardDescription>
            Required if the backend has OPENSDLC_API_KEY configured.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <input
            type="password"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            placeholder="Enter API key..."
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
          />
          <Button onClick={handleSaveKey} size="sm">Save</Button>
        </CardContent>
      </Card>

      {/* System Info */}
      {health && (
        <Card>
          <CardHeader>
            <CardTitle>System Info</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-muted-foreground">
            <p>Status: {health.status}</p>
            <p>LLM Provider: {health.llm_provider}</p>
            <p>Model: {health.model}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
