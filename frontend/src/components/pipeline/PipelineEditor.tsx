import { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable"
import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { StepCard } from "./StepCard"
import { useCreatePipeline, useUpdatePipeline } from "@/api/mutations/pipelines"
import { ApiError } from "@/api/client"
import type { PipelineStepInput, PipelineInfo } from "@/api/types"

interface PipelineEditorProps {
  existing?: PipelineInfo
}

export function PipelineEditor({ existing }: PipelineEditorProps) {
  const isEdit = !!existing
  const navigate = useNavigate()
  const createMutation = useCreatePipeline()
  const updateMutation = useUpdatePipeline()

  const [name, setName] = useState(existing?.name ?? "")
  const [description, setDescription] = useState(existing?.description ?? "")
  const [maxIterations, setMaxIterations] = useState(existing?.max_iterations ?? 3)
  const [maxReworks, setMaxReworks] = useState(existing?.max_reworks_per_gate ?? 3)
  const [steps, setSteps] = useState<PipelineStepInput[]>(
    existing?.steps.map((s) => ({
      agent: s.agent,
      model: s.model,
      provider: s.provider,
      mode: s.mode,
      max_tokens: null,
    })) ?? [{ agent: "ReqAgent" }],
  )
  const [error, setError] = useState<string | null>(null)

  // Sortable IDs (stable keys for dnd-kit)
  const [stepIds, setStepIds] = useState<string[]>(() =>
    steps.map(() => crypto.randomUUID()),
  )

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (!over || active.id === over.id) return

    const oldIndex = stepIds.indexOf(String(active.id))
    const newIndex = stepIds.indexOf(String(over.id))

    setSteps((prev) => arrayMove(prev, oldIndex, newIndex))
    setStepIds((prev) => arrayMove(prev, oldIndex, newIndex))
  }

  const handleStepChange = useCallback(
    (index: number, step: PipelineStepInput) => {
      setSteps((prev) => prev.map((s, i) => (i === index ? step : s)))
    },
    [],
  )

  const handleStepRemove = useCallback(
    (index: number) => {
      setSteps((prev) => prev.filter((_, i) => i !== index))
      setStepIds((prev) => prev.filter((_, i) => i !== index))
    },
    [],
  )

  function addStep() {
    setSteps((prev) => [...prev, { agent: "ReqAgent" }])
    setStepIds((prev) => [...prev, crypto.randomUUID()])
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!name.trim() || !/^[a-zA-Z0-9][a-zA-Z0-9_-]*$/.test(name)) {
      setError("Name must start with alphanumeric and contain only letters, digits, hyphens, underscores.")
      return
    }
    if (steps.length === 0) {
      setError("Pipeline must have at least one step.")
      return
    }

    if (isEdit) {
      updateMutation.mutate(
        {
          name: existing!.name,
          body: {
            description,
            max_iterations: maxIterations,
            max_reworks_per_gate: maxReworks,
            steps,
          },
        },
        {
          onSuccess: () => navigate(`/pipelines/${existing!.name}`),
          onError: (err) => {
            if (err instanceof ApiError && err.status === 403) {
              setError("Default pipeline cannot be modified.")
            } else {
              setError((err as Error).message)
            }
          },
        },
      )
    } else {
      createMutation.mutate(
        { name: name.trim(), description, max_iterations: maxIterations, max_reworks_per_gate: maxReworks, steps },
        {
          onSuccess: (created) => navigate(`/pipelines/${created.name}`),
          onError: (err) => {
            if (err instanceof ApiError && err.status === 409) {
              setError("A pipeline with this name already exists.")
            } else {
              setError((err as Error).message)
            }
          },
        },
      )
    }
  }

  const isPending = createMutation.isPending || updateMutation.isPending

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <h2 className="text-2xl font-bold">
        {isEdit ? `Edit: ${existing!.name}` : "New Pipeline"}
      </h2>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Settings</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="sm:col-span-2">
            <Label htmlFor="pipeline-name">Name</Label>
            <Input
              id="pipeline-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isEdit}
              pattern="^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
              maxLength={64}
              placeholder="my-pipeline"
              required
            />
          </div>
          <div className="sm:col-span-2">
            <Label htmlFor="pipeline-desc">Description</Label>
            <Input
              id="pipeline-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description"
            />
          </div>
          <div>
            <Label htmlFor="max-iter">Max Iterations</Label>
            <Input
              id="max-iter"
              type="number"
              min={1}
              max={10}
              value={maxIterations}
              onChange={(e) => setMaxIterations(Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="max-reworks">Max Reworks per Gate</Label>
            <Input
              id="max-reworks"
              type="number"
              min={1}
              max={10}
              value={maxReworks}
              onChange={(e) => setMaxReworks(Number(e.target.value))}
            />
          </div>
        </CardContent>
      </Card>

      {/* Steps */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Steps ({steps.length})</CardTitle>
          <Button type="button" variant="outline" size="sm" onClick={addStep}>
            <Plus className="mr-1 h-4 w-4" /> Add Step
          </Button>
        </CardHeader>
        <CardContent>
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={stepIds} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {steps.map((step, i) => (
                  <StepCard
                    key={stepIds[i]}
                    id={stepIds[i]}
                    index={i}
                    step={step}
                    onChange={handleStepChange}
                    onRemove={handleStepRemove}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
          {steps.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No steps yet. Click "Add Step" to begin.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Error */}
      {error && (
        <p className="text-sm text-destructive">{error}</p>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button type="submit" disabled={isPending}>
          {isPending ? "Saving..." : isEdit ? "Update Pipeline" : "Create Pipeline"}
        </Button>
        <Button type="button" variant="outline" onClick={() => navigate(-1)}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
