import { useParams } from "react-router-dom"
import { ProjectSettings } from "@/components/project/ProjectSettings"

export function ProjectSettingsPage() {
  const { projectId } = useParams()

  if (!projectId) return <p className="text-muted-foreground">No project ID provided.</p>

  return <ProjectSettings projectId={projectId} />
}
