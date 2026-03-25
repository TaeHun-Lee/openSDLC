import { useEffect } from "react"
import { useSettingsStore } from "@/stores/settings-store"

export function useTheme() {
  const { theme, setTheme } = useSettingsStore()

  useEffect(() => {
    const root = window.document.documentElement

    const applyTheme = (resolved: "light" | "dark") => {
      root.classList.remove("light", "dark")
      root.classList.add(resolved)
    }

    if (theme === "system") {
      const mq = window.matchMedia("(prefers-color-scheme: dark)")
      applyTheme(mq.matches ? "dark" : "light")
      const handler = (e: MediaQueryListEvent) => applyTheme(e.matches ? "dark" : "light")
      mq.addEventListener("change", handler)
      return () => mq.removeEventListener("change", handler)
    }

    applyTheme(theme)
  }, [theme])

  return { theme, setTheme }
}
