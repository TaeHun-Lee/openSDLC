import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react"
import type { PipelineValidationResult, ValidationIssue } from "@/api/types"

interface ValidationBannerProps {
  result: PipelineValidationResult
}

export function ValidationBanner({ result }: ValidationBannerProps) {
  if (result.valid && result.warnings.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-green-300 bg-green-500/10 p-4 text-green-700 dark:text-green-400">
        <CheckCircle2 className="h-5 w-5 shrink-0" />
        <span className="font-medium">Validation passed</span>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {result.errors.length > 0 && (
        <div className="rounded-lg border border-red-300 bg-red-500/10 p-4">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <XCircle className="h-5 w-5 shrink-0" />
            <span className="font-medium">
              {result.errors.length} error{result.errors.length !== 1 ? "s" : ""}
            </span>
          </div>
          <IssueList issues={result.errors} className="text-red-600 dark:text-red-400" />
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-500/10 p-4">
          <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <span className="font-medium">
              {result.warnings.length} warning{result.warnings.length !== 1 ? "s" : ""}
            </span>
          </div>
          <IssueList issues={result.warnings} className="text-amber-600 dark:text-amber-400" />
        </div>
      )}
    </div>
  )
}

function IssueList({ issues, className }: { issues: ValidationIssue[]; className?: string }) {
  return (
    <ul className={`mt-2 space-y-1 text-sm ${className ?? ""}`}>
      {issues.map((issue, i) => (
        <li key={i} className="flex gap-2">
          <span className="shrink-0 font-mono text-xs opacity-60">
            {issue.step != null ? `Step ${issue.step}` : issue.type}
          </span>
          <span>{issue.message}</span>
        </li>
      ))}
    </ul>
  )
}
