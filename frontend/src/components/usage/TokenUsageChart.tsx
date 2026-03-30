import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from "recharts"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { formatTokens } from "@/lib/format"
import type { ModelUsage, AgentUsage, IterationUsage } from "@/api/types"

const COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#ec4899",
  "#8b5cf6", "#14b8a6", "#f97316", "#64748b",
]

interface TokenUsageChartProps {
  byModel: Record<string, ModelUsage>
  byAgent: Record<string, AgentUsage>
  byIteration: IterationUsage[]
}

export function TokenUsageChart({ byModel, byAgent, byIteration }: TokenUsageChartProps) {
  const modelData = Object.entries(byModel).map(([name, u]) => ({
    name,
    total: u.input_tokens + u.output_tokens,
    input: u.input_tokens,
    output: u.output_tokens,
    steps: u.steps,
  }))

  const agentData = Object.entries(byAgent).map(([name, u]) => ({
    name: name.replace("Agent", ""),
    input: u.input_tokens,
    output: u.output_tokens,
    steps: u.steps,
  }))

  const iterData = byIteration.map((u) => ({
    name: `Iter ${u.iteration_num}`,
    input: u.input_tokens,
    output: u.output_tokens,
    steps: u.step_count,
  }))

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      {/* Model Pie Chart */}
      {modelData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Token Usage by Model</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={modelData}
                  dataKey="total"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ name, value }: { name: string; value: number }) => `${name} (${formatTokens(value)})`}
                >
                  {modelData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatTokens(Number(v))} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Agent Bar Chart */}
      {agentData.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Token Usage by Agent</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={agentData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" className="text-xs" />
                <YAxis tickFormatter={(v) => formatTokens(v)} className="text-xs" />
                <Tooltip formatter={(v) => formatTokens(Number(v))} />
                <Legend />
                <Bar dataKey="input" name="Input" fill="#3b82f6" stackId="tokens" />
                <Bar dataKey="output" name="Output" fill="#22c55e" stackId="tokens" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Iteration Line Chart */}
      {iterData.length > 1 && (
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Token Usage by Iteration</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={iterData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="name" className="text-xs" />
                <YAxis tickFormatter={(v) => formatTokens(v)} className="text-xs" />
                <Tooltip formatter={(v) => formatTokens(Number(v))} />
                <Legend />
                <Line type="monotone" dataKey="input" name="Input" stroke="#3b82f6" strokeWidth={2} />
                <Line type="monotone" dataKey="output" name="Output" stroke="#22c55e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
