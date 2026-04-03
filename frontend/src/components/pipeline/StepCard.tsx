import { useSortable } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { GripVertical, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select"
import { AgentPicker } from "./AgentPicker"
import type { PipelineStepInput } from "@/api/types"

interface StepCardProps {
  id: string
  index: number
  step: PipelineStepInput
  onChange: (index: number, step: PipelineStepInput) => void
  onRemove: (index: number) => void
}

export function StepCard({ id, index, step, onChange, onRemove }: StepCardProps) {
  const {
    attributes, listeners, setNodeRef, transform, transition, isDragging,
  } = useSortable({ id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  function update(patch: Partial<PipelineStepInput>) {
    onChange(index, { ...step, ...patch })
  }

  const isTestAgent = step.agent === "TestAgent"

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-start gap-3 rounded-lg border bg-card p-4"
    >
      {/* Drag handle */}
      <button
        type="button"
        className="mt-1 cursor-grab touch-none text-muted-foreground hover:text-foreground"
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-5 w-5" />
      </button>

      {/* Step number */}
      <span className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium">
        {index + 1}
      </span>

      {/* Fields */}
      <div className="flex-1 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="sm:col-span-2 lg:col-span-1">
          <Label className="text-xs">Agent</Label>
          <AgentPicker value={step.agent} onChange={(v) => update({ agent: v })} />
        </div>

        <div>
          <Label className="text-xs">Provider</Label>
          <Select
            value={step.provider ?? ""}
            onValueChange={(v) => update({ provider: v || null })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Default" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="anthropic">Anthropic</SelectItem>
              <SelectItem value="google">Google</SelectItem>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="ollama">Ollama</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="text-xs">Model</Label>
          <Input
            value={step.model ?? ""}
            onChange={(e) => update({ model: e.target.value || null })}
            placeholder="Default"
          />
        </div>

        {isTestAgent && (
          <div>
            <Label className="text-xs">Mode</Label>
            <Select
              value={step.mode ?? ""}
              onValueChange={(v) => update({ mode: v || null })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="design">Design</SelectItem>
                <SelectItem value="execution">Execution</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <div>
          <Label className="text-xs">Max Tokens</Label>
          <Input
            type="number"
            value={step.max_tokens ?? ""}
            onChange={(e) =>
              update({ max_tokens: e.target.value ? Number(e.target.value) : null })
            }
            placeholder="Default"
          />
        </div>
      </div>

      {/* Remove */}
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="mt-1 shrink-0 text-muted-foreground hover:text-destructive"
        onClick={() => onRemove(index)}
      >
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  )
}
