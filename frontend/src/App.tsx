import { lazy, Suspense, useEffect, Component, type ReactNode, type ErrorInfo } from "react"
import { BrowserRouter, Routes, Route, Link } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppShell } from "@/components/layout/AppShell"
import { setOn401Handler } from "@/api/client"
import { useSettingsStore } from "@/stores/settings-store"
import { ApiKeyDialog } from "@/components/ApiKeyDialog"

// Lazy-loaded pages
const DashboardPage = lazy(() => import("@/pages/DashboardPage").then(m => ({ default: m.DashboardPage })))
const PipelinePage = lazy(() => import("@/pages/PipelinePage").then(m => ({ default: m.PipelinePage })))
const PipelineEditorPage = lazy(() => import("@/pages/PipelineEditorPage").then(m => ({ default: m.PipelineEditorPage })))
const RunPage = lazy(() => import("@/pages/RunPage").then(m => ({ default: m.RunPage })))
const RunStartPage = lazy(() => import("@/pages/RunStartPage").then(m => ({ default: m.RunStartPage })))
const SettingsPage = lazy(() => import("@/pages/SettingsPage").then(m => ({ default: m.SettingsPage })))
const ProjectSettingsPage = lazy(() => import("@/pages/ProjectSettingsPage").then(m => ({ default: m.ProjectSettingsPage })))
const ArtifactsPage = lazy(() => import("@/pages/ArtifactsPage").then(m => ({ default: m.ArtifactsPage })))
const UsagePage = lazy(() => import("@/pages/UsagePage").then(m => ({ default: m.UsagePage })))
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage").then(m => ({ default: m.NotFoundPage })))

// 1-9: Route-level Error Boundary to prevent full app crash on render errors
interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class RouteErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("RouteErrorBoundary caught:", error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
          <h1 className="text-2xl font-bold text-destructive">Something went wrong</h1>
          <p className="max-w-md text-center text-sm text-muted-foreground">
            {this.state.error?.message ?? "An unexpected error occurred."}
          </p>
          <div className="flex gap-3">
            <button
              className="rounded-md border px-4 py-2 text-sm hover:bg-muted"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Try Again
            </button>
            <Link to="/" className="rounded-md border px-4 py-2 text-sm hover:bg-muted">
              Go to Dashboard
            </Link>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
})

function PageLoader() {
  return (
    <div className="flex h-full items-center justify-center">
      <div className="text-muted-foreground text-sm">Loading...</div>
    </div>
  )
}

function On401Connector() {
  const setShowApiKeyDialog = useSettingsStore((s) => s.setShowApiKeyDialog)
  useEffect(() => {
    setOn401Handler(() => setShowApiKeyDialog(true))
    return () => setOn401Handler(() => {})
  }, [setShowApiKeyDialog])
  return null
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <On401Connector />
          <ApiKeyDialog />
          <Toaster
            position="top-right"
            richColors
            closeButton
            toastOptions={{
              duration: 5000,
            }}
          />
          <RouteErrorBoundary>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<Suspense fallback={<PageLoader />}><DashboardPage /></Suspense>} />
                <Route path="pipelines" element={<Suspense fallback={<PageLoader />}><PipelinePage /></Suspense>} />
                <Route path="pipelines/new" element={<Suspense fallback={<PageLoader />}><PipelineEditorPage /></Suspense>} />
                <Route path="pipelines/:name" element={<Suspense fallback={<PageLoader />}><PipelinePage /></Suspense>} />
                <Route path="pipelines/:name/edit" element={<Suspense fallback={<PageLoader />}><PipelineEditorPage /></Suspense>} />
                <Route path="runs/new" element={<Suspense fallback={<PageLoader />}><RunStartPage /></Suspense>} />
                <Route path="runs/:runId" element={<Suspense fallback={<PageLoader />}><RunPage /></Suspense>} />
                <Route path="runs/:runId/artifacts" element={<Suspense fallback={<PageLoader />}><ArtifactsPage /></Suspense>} />
                <Route path="runs/:runId/usage" element={<Suspense fallback={<PageLoader />}><UsagePage /></Suspense>} />
                <Route path="projects/:projectId/usage" element={<Suspense fallback={<PageLoader />}><UsagePage /></Suspense>} />
                <Route path="projects/:projectId" element={<Suspense fallback={<PageLoader />}><DashboardPage /></Suspense>} />
                <Route path="projects/:projectId/settings" element={<Suspense fallback={<PageLoader />}><ProjectSettingsPage /></Suspense>} />
                <Route path="settings" element={<Suspense fallback={<PageLoader />}><SettingsPage /></Suspense>} />
                <Route path="*" element={<Suspense fallback={<PageLoader />}><NotFoundPage /></Suspense>} />
              </Route>
            </Routes>
          </RouteErrorBoundary>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
