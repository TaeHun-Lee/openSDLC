import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatTokens } from "@/lib/format"

interface UsageSummaryProps {
  inputTokens: number
  outputTokens: number
  cacheReadTokens: number
  cacheCreationTokens: number
}

export function UsageSummary({
  inputTokens,
  outputTokens,
  cacheReadTokens,
  cacheCreationTokens,
}: UsageSummaryProps) {
  const total = inputTokens + outputTokens

  const cards = [
    { label: "Total Tokens", value: total, color: "text-foreground" },
    { label: "Input", value: inputTokens, color: "text-blue-600" },
    { label: "Output", value: outputTokens, color: "text-green-600" },
    { label: "Cache Read", value: cacheReadTokens, color: "text-purple-600" },
    { label: "Cache Creation", value: cacheCreationTokens, color: "text-amber-600" },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((c) => (
        <Card key={c.label}>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs text-muted-foreground">{c.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-2xl font-bold ${c.color}`}>{formatTokens(c.value)}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
