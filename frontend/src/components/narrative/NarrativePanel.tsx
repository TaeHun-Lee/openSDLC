import { useRef, useEffect, useState, useCallback } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Info, CheckCircle2, XCircle } from "lucide-react"
import { MessageBubble } from "./MessageBubble"
import { ReworkMarker } from "./ReworkMarker"
import { StepTransition } from "./StepTransition"
import { useNarrativeStore, type NarrativeMessage } from "@/stores/narrative-store"

export function NarrativePanel() {
  const messages = useNarrativeStore((s) => s.messages)
  const bottomRef = useRef<HTMLDivElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages.length, autoScroll])

  // Detect user scrolling up to pause auto-scroll
  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
    setAutoScroll(isAtBottom)
  }, [])

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Waiting for events...
      </div>
    )
  }

  // Group messages by iteration
  let currentIter: number | null = null

  return (
    <ScrollArea className="h-full">
      <div
        ref={scrollRef}
        className="space-y-1 p-4"
        onScroll={handleScroll}
      >
        {messages.map((msg) => {
          const elements: React.ReactNode[] = []

          // Iteration header
          if (msg.iterationNum != null && msg.iterationNum !== currentIter) {
            currentIter = msg.iterationNum
            elements.push(
              <div key={`iter-${currentIter}`} className="py-3">
                <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Iteration {currentIter}
                </div>
              </div>,
            )
          }

          elements.push(
            <NarrativeEvent key={msg.id} message={msg} />,
          )

          return elements
        })}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}

function NarrativeEvent({ message }: { message: NarrativeMessage }) {
  switch (message.eventType) {
    case "pipeline_started":
      return (
        <div className="flex items-center gap-2 rounded-lg border border-blue-300 bg-blue-500/10 p-3 text-sm text-blue-700 dark:text-blue-400">
          <Info className="h-4 w-4 shrink-0" />
          {message.message ?? "Pipeline started"}
        </div>
      )

    case "step_started":
    case "step_completed":
      return <StepTransition message={message} />

    case "agent_narrative":
      return <MessageBubble message={message} />

    case "validation_result":
      return (
        <div className="rounded-lg border p-3 text-sm">
          <span className="font-medium">{message.agentName}: </span>
          {message.message}
        </div>
      )

    case "rework_triggered":
      return <ReworkMarker message={message} />

    case "pipeline_completed":
      return (
        <div className="flex items-center gap-2 rounded-lg border border-green-300 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          {message.message ?? "Pipeline completed"}
        </div>
      )

    case "pipeline_error":
      return (
        <div className="flex items-center gap-2 rounded-lg border border-red-300 bg-red-500/10 p-3 text-sm text-red-700 dark:text-red-400">
          <XCircle className="h-4 w-4 shrink-0" />
          {message.message ?? "Pipeline error"}
        </div>
      )

    default:
      if (message.message) {
        return (
          <div className="py-1 text-sm text-muted-foreground">
            {message.message}
          </div>
        )
      }
      return null
  }
}
