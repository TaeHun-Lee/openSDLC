import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Play, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { ValidationBanner } from "@/components/pipeline/ValidationBanner"
import { usePipelines, usePipeline } from "@/api/queries/pipelines"
import { useProjects } from "@/api/queries/projects"
import { useStartRun } from "@/api/mutations/runs"
import { api } from "@/api/client"
import { ApiError } from "@/api/client"
import type { PipelineValidationResult } from "@/api/types"

export function RunStartPage() {
  const navigate = useNavigate()
  const { data: pipelines } = usePipelines()
  const { data: projects } = useProjects()
  const startRun = useStartRun()

  const [userStory, setUserStory] = useState("")
  const [pipeline, setPipeline] = useState("")
  const [projectId, setProjectId] = useState("")
  const [error, setError] = useState("")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [maxIterations, setMaxIterations] = useState<number | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<PipelineValidationResult | null>(null)
  const [showWarningDialog, setShowWarningDialog] = useState(false)

  // Set default pipeline from API (is_default flag) once loaded
  useEffect(() => {
    if (pipelines && pipelines.length > 0 && !pipeline) {
      const defaultPipeline = pipelines.find((p) => p.is_default)
      setPipeline(defaultPipeline?.name ?? pipelines[0].name)
    }
  }, [pipelines, pipeline])

  const { data: selectedPipeline } = usePipeline(pipeline)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")

    if (userStory.trim().length < 10) {
      setError("User story must be at least 10 characters.")
      return
    }

    // Pre-run validation
    setIsValidating(true)
    try {
      const result = await api.post<PipelineValidationResult>(
        `/pipelines/${pipeline}/validate`,
      )
      setValidationResult(result)

      if (result.errors.length > 0) {
        setIsValidating(false)
        return // Block — errors shown via ValidationBanner
      }

      if (result.warnings.length > 0) {
        setIsValidating(false)
        setShowWarningDialog(true)
        return // Show warning confirmation
      }

      // Valid — proceed
      await doStartRun()
    } catch {
      setError("Failed to validate pipeline.")
    } finally {
      setIsValidating(false)
    }
  }

  async function doStartRun() {
    try {
      const result = await startRun.mutateAsync({
        user_story: userStory,
        pipeline,
        project_id: projectId || null,
        ...(maxIterations != null ? { max_iterations: maxIterations } : {}),
      })
      navigate(`/runs/${result.run_id}`)
    } catch (err) {
      if (err instanceof ApiError && (err.status === 503 || err.status === 429)) {
        setError("Maximum concurrent runs reached. Please wait and try again.")
      } else {
        setError(err instanceof Error ? err.message : "Failed to start run")
      }
    }
  }

  function handleWarningConfirm() {
    setShowWarningDialog(false)
    doStartRun()
  }

  const effectiveMaxIter = maxIterations ?? selectedPipeline?.max_iterations ?? 3

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
                <Label>Pipeline</Label>
                <select
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                  value={pipeline}
                  onChange={(e) => {
                    setPipeline(e.target.value)
                    setValidationResult(null)
                    setMaxIterations(null)
                  }}
                >
                  {pipelines?.map((p) => (
                    <option key={p.name} value={p.name}>
                      {p.name} ({p.step_count} steps)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label>Project (optional)</Label>
                <select
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
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

            {/* Advanced Settings */}
            <button
              type="button"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              Advanced Settings
            </button>

            {showAdvanced && (
              <div className="rounded-lg border p-4 space-y-3">
                <div>
                  <Label htmlFor="max-iter-slider">
                    Max Iterations: {effectiveMaxIter}
                  </Label>
                  <Input
                    id="max-iter-slider"
                    type="range"
                    min={1}
                    max={10}
                    value={effectiveMaxIter}
                    onChange={(e) => setMaxIterations(Number(e.target.value))}
                    className="mt-1"
                  />
                  <div className="flex justify-between text-xs text-muted-foreground mt-1">
                    <span>1</span>
                    <span>10</span>
                  </div>
                </div>
              </div>
            )}

            {/* Validation result */}
            {validationResult && validationResult.errors.length > 0 && (
              <ValidationBanner result={validationResult} />
            )}

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}

            <Button
              type="submit"
              disabled={startRun.isPending || isValidating || !pipeline}
              className="w-full"
            >
              <Play className="mr-2 h-4 w-4" />
              {isValidating
                ? "Validating..."
                : startRun.isPending
                  ? "Starting..."
                  : "Start Run"}
            </Button>
          </CardContent>
        </Card>
      </form>

      {/* Warning confirmation dialog */}
      <Dialog open={showWarningDialog} onOpenChange={setShowWarningDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Pipeline Warnings</DialogTitle>
            <DialogDescription>
              The pipeline validation found warnings. Do you want to proceed anyway?
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[40vh] overflow-y-auto">
            {validationResult && <ValidationBanner result={validationResult} />}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWarningDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleWarningConfirm} disabled={startRun.isPending}>
              {startRun.isPending ? "Starting..." : "Proceed Anyway"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
