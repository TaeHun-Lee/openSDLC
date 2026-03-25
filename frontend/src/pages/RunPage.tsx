import { useParams } from "react-router-dom"
import { useRun } from "@/api/queries/runs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { formatTimestamp, formatTokens } from "@/lib/format"
import { STATUS_COLORS, AGENT_COLORS, VERDICT_COLORS } from "@/lib/constants"
import { cn } from "@/lib/utils"

export function RunPage() {
  const { runId } = useParams()
  const { data: run, isLoading } = useRun(runId || "")

  if (!runId) return <p>No run ID provided.</p>
  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (!run) return <p className="text-muted-foreground">Run not found.</p>

  const isActive = run.status === "running"
  const totalSteps = run.iterations.flatMap((i) => i.steps).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Run {run.run_id.slice(0, 8)}...</h2>
          <p className="text-muted-foreground">{run.pipeline_name}</p>
        </div>
        <div className="flex items-center gap-2">
          <div className={cn("h-2 w-2 rounded-full", STATUS_COLORS[run.status])} />
          <Badge variant={run.status === "completed" ? "default" : run.status === "failed" ? "destructive" : "secondary"}>
            {run.status}
          </Badge>
        </div>
      </div>

      {/* User Story */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">User Story</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm whitespace-pre-wrap">{run.user_story}</p>
        </CardContent>
      </Card>

      {/* Progress */}
      {isActive && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between text-sm mb-2">
              <span>Progress</span>
              <span>{totalSteps} steps completed</span>
            </div>
            <Progress value={50} />
          </CardContent>
        </Card>
      )}

      {/* Iterations */}
      {run.iterations.length > 0 && (
        <Tabs defaultValue={String(run.iterations[run.iterations.length - 1].iteration_num)}>
          <TabsList>
            {run.iterations.map((iter) => (
              <TabsTrigger key={iter.iteration_num} value={String(iter.iteration_num)}>
                Iteration {iter.iteration_num}
                {iter.satisfaction_score != null && (
                  <Badge variant="outline" className="ml-2 text-xs">{iter.satisfaction_score}</Badge>
                )}
              </TabsTrigger>
            ))}
          </TabsList>
          {run.iterations.map((iter) => (
            <TabsContent key={iter.iteration_num} value={String(iter.iteration_num)}>
              <Card>
                <CardContent className="p-4">
                  <div className="space-y-3">
                    {iter.steps.map((step) => (
                      <div
                        key={`${step.step_num}-${step.rework_seq}`}
                        className="flex items-center justify-between rounded-lg border p-3"
                      >
                        <div className="flex items-center gap-3">
                          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-sm font-medium">
                            {step.step_num}
                          </span>
                          <div>
                            <p className={cn("font-medium", AGENT_COLORS[step.agent_name])}>
                              {step.agent_name}
                            </p>
                            {step.rework_seq > 0 && (
                              <span className="text-xs text-muted-foreground">rework #{step.rework_seq}</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {step.verdict && (
                            <Badge className={cn("text-xs", VERDICT_COLORS[step.verdict])}>
                              {step.verdict}
                            </Badge>
                          )}
                          {step.model_used && (
                            <span className="text-xs text-muted-foreground">{step.model_used}</span>
                          )}
                          {(step.input_tokens || step.output_tokens) && (
                            <span className="text-xs text-muted-foreground">
                              {formatTokens(step.input_tokens || 0)} / {formatTokens(step.output_tokens || 0)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
          ))}
        </Tabs>
      )}

      {/* Error */}
      {run.error && (
        <Card className="border-red-500">
          <CardContent className="p-4">
            <p className="text-sm text-red-500">{run.error}</p>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm text-muted-foreground">
          <p>Created: {formatTimestamp(run.created_at)}</p>
          {run.finished_at && <p>Finished: {formatTimestamp(run.finished_at)}</p>}
          <p>Max Iterations: {run.max_iterations}</p>
        </CardContent>
      </Card>
    </div>
  )
}
