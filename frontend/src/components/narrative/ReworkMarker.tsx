import { RotateCcw } from "lucide-react"
import type { NarrativeMessage } from "@/stores/narrative-store"

interface ReworkMarkerProps {
  message: NarrativeMessage
}

export function ReworkMarker({ message }: ReworkMarkerProps) {
  const text = message.message ?? "Rework triggered"

  return (
    <div className="flex items-center gap-2 py-3">
      <div className="flex-1 border-t border-amber-400/50" />
      <div className="flex items-center gap-1.5 text-xs font-medium text-amber-600">
        <RotateCcw className="h-3 w-3" />
        {text}
      </div>
      <div className="flex-1 border-t border-amber-400/50" />
    </div>
  )
}
