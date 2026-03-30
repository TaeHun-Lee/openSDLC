import { Badge } from "@/components/ui/badge"
import { AGENT_COLORS, VERDICT_COLORS } from "@/lib/constants"
import { formatTokens } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { StepDetailInfo } from "@/api/types"

interface ProgressTimelineProps {
  steps: StepDetailInfo[]
  currentStepNum: number | null
  currentAgent: string | null
}

export function ProgressTimeline({ steps, currentStepNum, currentAgent }: ProgressTimelineProps) {
  return (
    <div className="space-y-1">
      {steps.map((step) => {
        const isCurrent =
          step.step_num === currentStepNum && step.agent_name === currentAgent && !step.verdict
        const isCompleted = !!step.verdict

        return (
          <TimelineItem
            key={`${step.step_num}-${step.rework_seq}`}
            step={step}
            isCurrent={isCurrent}
            isCompleted={isCompleted}
          />
        )
      })}
    </div>
  )
}

function TimelineItem({
  step,
  isCurrent,
  isCompleted,
}: {
  step: StepDetailInfo
  isCurrent: boolean
  isCompleted: boolean
}) {
  const colorClass = AGENT_COLORS[step.agent_name] ?? "text-foreground"

  return (
    <div className="group relative flex gap-3 py-2">
      {/* Timeline dot */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            "h-3 w-3 rounded-full border-2",
            isCurrent && "animate-pulse bg-blue-500 border-blue-500",
            isCompleted && step.verdict === "pass" && "bg-green-500 border-green-500",
            isCompleted && step.verdict === "fail" && "bg-red-500 border-red-500",
            isCompleted && step.verdict === "warning" && "bg-amber-500 border-amber-500",
            isCompleted && !step.verdict && "bg-muted-foreground border-muted-foreground",
            !isCurrent && !isCompleted && "bg-muted border-muted-foreground/30",
          )}
        />
        <div className="w-px flex-1 bg-border" />
      </div>

      {/* Content */}
      <div className={cn("flex-1 pb-2", !isCompleted && !isCurrent && "opacity-50")}>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Step {step.step_num}</span>
          <span className={cn("text-sm font-medium", colorClass)}>{step.agent_name}</span>
          {step.rework_seq > 0 && (
            <Badge variant="outline" className="text-[10px]">rework #{step.rework_seq}</Badge>
          )}
        </div>

        {isCompleted && (
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {step.verdict && (
              <Badge className={cn("text-[10px]", VERDICT_COLORS[step.verdict])}>
                {step.verdict}
              </Badge>
            )}
            {step.model_used && <span>{step.model_used}</span>}
            {(step.input_tokens || step.output_tokens) && (
              <span>
                {formatTokens(step.input_tokens ?? 0)} / {formatTokens(step.output_tokens ?? 0)}
              </span>
            )}
            {step.cache_read_tokens != null && step.cache_read_tokens > 0 && (
              <span className="text-green-600">
                cache: {formatTokens(step.cache_read_tokens)}
              </span>
            )}
          </div>
        )}

        {isCurrent && (
          <p className="mt-1 text-xs text-blue-500">Running...</p>
        )}
      </div>
    </div>
  )
}
