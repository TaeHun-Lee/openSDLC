import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useRun } from "@/api/queries/runs"
import { useRunArtifacts } from "@/api/queries/runs"
import { ArtifactList } from "@/components/artifacts/ArtifactList"
import { CodeFileTree } from "@/components/artifacts/CodeFileTree"
import { CodeViewer } from "@/components/artifacts/CodeViewer"
import type { CodeFileInfo } from "@/api/types"

export function ArtifactsPage() {
  const { runId } = useParams()
  const { data: run } = useRun(runId || "")
  const iterations = run?.iterations ?? []

  // Default to last iteration
  const lastIter = iterations.length > 0 ? iterations[iterations.length - 1].iteration_num : undefined
  const [selectedIteration, setSelectedIteration] = useState<number | undefined>(undefined)
  const effectiveIter = selectedIteration ?? lastIter

  const { data: artifacts, isLoading } = useRunArtifacts(runId || "", effectiveIter)
  const [selectedFile, setSelectedFile] = useState<CodeFileInfo | null>(null)

  if (!runId) return <p>No run ID provided.</p>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/runs/${runId}`}>
            <ArrowLeft className="mr-1 h-4 w-4" /> Back to Run
          </Link>
        </Button>
        <h2 className="text-2xl font-bold">Artifacts</h2>
        {run && (
          <span className="text-sm text-muted-foreground">
            Run {run.run_id.slice(0, 8)}... — {run.pipeline_name}
          </span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[200px_1fr]">
        {/* Left: Iteration selector */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Iteration</h3>
          {iterations.length === 0 ? (
            <p className="text-xs text-muted-foreground">No iterations yet</p>
          ) : (
            <div className="flex flex-col gap-1">
              {iterations.map((iter) => (
                <Button
                  key={iter.iteration_num}
                  variant={effectiveIter === iter.iteration_num ? "default" : "ghost"}
                  size="sm"
                  className="justify-start"
                  onClick={() => setSelectedIteration(iter.iteration_num)}
                >
                  Iteration {iter.iteration_num}
                  {iter.satisfaction_score != null && (
                    <span className="ml-auto text-xs opacity-70">
                      score: {iter.satisfaction_score}
                    </span>
                  )}
                </Button>
              ))}
            </div>
          )}
        </div>

        {/* Main: Artifacts + Code tabs */}
        <div>
          {isLoading ? (
            <p className="text-muted-foreground">Loading artifacts...</p>
          ) : !artifacts ? (
            <p className="text-muted-foreground">No artifacts found.</p>
          ) : (
            <Tabs defaultValue="artifacts">
              <TabsList>
                <TabsTrigger value="artifacts">
                  Artifacts ({artifacts.artifacts.length})
                </TabsTrigger>
                <TabsTrigger value="code">
                  Code Files ({artifacts.code_files.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="artifacts" className="mt-4">
                <ArtifactList artifacts={artifacts.artifacts} />
              </TabsContent>

              <TabsContent value="code" className="mt-4">
                {artifacts.code_files.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No code files generated.</p>
                ) : (
                  <div className="grid gap-4 lg:grid-cols-[250px_1fr]">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm">Files</CardTitle>
                      </CardHeader>
                      <CardContent className="p-2">
                        <CodeFileTree
                          files={artifacts.code_files}
                          selectedPath={selectedFile?.path ?? null}
                          onSelect={setSelectedFile}
                        />
                      </CardContent>
                    </Card>
                    <div>
                      {selectedFile ? (
                        <CodeViewer
                          path={selectedFile.path}
                          language={selectedFile.language}
                          content={selectedFile.content}
                        />
                      ) : (
                        <div className="flex h-full items-center justify-center text-sm text-muted-foreground border rounded-lg p-8">
                          Select a file to view
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          )}
        </div>
      </div>
    </div>
  )
}
