import { ArrowRight } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { AGENT_COLORS, AGENT_BG_COLORS } from "@/lib/constants"
import type { ArtifactFlowStep } from "@/api/types"

interface PipelineFlowViewProps {
  flow: ArtifactFlowStep[]
}

export function PipelineFlowView({ flow }: PipelineFlowViewProps) {
  if (flow.length === 0) return null

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-muted-foreground">Artifact Flow</h4>
      <div className="flex flex-wrap items-center gap-2">
        {flow.map((step, i) => (
          <div key={step.step} className="flex items-center gap-2">
            <FlowNode step={step} />
            {i < flow.length - 1 && (
              <div className="flex flex-col items-center">
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
                {step.produces.length > 0 && (
                  <span className="text-[10px] text-muted-foreground max-w-[80px] truncate text-center">
                    {step.produces.join(", ")}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function FlowNode({ step }: { step: ArtifactFlowStep }) {
  const colorClass = AGENT_COLORS[step.agent] ?? "text-foreground"
  const bgClass = AGENT_BG_COLORS[step.agent] ?? "bg-muted"

  return (
    <div
      className={`flex flex-col items-center gap-1 rounded-lg border p-3 ${bgClass}`}
    >
      <span className="text-xs font-mono text-muted-foreground">Step {step.step}</span>
      <span className={`text-sm font-medium ${colorClass}`}>{step.agent}</span>
      <div className="flex flex-wrap gap-1 justify-center">
        {step.consumes.map((c) => (
          <Badge key={c} variant="outline" className="text-[10px] px-1 py-0">
            {c}
          </Badge>
        ))}
      </div>
    </div>
  )
}
