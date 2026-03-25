import { BrowserRouter, Routes, Route } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { AppShell } from "@/components/layout/AppShell"
import { DashboardPage } from "@/pages/DashboardPage"
import { PipelinePage } from "@/pages/PipelinePage"
import { RunPage } from "@/pages/RunPage"
import { RunStartPage } from "@/pages/RunStartPage"
import { SettingsPage } from "@/pages/SettingsPage"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<DashboardPage />} />
              <Route path="pipelines" element={<PipelinePage />} />
              <Route path="pipelines/:name" element={<PipelinePage />} />
              <Route path="runs/new" element={<RunStartPage />} />
              <Route path="runs/:runId" element={<RunPage />} />
              <Route path="projects/:projectId" element={<DashboardPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </TooltipProvider>
    </QueryClientProvider>
  )
}
