import { Wifi, WifiOff, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useSSEStore } from "@/stores/sse-store"
import type { ConnectionState } from "@/hooks/use-sse-stream"

interface ConnectionStatusProps {
  state: ConnectionState
  reconnectAttempt: number
  onReconnect: () => void
}

const MAX_RECONNECTS = 10

export function ConnectionStatus({ state, reconnectAttempt, onReconnect }: ConnectionStatusProps) {
  const sseError = useSSEStore((s) => s.error)

  if (state === "connected") {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-600">
        <Wifi className="h-3 w-3" /> Connected
      </div>
    )
  }

  if (state === "reconnecting") {
    return (
      <div className="flex items-center gap-1.5 text-xs text-amber-600">
        <Loader2 className="h-3 w-3 animate-spin" /> Reconnecting ({reconnectAttempt}/{MAX_RECONNECTS})
      </div>
    )
  }

  const isMaxRetries = reconnectAttempt >= MAX_RECONNECTS

  return (
    <div className="flex items-center gap-2 text-xs text-red-600">
      <WifiOff className="h-3 w-3" />
      <span>
        {isMaxRetries
          ? "Max reconnect attempts exceeded"
          : sseError || "Disconnected"}
      </span>
      <Button variant="ghost" size="sm" className="h-6 px-2 text-xs" onClick={onReconnect}>
        Reconnect
      </Button>
    </div>
  )
}
