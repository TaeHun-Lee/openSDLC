import { useParams, Link } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useRunUsage } from "@/api/queries/runs"
import { useProjectUsage } from "@/api/queries/projects"
import { UsageSummary } from "@/components/usage/UsageSummary"
import { TokenUsageChart } from "@/components/usage/TokenUsageChart"

function RunUsageView({ runId }: { runId: string }) {
  const { data, isLoading } = useRunUsage(runId)

  if (isLoading) return <p className="text-muted-foreground">Loading usage data...</p>
  if (!data) return <p className="text-muted-foreground">No usage data available.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/runs/${runId}`}>
            <ArrowLeft className="mr-1 h-4 w-4" /> Back to Run
          </Link>
        </Button>
        <h2 className="text-2xl font-bold">Token Usage</h2>
        <span className="text-sm text-muted-foreground">Run {runId.slice(0, 8)}...</span>
      </div>

      <UsageSummary
        inputTokens={data.total_input_tokens}
        outputTokens={data.total_output_tokens}
        cacheReadTokens={data.total_cache_read_tokens}
        cacheCreationTokens={data.total_cache_creation_tokens}
      />

      <TokenUsageChart
        byModel={data.by_model}
        byAgent={data.by_agent}
        byIteration={data.by_iteration}
      />
    </div>
  )
}

function ProjectUsageView({ projectId }: { projectId: string }) {
  const { data, isLoading } = useProjectUsage(projectId)

  if (isLoading) return <p className="text-muted-foreground">Loading usage data...</p>
  if (!data) return <p className="text-muted-foreground">No usage data available.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/projects/${projectId}`}>
            <ArrowLeft className="mr-1 h-4 w-4" /> Back to Project
          </Link>
        </Button>
        <h2 className="text-2xl font-bold">Project Token Usage</h2>
      </div>

      <UsageSummary
        inputTokens={data.total_input_tokens}
        outputTokens={data.total_output_tokens}
        cacheReadTokens={data.total_cache_read_tokens}
        cacheCreationTokens={data.total_cache_creation_tokens}
      />

      <TokenUsageChart
        byModel={data.by_model}
        byAgent={{}}
        byIteration={[]}
      />

      {/* Pipeline breakdown */}
      {Object.keys(data.by_pipeline).length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">By Pipeline</h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(data.by_pipeline).map(([name, info]) => (
              <div key={name} className="rounded-lg border p-3 text-sm">
                <p className="font-medium">{name}</p>
                <p className="text-muted-foreground">
                  {info.runs} run{info.runs !== 1 ? "s" : ""} — {((info.input_tokens + info.output_tokens) / 1000).toFixed(1)}K tokens
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function UsagePage() {
  const { runId, projectId } = useParams()

  if (runId) return <RunUsageView runId={runId} />
  if (projectId) return <ProjectUsageView projectId={projectId} />
  return <p className="text-muted-foreground">No run or project specified.</p>
}
