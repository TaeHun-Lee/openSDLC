import { useState } from "react"
import { useSettingsStore } from "@/stores/settings-store"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { KeyRound } from "lucide-react"

export function ApiKeyDialog() {
  const { showApiKeyDialog, setShowApiKeyDialog, setApiKey, apiKey } = useSettingsStore()
  const [keyInput, setKeyInput] = useState("")

  const handleSave = () => {
    if (!keyInput.trim()) return
    setApiKey(keyInput.trim())
    setShowApiKeyDialog(false)
    setKeyInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave()
    }
  }

  return (
    <Dialog open={showApiKeyDialog} onOpenChange={setShowApiKeyDialog}>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-muted-foreground" />
            <DialogTitle>API Key Required</DialogTitle>
          </div>
          <DialogDescription>
            The server requires authentication. Please enter your API key.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label htmlFor="api-key-input">API Key</Label>
          <Input
            id="api-key-input"
            type="password"
            placeholder="Enter your API key..."
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          {apiKey && (
            <p className="text-xs text-muted-foreground">
              A saved key already exists. Entering a new key will overwrite it.
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowApiKeyDialog(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!keyInput.trim()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
