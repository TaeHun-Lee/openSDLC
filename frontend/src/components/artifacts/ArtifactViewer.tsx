import { useState, useEffect, useRef, useMemo } from "react"
import DOMPurify from "dompurify"
import { Copy, Check, ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

interface ArtifactViewerProps {
  artifactType: string
  artifactId: string | null
  content: string
  language?: string
  defaultCollapsed?: boolean
}

export function ArtifactViewer({
  artifactType,
  artifactId,
  content,
  language = "yaml",
  defaultCollapsed = false,
}: ArtifactViewerProps) {
  const [html, setHtml] = useState<string>("")
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const [copied, setCopied] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    async function highlight() {
      const { getHighlighter } = await import("@/lib/shiki")
      const highlighter = await getHighlighter()
      const result = highlighter.codeToHtml(content, {
        lang: language,
        themes: { light: "github-light", dark: "github-dark" },
      })
      if (!cancelled) setHtml(result)
    }
    highlight()
    return () => { cancelled = true }
  }, [content, language])

  async function handleCopy() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const safeHtml = useMemo(() => html ? DOMPurify.sanitize(html) : "", [html])

  const lineCount = content.split("\n").length
  const isLong = lineCount > 50

  return (
    <div className="rounded-lg border">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <Badge variant="secondary">{artifactType}</Badge>
          {artifactId && (
            <span className="text-xs text-muted-foreground">{artifactId}</span>
          )}
          <span className="text-xs text-muted-foreground">{lineCount} lines</span>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2">
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          </Button>
          {isLong && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCollapsed(!collapsed)}
              className="h-7 px-2"
            >
              {collapsed ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />}
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div
        ref={containerRef}
        className={`overflow-auto text-sm ${collapsed ? "max-h-[200px]" : "max-h-[600px]"}`}
      >
        {safeHtml ? (
          <div
            className="[&_pre]:!bg-transparent [&_pre]:p-4 [&_pre]:m-0 [&_code]:text-xs"
            dangerouslySetInnerHTML={{ __html: safeHtml }}
          />
        ) : (
          <pre className="p-4 text-xs whitespace-pre-wrap">{content}</pre>
        )}
      </div>

      {/* Collapsed indicator */}
      {collapsed && isLong && (
        <button
          className="w-full border-t py-1 text-xs text-muted-foreground hover:bg-muted/50"
          onClick={() => setCollapsed(false)}
        >
          Show all ({lineCount} lines)
        </button>
      )}
    </div>
  )
}
