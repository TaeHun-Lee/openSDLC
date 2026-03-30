import { useAgents } from "@/api/queries/agents"
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip"
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "@/components/ui/select"
import { AGENT_COLORS } from "@/lib/constants"

interface AgentPickerProps {
  value: string
  onChange: (agentId: string) => void
}

export function AgentPicker({ value, onChange }: AgentPickerProps) {
  const { data: agents } = useAgents()

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select Agent" />
      </SelectTrigger>
      <SelectContent>
        {agents?.map((agent) => (
          <Tooltip key={agent.agent_id}>
            <TooltipTrigger asChild>
              <div>
                <SelectItem value={agent.agent_id}>
                  <span className={AGENT_COLORS[agent.agent_id] ?? ""}>
                    {agent.display_name}
                  </span>
                </SelectItem>
              </div>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-xs">
              <p className="font-medium">{agent.role}</p>
              {agent.primary_inputs.length > 0 && (
                <p className="text-xs">Inputs: {agent.primary_inputs.join(", ")}</p>
              )}
              {agent.primary_outputs.length > 0 && (
                <p className="text-xs">Outputs: {agent.primary_outputs.join(", ")}</p>
              )}
            </TooltipContent>
          </Tooltip>
        ))}
      </SelectContent>
    </Select>
  )
}
