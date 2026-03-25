import { Link, useParams } from "react-router-dom"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useProjects } from "@/api/queries/projects"
import { useProject } from "@/api/queries/projects"
import { useRuns } from "@/api/queries/runs"
import { formatRelativeTime } from "@/lib/format"
import { STATUS_COLORS } from "@/lib/constants"
import { cn } from "@/lib/utils"

export function DashboardPage() {
  const { projectId } = useParams()
  const { data: projects } = useProjects()
  const { data: projectDetail } = useProject(projectId || "")
  const { data: runs } = useRuns(projectId)

  if (projectId && projectDetail) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{projectDetail.name}</h2>
            {projectDetail.description && (
              <p className="text-muted-foreground">{projectDetail.description}</p>
            )}
          </div>
          <Button asChild>
            <Link to="/runs/new">
              <Plus className="mr-2 h-4 w-4" /> New Run
            </Link>
          </Button>
        </div>
        <RunList runs={projectDetail.runs} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <Button asChild>
          <Link to="/runs/new">
            <Plus className="mr-2 h-4 w-4" /> New Run
          </Link>
        </Button>
      </div>

      {/* Projects */}
      {projects && projects.length > 0 && (
        <section>
          <h3 className="mb-3 text-lg font-semibold">Projects</h3>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Card key={project.project_id}>
                <CardHeader className="pb-2">
                  <CardTitle>
                    <Link
                      to={`/projects/${project.project_id}`}
                      className="hover:underline"
                    >
                      {project.name}
                    </Link>
                  </CardTitle>
                  {project.description && (
                    <CardDescription>{project.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {project.run_count} run{project.run_count !== 1 ? "s" : ""}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* Recent Runs */}
      <section>
        <h3 className="mb-3 text-lg font-semibold">Recent Runs</h3>
        <RunList runs={runs || []} />
      </section>
    </div>
  )
}

function RunList({ runs }: { runs: Array<{ run_id: string; pipeline_name: string; status: string; created_at: number; error?: string | null }> }) {
  if (runs.length === 0) {
    return <p className="text-sm text-muted-foreground">No runs yet.</p>
  }

  return (
    <div className="space-y-2">
      {runs.map((run) => (
        <Card key={run.run_id}>
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className={cn("h-2 w-2 rounded-full", STATUS_COLORS[run.status] || "bg-gray-500")} />
              <div>
                <Link to={`/runs/${run.run_id}`} className="font-medium hover:underline">
                  {run.run_id.slice(0, 8)}...
                </Link>
                <p className="text-sm text-muted-foreground">{run.pipeline_name}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Badge variant={run.status === "completed" ? "default" : run.status === "failed" ? "destructive" : "secondary"}>
                {run.status}
              </Badge>
              <span className="text-sm text-muted-foreground">
                {formatRelativeTime(run.created_at)}
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
