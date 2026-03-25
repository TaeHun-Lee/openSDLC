import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Play } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { usePipelines } from "@/api/queries/pipelines"
import { useProjects } from "@/api/queries/projects"
import { useStartRun } from "@/api/mutations/runs"

export function RunStartPage() {
  const navigate = useNavigate()
  const { data: pipelines } = usePipelines()
  const { data: projects } = useProjects()
  const startRun = useStartRun()

  const [userStory, setUserStory] = useState("")
  const [pipeline, setPipeline] = useState("full_spiral")
  const [projectId, setProjectId] = useState("")
  const [error, setError] = useState("")

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (userStory.trim().length < 10) {
      setError("User story must be at least 10 characters.")
      return
    }

    try {
      const result = await startRun.mutateAsync({
        user_story: userStory,
        pipeline,
        project_id: projectId || null,
      })
      navigate(`/runs/${result.run_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start run")
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">Start New Run</h2>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>User Story</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              className="w-full min-h-[120px] rounded-md border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              placeholder="Describe what you want to build..."
              value={userStory}
              onChange={(e) => setUserStory(e.target.value)}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-sm font-medium">Pipeline</label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={pipeline}
                  onChange={(e) => setPipeline(e.target.value)}
                >
                  {pipelines?.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name} ({p.step_count} steps)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-sm font-medium">Project (optional)</label>
                <select
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                >
                  <option value="">No project</option>
                  {projects?.map((p) => (
                    <option key={p.project_id} value={p.project_id}>
                      {p.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-500">{error}</p>
            )}

            <Button type="submit" disabled={startRun.isPending} className="w-full">
              <Play className="mr-2 h-4 w-4" />
              {startRun.isPending ? "Starting..." : "Start Run"}
            </Button>
          </CardContent>
        </Card>
      </form>
    </div>
  )
}
