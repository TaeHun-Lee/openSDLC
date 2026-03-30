import { useState } from "react"
import { Link, useParams, useNavigate } from "react-router-dom"
import { Plus, Settings2, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { useProjects, useProject } from "@/api/queries/projects"
import { useRuns } from "@/api/queries/runs"
import { useCreateProject } from "@/api/mutations/projects"
import { useResumeRun } from "@/api/mutations/runs"
import { formatRelativeTime } from "@/lib/format"
import { STATUS_COLORS } from "@/lib/constants"
import { cn } from "@/lib/utils"

export function DashboardPage() {
  const { projectId } = useParams()
  const { data: projects } = useProjects()
  const { data: projectDetail } = useProject(projectId || "")
  const { data: runs } = useRuns(projectId)
  const [showCreateDialog, setShowCreateDialog] = useState(false)

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
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to={`/projects/${projectId}/settings`}>
                <Settings2 className="mr-1 h-4 w-4" /> Settings
              </Link>
            </Button>
            <Button asChild>
              <Link to="/runs/new">
                <Plus className="mr-2 h-4 w-4" /> New Run
              </Link>
            </Button>
          </div>
        </div>
        <RunList runs={projectDetail.runs} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowCreateDialog(true)}>
            <Plus className="mr-2 h-4 w-4" /> New Project
          </Button>
          <Button asChild>
            <Link to="/runs/new">
              <Plus className="mr-2 h-4 w-4" /> New Run
            </Link>
          </Button>
        </div>
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

      {/* Create Project Dialog */}
      <CreateProjectDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
      />
    </div>
  )
}

function CreateProjectDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const createMutation = useCreateProject()
  const navigate = useNavigate()
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")

  function handleCreate() {
    if (!name.trim()) return
    createMutation.mutate(
      { name: name.trim(), description },
      {
        onSuccess: (project) => {
          onOpenChange(false)
          setName("")
          setDescription("")
          navigate(`/projects/${project.project_id}`)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Project</DialogTitle>
          <DialogDescription>
            A project groups related runs together.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <Label htmlFor="new-project-name">Name</Label>
            <Input
              id="new-project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Project"
              required
            />
          </div>
          <div>
            <Label htmlFor="new-project-desc">Description</Label>
            <Input
              id="new-project-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
            />
          </div>
          {createMutation.isError && (
            <p className="text-sm text-destructive">
              {(createMutation.error as Error).message ?? "Failed to create project"}
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            disabled={createMutation.isPending || !name.trim()}
          >
            {createMutation.isPending ? "Creating..." : "Create"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function RunList({ runs }: { runs: Array<{ run_id: string; pipeline_name: string; status: string; created_at: number; steps_completed?: number; error?: string | null }> }) {
  const navigate = useNavigate()
  const resumeMutation = useResumeRun()

  if (runs.length === 0) {
    return <p className="text-sm text-muted-foreground">No runs yet.</p>
  }

  const sorted = [...runs].sort((a, b) => b.created_at - a.created_at)
  const canResume = (status: string) => status === "failed" || status === "cancelled"

  function handleResume(runId: string) {
    resumeMutation.mutate(runId, {
      onSuccess: (data) => navigate(`/runs/${data.run_id}`),
    })
  }

  return (
    <div className="space-y-2">
      {sorted.map((run) => (
        <Card key={run.run_id}>
          <CardContent className="flex items-center justify-between p-4">
            <div className="flex items-center gap-3">
              <div className={cn("h-2 w-2 rounded-full", STATUS_COLORS[run.status] || "bg-gray-500")} />
              <div>
                <Link to={`/runs/${run.run_id}`} className="font-medium hover:underline">
                  {run.run_id.slice(0, 8)}...
                </Link>
                <p className="text-sm text-muted-foreground">
                  {run.pipeline_name}
                  {run.steps_completed != null && (
                    <span className="ml-2 text-xs">({run.steps_completed} steps)</span>
                  )}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {canResume(run.status) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleResume(run.run_id)}
                  disabled={resumeMutation.isPending}
                >
                  <RotateCcw className="mr-1 h-3 w-3" /> Resume
                </Button>
              )}
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
