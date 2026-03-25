import { NavLink } from "react-router-dom"
import {
  LayoutDashboard,
  GitBranch,
  Play,
  FolderOpen,
  Settings,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { useProjects } from "@/api/queries/projects"

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/pipelines", icon: GitBranch, label: "Pipelines" },
  { to: "/runs/new", icon: Play, label: "New Run" },
  { to: "/settings", icon: Settings, label: "Settings" },
]

export function Sidebar() {
  const { data: projects } = useProjects()

  return (
    <aside className="flex h-full w-60 flex-col border-r bg-sidebar-background">
      <div className="flex h-14 items-center px-4 font-semibold text-sidebar-foreground">
        OpenSDLC
      </div>
      <Separator />
      <ScrollArea className="flex-1 px-3 py-2">
        <nav className="flex flex-col gap-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent/50",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {projects && projects.length > 0 && (
          <>
            <Separator className="my-3" />
            <div className="px-3 py-1 text-xs font-semibold uppercase text-muted-foreground">
              Projects
            </div>
            <nav className="flex flex-col gap-1">
              {projects.map((project) => (
                <NavLink
                  key={project.project_id}
                  to={`/projects/${project.project_id}`}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground hover:bg-sidebar-accent/50",
                    )
                  }
                >
                  <FolderOpen className="h-4 w-4" />
                  <span className="truncate">{project.name}</span>
                </NavLink>
              ))}
            </nav>
          </>
        )}
      </ScrollArea>
    </aside>
  )
}
