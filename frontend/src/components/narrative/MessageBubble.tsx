import { Badge } from "@/components/ui/badge"
import { AGENT_COLORS, AGENT_BG_COLORS } from "@/lib/constants"
import { formatTimestamp } from "@/lib/format"
import type { NarrativeMessage } from "@/stores/narrative-store"

interface MessageBubbleProps {
  message: NarrativeMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const agent = message.agentName ?? "System"
  const colorClass = AGENT_COLORS[agent] ?? "text-foreground"
  const bgClass = AGENT_BG_COLORS[agent] ?? "bg-muted"

  return (
    <div className="flex gap-3 py-2">
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${bgClass} ${colorClass}`}
      >
        {agent.slice(0, 2)}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${colorClass}`}>{agent}</span>
          {message.data?.rework_seq != null && Number(message.data.rework_seq) > 0 && (
            <Badge variant="outline" className="text-[10px]">
              rework #{String(message.data.rework_seq)}
            </Badge>
          )}
          <span className="text-[10px] text-muted-foreground">
            {formatTimestamp(message.createdAt)}
          </span>
        </div>
        {message.message && (
          <p className="text-sm whitespace-pre-wrap">{message.message}</p>
        )}
      </div>
    </div>
  )
}
