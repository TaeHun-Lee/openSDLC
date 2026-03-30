import { useParams, Link, useNavigate } from "react-router-dom"
import { useRun } from "@/api/queries/runs"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FileText, BarChart3, Copy } from "lucide-react"
import { Button } from "@/components/ui/button"
import { formatTimestamp } from "@/lib/format"
import { STATUS_COLORS } from "@/lib/constants"
import { cn } from "@/lib/utils"
import { useSSEStream } from "@/hooks/use-sse-stream"
import { useSSEStore } from "@/stores/sse-store"
import { RunProgress } from "@/components/run/RunProgress"
import { ProgressTimeline } from "@/components/run/ProgressTimeline"
import { ConnectionStatus } from "@/components/run/ConnectionStatus"
import { NarrativePanel } from "@/components/narrative/NarrativePanel"
import { RunActionButtons } from "@/components/run/CancelButton"
import { useStartRun } from "@/api/mutations/runs"

export function RunPage() {
  const navigate = useNavigate()
  const { runId } = useParams()
  const { data: run, isLoading } = useRun(runId || "")
  const cloneMutation = useStartRun()
  const sseStatus = useSSEStore((s) => s.status)
  const sseStep = useSSEStore((s) => s.currentStep)
  const sseAgent = useSSEStore((s) => s.currentAgent)

  const isActive = run?.status === "running" || run?.status === "pending"
  const { connectionState, reconnectAttempt, manualReconnect } = useSSEStream(
    runId || "",
    !!runId && !!run,
  )

  if (!runId) return <p>No run ID provided.</p>
  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (!run) return <p className="text-muted-foreground">Run not found.</p>

  // SSE real-time status takes precedence once connected;
  // while SSE is still idle (connecting), trust the DB status.
  const displayStatus =
    sseStatus !== "idle" ? sseStatus : run.status

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Run {run.run_id.slice(0, 8)}...</h2>
          <p className="text-muted-foreground">{run.pipeline_name}</p>
        </div>
        <div className="flex items-center gap-3">
          {isActive && (
            <ConnectionStatus
              state={connectionState}
              reconnectAttempt={reconnectAttempt}
              onReconnect={manualReconnect}
            />
          )}
          <div className="flex items-center gap-2">
            <div className={cn("h-2 w-2 rounded-full", STATUS_COLORS[displayStatus])} />
            <Badge variant={displayStatus === "completed" ? "default" : displayStatus === "failed" ? "destructive" : "secondary"}>
              {displayStatus}
            </Badge>
          </div>
          <RunActionButtons runId={run.run_id} status={displayStatus} />
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

      {/* Live Progress (running only) */}
      {(displayStatus === "running" || displayStatus === "pending") && (
        <RunProgress maxIterations={run.max_iterations} startedAt={run.created_at} />
      )}

      {/* Main content: Timeline + Narrative side by side */}
      <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
        {/* Left: Timeline */}
        <div className="space-y-4 h-[500px] overflow-y-scroll">
          {run.iterations.length > 0 && (
            <Tabs defaultValue={String(run.iterations[run.iterations.length - 1].iteration_num)}>
              <TabsList className="w-full">
                {run.iterations.map((iter) => (
                  <TabsTrigger key={iter.iteration_num} value={String(iter.iteration_num)} className="flex-1">
                    Iter {iter.iteration_num}
                    {iter.satisfaction_score != null && (
                      <Badge variant="outline" className="ml-1 text-[10px]">{iter.satisfaction_score}</Badge>
                    )}
                  </TabsTrigger>
                ))}
              </TabsList>
              {run.iterations.map((iter) => (
                <TabsContent key={iter.iteration_num} value={String(iter.iteration_num)}>
                  <ProgressTimeline
                    steps={iter.steps}
                    currentStepNum={sseStep}
                    currentAgent={sseAgent}
                  />
                </TabsContent>
              ))}
            </Tabs>
          )}
        </div>

        {/* Right: Narrative */}
        <Card className="min-h-[400px]">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Agent Narrative</CardTitle>
          </CardHeader>
          <CardContent className="h-[500px] p-0">
            <NarrativePanel />
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="flex gap-2">
        <Button variant="outline" size="sm" asChild>
          <Link to={`/runs/${runId}/artifacts`}>
            <FileText className="mr-1 h-4 w-4" /> View Artifacts
          </Link>
        </Button>
        <Button variant="outline" size="sm" asChild>
          <Link to={`/runs/${runId}/usage`}>
            <BarChart3 className="mr-1 h-4 w-4" /> Token Usage
          </Link>
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={cloneMutation.isPending}
          onClick={() => {
            cloneMutation.mutate(
              {
                user_story: run.user_story,
                pipeline: run.pipeline_name,
                project_id: run.project_id,
                max_iterations: run.max_iterations,
              },
              { onSuccess: (data) => navigate(`/runs/${data.run_id}`) },
            )
          }}
        >
          <Copy className="mr-1 h-4 w-4" /> {cloneMutation.isPending ? "Cloning..." : "Clone Run"}
        </Button>
      </div>

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
