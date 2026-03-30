import { useParams } from "react-router-dom"
import { usePipeline } from "@/api/queries/pipelines"
import { PipelineEditor } from "@/components/pipeline/PipelineEditor"

export function PipelineEditorPage() {
  const { name } = useParams()

  if (name) {
    return <EditMode name={name} />
  }

  return <PipelineEditor />
}

function EditMode({ name }: { name: string }) {
  const { data: pipeline, isLoading } = usePipeline(name)

  if (isLoading) return <p className="text-muted-foreground">Loading...</p>
  if (!pipeline) return <p className="text-muted-foreground">Pipeline not found.</p>

  return <PipelineEditor existing={pipeline} />
}
