import { useState } from "react"
import { Link, useParams, useNavigate } from "react-router-dom"
import {
  Plus, Shield, GitBranch, Copy, Trash2, Pencil,
  RotateCcw, Bot, ArrowDownUp, CheckCircle2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { usePipelines, usePipeline } from "@/api/queries/pipelines"
import { useAgents } from "@/api/queries/agents"
import { useDeletePipeline, useCreatePipeline } from "@/api/mutations/pipelines"
import { useValidatePipeline } from "@/api/queries/pipelines"
import { ValidationBanner } from "@/components/pipeline/ValidationBanner"
import { PipelineFlowView } from "@/components/pipeline/PipelineFlowView"
import { AGENT_COLORS, AGENT_BG_COLORS } from "@/lib/constants"
import type { AgentInfo, PipelineInfo } from "@/api/types"

export function PipelinePage() {
  const { name } = useParams()

  if (name) {
    return <PipelineDetail name={name} />
  }

  return <PipelineList />
}

// ---------------------------------------------------------------------------
// Pipeline List
// ---------------------------------------------------------------------------

function PipelineList() {
  const { data: pipelines, isLoading } = usePipelines()
  const { data: agents, isLoading: agentsLoading } = useAgents()

  return (
    <div className="space-y-8">
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

      {/* Agent Palette */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Bot className="h-5 w-5" /> Available Agents
        </h3>
        {agentsLoading ? (
          <p className="text-muted-foreground">Loading agents...</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents?.map((agent) => (
              <AgentCard key={agent.agent_id} agent={agent} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Agent Card
// ---------------------------------------------------------------------------

function AgentCard({ agent }: { agent: AgentInfo }) {
  const colorClass = AGENT_COLORS[agent.agent_id] ?? "text-foreground"
  const bgClass = AGENT_BG_COLORS[agent.agent_id] ?? "bg-muted"

  return (
    <Card className={bgClass}>
      <CardHeader className="pb-2">
        <CardTitle className={`text-base ${colorClass}`}>
          {agent.display_name}
        </CardTitle>
        <CardDescription>{agent.role}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {agent.primary_inputs.length > 0 && (
          <div>
            <span className="font-medium text-muted-foreground">Inputs: </span>
            {agent.primary_inputs.map((input) => (
              <Badge key={input} variant="outline" className="mr-1 mb-1">{input}</Badge>
            ))}
          </div>
        )}
        {agent.primary_outputs.length > 0 && (
          <div>
            <span className="font-medium text-muted-foreground">Outputs: </span>
            {agent.primary_outputs.map((output) => (
              <Badge key={output} variant="secondary" className="mr-1 mb-1">{output}</Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ---------------------------------------------------------------------------
// Pipeline Detail
// ---------------------------------------------------------------------------

function PipelineDetail({ name }: { name: string }) {
  const { data: pipeline, isLoading } = usePipeline(name)
  const deleteMutation = useDeletePipeline()
  const cloneMutation = useCreatePipeline()
  const navigate = useNavigate()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showCloneDialog, setShowCloneDialog] = useState(false)
  const [cloneName, setCloneName] = useState("")
  const [validateEnabled, setValidateEnabled] = useState(false)
  const { data: validationResult, isFetching: isValidating } = useValidatePipeline(name, validateEnabled)

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (!pipeline) return <p className="text-muted-foreground">Pipeline not found.</p>

  function handleDelete() {
    deleteMutation.mutate(name, {
      onSuccess: () => {
        setShowDeleteDialog(false)
        navigate("/pipelines")
      },
    })
  }

  function handleClone() {
    if (!pipeline || !cloneName.trim()) return
    cloneMutation.mutate(
      {
        name: cloneName.trim(),
        description: pipeline.description,
        max_iterations: pipeline.max_iterations,
        max_reworks_per_gate: pipeline.max_reworks_per_gate,
        steps: pipeline.steps.map((s) => ({
          agent: s.agent,
          model: s.model,
          provider: s.provider,
          mode: s.mode,
        })),
      },
      {
        onSuccess: (created) => {
          setShowCloneDialog(false)
          navigate(`/pipelines/${created.name}`)
        },
      },
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">{pipeline.name}</h2>
          {pipeline.description && (
            <p className="text-muted-foreground">{pipeline.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {pipeline.is_default ? (
            <Badge variant="secondary">
              <Shield className="mr-1 h-3 w-3" />Default (read-only)
            </Badge>
          ) : (
            <>
              <Button variant="outline" size="sm" asChild>
                <Link to={`/pipelines/${name}/edit`}>
                  <Pencil className="mr-1 h-3 w-3" /> Edit
                </Link>
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowDeleteDialog(true)}
              >
                <Trash2 className="mr-1 h-3 w-3" /> Delete
              </Button>
            </>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setCloneName(`${pipeline.name}-copy`)
              setShowCloneDialog(true)
            }}
          >
            <Copy className="mr-1 h-3 w-3" /> Clone
          </Button>
          {pipeline.is_default && (
            <Tooltip>
              <TooltipTrigger asChild>
                <span>
                  <Button variant="outline" size="sm" disabled>
                    <Pencil className="mr-1 h-3 w-3" /> Edit
                  </Button>
                </span>
              </TooltipTrigger>
              <TooltipContent>Default pipeline cannot be modified</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p>Max Iterations: {pipeline.max_iterations}</p>
          <p>Max Reworks per Gate: {pipeline.max_reworks_per_gate}</p>
        </CardContent>
      </Card>

      {/* Steps */}
      <Card>
        <CardHeader>
          <CardTitle>Steps ({pipeline.steps.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {pipeline.steps.map((step) => (
              <StepRow key={step.step} step={step} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Validation */}
      <div className="space-y-4">
        <Button
          variant="outline"
          onClick={() => setValidateEnabled(true)}
          disabled={isValidating}
        >
          <CheckCircle2 className="mr-2 h-4 w-4" />
          {isValidating ? "Validating..." : "Validate Pipeline"}
        </Button>
        {validationResult && (
          <>
            <ValidationBanner result={validationResult} />
            {validationResult.artifact_flow.length > 0 && (
              <PipelineFlowView flow={validationResult.artifact_flow} />
            )}
          </>
        )}
      </div>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Pipeline</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clone Dialog */}
      <Dialog open={showCloneDialog} onOpenChange={setShowCloneDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clone Pipeline</DialogTitle>
            <DialogDescription>
              Create a copy of "{pipeline.name}" with a new name.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium">New Pipeline Name</label>
            <input
              className="mt-1 flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={cloneName}
              onChange={(e) => setCloneName(e.target.value)}
              pattern="^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
              maxLength={64}
              placeholder="my-pipeline-copy"
            />
            {cloneMutation.isError && (
              <p className="mt-2 text-sm text-destructive">
                {(cloneMutation.error as Error).message ?? "Failed to clone pipeline"}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCloneDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleClone}
              disabled={cloneMutation.isPending || !cloneName.trim()}
            >
              {cloneMutation.isPending ? "Cloning..." : "Clone"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step Row — shows on_fail, on_next_iteration, model, mode
// ---------------------------------------------------------------------------

function StepRow({ step }: { step: PipelineInfo["steps"][number] }) {
  const colorClass = AGENT_COLORS[step.agent] ?? "text-foreground"

  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-muted text-sm font-medium">
          {step.step}
        </span>
        <div>
          <p className={`font-medium ${colorClass}`}>{step.agent}</p>
          {step.mode && (
            <p className="text-xs text-muted-foreground">mode: {step.mode}</p>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {step.model && <Badge variant="outline">{step.model}</Badge>}
        {step.on_fail && (
          <Badge variant="destructive" className="flex items-center gap-1">
            <RotateCcw className="h-3 w-3" />on_fail: {step.on_fail}
          </Badge>
        )}
        {step.on_next_iteration && (
          <Badge className="flex items-center gap-1 bg-purple-500/10 text-purple-600 border-purple-300">
            <ArrowDownUp className="h-3 w-3" />next_iter: {step.on_next_iteration}
          </Badge>
        )}
      </div>
    </div>
  )
}
