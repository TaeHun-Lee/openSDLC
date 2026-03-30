import { useState, useEffect } from "react"
import { Loader2, Info } from "lucide-react"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { useSSEStore } from "@/stores/sse-store"
import { useNarrativeStore } from "@/stores/narrative-store"
import { AGENT_COLORS } from "@/lib/constants"
import { formatDuration } from "@/lib/format"

interface RunProgressProps {
  maxIterations: number
  startedAt: number
}

export function RunProgress({ maxIterations, startedAt }: RunProgressProps) {
  const { status, currentIteration, currentStep, currentAgent, stepsTotal } = useSSEStore()
  const isResume = useNarrativeStore((s) => s.isResume)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (status !== "running") return
    const interval = setInterval(() => {
      setElapsed(Date.now() / 1000 - startedAt)
    }, 1000)
    return () => clearInterval(interval)
  }, [status, startedAt])

  if (status !== "running") return null

  const iterProgress = currentIteration != null && maxIterations > 0
    ? (currentIteration / maxIterations) * 100
    : 0
  const stepProgress = currentStep != null && stepsTotal != null && stepsTotal > 0
    ? (currentStep / stepsTotal) * 100
    : 0

  return (
    <div className="space-y-3">
      {isResume && (
        <div className="flex items-center gap-2 rounded-lg border border-blue-300 bg-blue-500/10 p-3 text-sm text-blue-700 dark:text-blue-400">
          <Info className="h-4 w-4 shrink-0" />
          Resuming from a previous run
        </div>
      )}

      <div className="rounded-lg border p-4 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span>
            Iteration {currentIteration ?? "—"} / {maxIterations}
            {" — "}
            Step {currentStep ?? "—"} / {stepsTotal ?? "—"}
          </span>
          <span className="text-muted-foreground">{formatDuration(elapsed)}</span>
        </div>

        <Progress value={stepsTotal ? stepProgress : iterProgress} />

        {currentAgent && (
          <div className="flex items-center gap-2 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className={AGENT_COLORS[currentAgent] ?? ""}>
              {currentAgent}
            </span>
            <Badge variant="secondary" className="text-xs">running</Badge>
          </div>
        )}
      </div>
    </div>
  )
}
