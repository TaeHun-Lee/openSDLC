// Backend Pydantic models → TypeScript interfaces
// Matches backend/app/models/responses.py 1:1

// --- Pipeline ---

export interface StepInfo {
  step: number
  agent: string
  model: string | null
  provider: string | null
  on_fail: string | null
  on_next_iteration: string | null
  mode: string | null
}

export interface PipelineInfo {
  name: string
  description: string
  max_iterations: number
  max_reworks_per_gate: number
  steps: StepInfo[]
  is_default: boolean
}

export interface PipelineListItem {
  name: string
  description: string
  step_count: number
  is_default: boolean
}

// --- Agent ---

export interface AgentInfo {
  agent_id: string
  display_name: string
  role: string
  primary_inputs: string[]
  primary_outputs: string[]
}

// --- Project ---

export interface ProjectInfo {
  project_id: string
  name: string
  description: string
  created_at: number
  run_count: number
}

export interface ProjectDetail {
  project_id: string
  name: string
  description: string
  created_at: number
  runs: RunSummary[]
}

// --- Run ---

export interface RunCreated {
  run_id: string
  status: string
  pipeline: string
}

export interface StepResultInfo {
  step_id: string
  agent_id: string
  artifact_type: string
  model_used: string
  validation_result: string | null
  narrative: string
}

export interface ArtifactRef {
  artifact_type: string | null
  artifact_id: string | null
  file_path: string
}

export interface CodeFileRef {
  relative_path: string
  file_path: string
  size_bytes: number | null
}

export interface StepDetailInfo {
  step_num: number
  agent_name: string
  mode: string | null
  verdict: string | null
  model_used: string | null
  provider: string | null
  input_tokens: number | null
  output_tokens: number | null
  cache_read_tokens: number | null
  cache_creation_tokens: number | null
  rework_seq: number
  started_at: number | null
  finished_at: number | null
  artifacts: ArtifactRef[]
}

export interface IterationInfo {
  iteration_num: number
  status: string
  satisfaction_score: number | null
  started_at: number | null
  finished_at: number | null
  steps: StepDetailInfo[]
  code_files: CodeFileRef[]
}

export interface RunSummary {
  run_id: string
  pipeline_name: string
  status: string
  created_at: number
  finished_at: number | null
  steps_completed: number
  error: string | null
}

export interface RunDetail {
  run_id: string
  pipeline_name: string
  user_story: string
  status: string
  max_iterations: number
  project_id: string | null
  created_at: number
  finished_at: number | null
  iterations: IterationInfo[]
  steps: StepResultInfo[]
  artifacts: Record<string, string>
  error: string | null
}

export interface ArtifactInfo {
  artifact_type: string
  artifact_id: string | null
  yaml_content: string
}

export interface CodeFileInfo {
  path: string
  language: string
  content: string
}

export interface RunArtifacts {
  run_id: string
  artifacts: ArtifactInfo[]
  code_files: CodeFileInfo[]
  runtime_info: Record<string, string>
}

// --- Events ---

export interface EventInfo {
  id: number
  event_type: string
  agent_name: string | null
  message: string | null
  iteration_num: number | null
  created_at: number
  data?: Record<string, unknown> | null
}

// --- Usage ---

export interface ModelUsage {
  steps: number
  input_tokens: number
  output_tokens: number
  provider: string | null
}

export interface AgentUsage {
  steps: number
  input_tokens: number
  output_tokens: number
}

export interface IterationUsage {
  iteration_num: number
  input_tokens: number
  output_tokens: number
  step_count: number
}

export interface RunUsage {
  run_id: string
  total_input_tokens: number
  total_output_tokens: number
  total_cache_read_tokens: number
  total_cache_creation_tokens: number
  by_model: Record<string, ModelUsage>
  by_agent: Record<string, AgentUsage>
  by_iteration: IterationUsage[]
}

export interface ProjectUsage {
  project_id: string
  total_runs: number
  total_input_tokens: number
  total_output_tokens: number
  total_cache_read_tokens: number
  total_cache_creation_tokens: number
  by_model: Record<string, ModelUsage>
  by_pipeline: Record<string, { runs: number; input_tokens: number; output_tokens: number }>
}

// --- Validation ---

export interface ValidationIssue {
  type: string
  step: number | null
  agent: string | null
  provider: string | null
  message: string
}

export interface ArtifactFlowStep {
  step: number
  agent: string
  produces: string[]
  consumes: string[]
}

export interface PipelineValidationResult {
  valid: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  artifact_flow: ArtifactFlowStep[]
}

// --- Health ---

export interface HealthResponse {
  status: string
  llm_provider: string
  model: string
}

// --- Requests ---

export interface PipelineStepInput {
  agent: string
  model?: string | null
  provider?: string | null
  mode?: string | null
  max_tokens?: number | null
}

export interface CreatePipelineRequest {
  name: string
  description?: string
  max_iterations?: number
  max_reworks_per_gate?: number
  steps: PipelineStepInput[]
}

export interface UpdatePipelineRequest {
  description?: string | null
  max_iterations?: number | null
  max_reworks_per_gate?: number | null
  steps?: PipelineStepInput[] | null
}

export interface StartRunRequest {
  user_story: string
  pipeline?: string
  project_id?: string | null
  max_iterations?: number | null
}

export interface CreateProjectRequest {
  name: string
  description?: string
}

export interface UpdateProjectRequest {
  name?: string | null
  description?: string | null
}
