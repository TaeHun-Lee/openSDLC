import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Square, Play, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog"
import { useCancelRun, useResumeRun } from "@/api/mutations/runs"
import { ApiError } from "@/api/client"

interface RunActionButtonsProps {
  runId: string
  status: string
}

export function RunActionButtons({ runId, status }: RunActionButtonsProps) {
  const cancelMutation = useCancelRun()
  const resumeMutation = useResumeRun()
  const navigate = useNavigate()
  const [showCancelDialog, setShowCancelDialog] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  function handleCancel() {
    setErrorMsg(null)
    cancelMutation.mutate(runId, {
      onSuccess: () => setShowCancelDialog(false),
      onError: (err) => {
        if (err instanceof ApiError && err.status === 409) {
          setErrorMsg("This run has already completed or been cancelled.")
        } else {
          setErrorMsg((err as Error).message)
        }
        setShowCancelDialog(false)
      },
    })
  }

  function handleResume() {
    setErrorMsg(null)
    resumeMutation.mutate(runId, {
      onSuccess: (created) => navigate(`/runs/${created.run_id}`),
      onError: (err) => {
        if (err instanceof ApiError && err.status === 409) {
          setErrorMsg("This run cannot be resumed in its current state.")
        } else {
          setErrorMsg((err as Error).message)
        }
      },
    })
  }

  return (
    <>
      {status === "running" && (
        <Button
          variant="destructive"
          size="sm"
          onClick={() => { setErrorMsg(null); setShowCancelDialog(true) }}
          disabled={cancelMutation.isPending}
        >
          {cancelMutation.isPending ? (
            <><Loader2 className="mr-1 h-3 w-3 animate-spin" /> Cancelling...</>
          ) : (
            <><Square className="mr-1 h-3 w-3" /> Cancel</>
          )}
        </Button>
      )}

      {status === "cancelling" && (
        <Button variant="destructive" size="sm" disabled>
          <Loader2 className="mr-1 h-3 w-3 animate-spin" /> Cancelling...
        </Button>
      )}

      {(status === "cancelled" || status === "failed") && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleResume}
          disabled={resumeMutation.isPending}
        >
          {resumeMutation.isPending ? (
            <><Loader2 className="mr-1 h-3 w-3 animate-spin" /> Resuming...</>
          ) : (
            <><Play className="mr-1 h-3 w-3" /> Resume</>
          )}
        </Button>
      )}

      {errorMsg && (
        <span className="text-xs text-destructive">{errorMsg}</span>
      )}

      {/* Cancel confirmation dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel Run</DialogTitle>
            <DialogDescription>
              The pipeline will stop after the current step completes. Are you sure?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCancelDialog(false)}>
              Keep Running
            </Button>
            <Button
              variant="destructive"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? "Cancelling..." : "Cancel Run"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
