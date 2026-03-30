import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ArtifactViewer } from "./ArtifactViewer"
import type { ArtifactInfo } from "@/api/types"

interface ArtifactListProps {
  artifacts: ArtifactInfo[]
}

export function ArtifactList({ artifacts }: ArtifactListProps) {
  if (artifacts.length === 0) {
    return <p className="text-sm text-muted-foreground py-4">No artifacts available.</p>
  }

  const types = [...new Set(artifacts.map((a) => a.artifact_type))]

  if (types.length === 1) {
    return (
      <div className="space-y-4">
        {artifacts.map((a, i) => (
          <ArtifactViewer
            key={i}
            artifactType={a.artifact_type}
            artifactId={a.artifact_id}
            content={a.yaml_content}
            defaultCollapsed={artifacts.length > 2}
          />
        ))}
      </div>
    )
  }

  return (
    <Tabs defaultValue={types[0]}>
      <TabsList>
        {types.map((type) => (
          <TabsTrigger key={type} value={type}>
            {type.replace("Artifact", "")}
          </TabsTrigger>
        ))}
      </TabsList>
      {types.map((type) => (
        <TabsContent key={type} value={type} className="space-y-4">
          {artifacts
            .filter((a) => a.artifact_type === type)
            .map((a, i) => (
              <ArtifactViewer
                key={i}
                artifactType={a.artifact_type}
                artifactId={a.artifact_id}
                content={a.yaml_content}
              />
            ))}
        </TabsContent>
      ))}
    </Tabs>
  )
}
