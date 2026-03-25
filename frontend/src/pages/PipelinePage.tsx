import { Link, useParams } from "react-router-dom"
import { Plus, Shield, GitBranch } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { usePipelines, usePipeline } from "@/api/queries/pipelines"

export function PipelinePage() {
  const { name } = useParams()

  if (name) {
    return <PipelineDetail name={name} />
  }

  return <PipelineList />
}

function PipelineList() {
  const { data: pipelines, isLoading } = usePipelines()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Pipelines</h2>
        <Button asChild>
          <Link to="/pipelines/new">
            <Plus className="mr-2 h-4 w-4" /> New Pipeline
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {pipelines?.map((pipeline) => (
            <Card key={pipeline.name}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2">
                  <GitBranch className="h-4 w-4" />
                  <Link to={`/pipelines/${pipeline.name}`} className="hover:underline">
                    {pipeline.name}
                  </Link>
                  {pipeline.is_default && (
                    <Badge variant="secondary"><Shield className="mr-1 h-3 w-3" />Default</Badge>
                  )}
                </CardTitle>
                {pipeline.description && (
                  <CardDescription>{pipeline.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {pipeline.step_count} step{pipeline.step_count !== 1 ? "s" : ""}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}

function PipelineDetail({ name }: { name: string }) {
  const { data: pipeline, isLoading } = usePipeline(name)

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (!pipeline) return <p className="text-muted-foreground">Pipeline not found.</p>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{pipeline.name}</h2>
          {pipeline.description && (
            <p className="text-muted-foreground">{pipeline.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {pipeline.is_default && (
            <Badge variant="secondary"><Shield className="mr-1 h-3 w-3" />Default (read-only)</Badge>
          )}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Max Iterations: {pipeline.max_iterations}</p>
          <p>Max Reworks per Gate: {pipeline.max_reworks_per_gate}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Steps ({pipeline.steps.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {pipeline.steps.map((step) => (
              <div
                key={step.step}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-sm font-medium">
                    {step.step}
                  </span>
                  <div>
                    <p className="font-medium">{step.agent}</p>
                    {step.mode && <p className="text-xs text-muted-foreground">mode: {step.mode}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {step.model && <Badge variant="outline">{step.model}</Badge>}
                  {step.on_fail && (
                    <Badge variant="destructive">on_fail: {step.on_fail}</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
