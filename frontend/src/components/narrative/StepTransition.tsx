import { Badge } from "@/components/ui/badge"
import { AGENT_COLORS, VERDICT_COLORS } from "@/lib/constants"
import { formatTokens } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { NarrativeMessage } from "@/stores/narrative-store"

interface StepTransitionProps {
  message: NarrativeMessage
}

export function StepTransition({ message }: StepTransitionProps) {
  const agent = message.agentName ?? ""
  const colorClass = AGENT_COLORS[agent] ?? ""

  if (message.eventType === "step_started") {
    let stepNum: number | undefined
    try {
      const data = message.message ? JSON.parse(message.message) as Record<string, unknown> : null
      stepNum = typeof data?.step_num === "number" ? data.step_num : undefined
    } catch {
      // plain text message
    }

    return (
      <div className="flex items-center gap-2 py-2">
        <div className="flex-1 border-t" />
        <span className="text-xs font-medium text-muted-foreground">
          {stepNum != null && `Step ${stepNum}: `}
          <span className={colorClass}>{agent}</span>
        </span>
        <div className="flex-1 border-t" />
      </div>
    )
  }

  // step_completed
  let verdict: string | undefined
  let model: string | undefined
  let inputTokens: number | undefined
  let outputTokens: number | undefined

  try {
    const data = message.message ? JSON.parse(message.message) as Record<string, unknown> : null
    verdict = typeof data?.verdict === "string" ? data.verdict : undefined
    model = typeof data?.model_used === "string" ? data.model_used : undefined
    inputTokens = typeof data?.input_tokens === "number" ? data.input_tokens : undefined
    outputTokens = typeof data?.output_tokens === "number" ? data.output_tokens : undefined
  } catch {
    // plain text
  }

  return (
    <div className="flex items-center gap-2 py-1 text-xs text-muted-foreground">
      {verdict && (
        <Badge className={cn("text-[10px]", VERDICT_COLORS[verdict])}>{verdict}</Badge>
      )}
      {model && <span>{model}</span>}
      {(inputTokens || outputTokens) && (
        <span>{formatTokens(inputTokens ?? 0)} / {formatTokens(outputTokens ?? 0)}</span>
      )}
    </div>
  )
}
