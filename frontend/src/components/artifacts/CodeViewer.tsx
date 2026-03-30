import { useState, useEffect, useMemo } from "react"
import DOMPurify from "dompurify"
import { Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"

interface CodeViewerProps {
  path: string
  language: string
  content: string
}

export function CodeViewer({ path, language, content }: CodeViewerProps) {
  const [html, setHtml] = useState<string>("")
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function highlight() {
      const { getHighlighter } = await import("@/lib/shiki")
      const highlighter = await getHighlighter()
      const langMap: Record<string, string> = {
        javascript: "javascript",
        typescript: "typescript",
        python: "python",
        html: "html",
        css: "css",
        json: "json",
        yaml: "yaml",
        markdown: "markdown",
        shell: "bash",
        bash: "bash",
      }
      const lang = langMap[language.toLowerCase()] ?? "text"
      try {
        const result = highlighter.codeToHtml(content, {
          lang,
          themes: { light: "github-light", dark: "github-dark" },
        })
        if (!cancelled) setHtml(result)
      } catch {
        if (!cancelled) setHtml("")
      }
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

  return (
    <div className="rounded-lg border">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{path}</span>
          <span className="text-xs text-muted-foreground">{language}</span>
          <span className="text-xs text-muted-foreground">{lineCount} lines</span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 px-2">
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
        </Button>
      </div>
      <div className="overflow-auto max-h-[600px] text-sm">
        {safeHtml ? (
          <div
            className="[&_pre]:!bg-transparent [&_pre]:p-4 [&_pre]:m-0 [&_code]:text-xs"
            dangerouslySetInnerHTML={{ __html: safeHtml }}
          />
        ) : (
          <pre className="p-4 text-xs whitespace-pre-wrap">{content}</pre>
        )}
      </div>
    </div>
  )
}
