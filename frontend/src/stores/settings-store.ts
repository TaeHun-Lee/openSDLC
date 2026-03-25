import { create } from "zustand"
import { persist } from "zustand/middleware"

type Theme = "light" | "dark" | "system"

interface SettingsState {
  theme: Theme
  apiKey: string
  showApiKeyDialog: boolean
  setTheme: (theme: Theme) => void
  setApiKey: (key: string) => void
  setShowApiKeyDialog: (show: boolean) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: "system",
      apiKey: "",
      showApiKeyDialog: false,
      setTheme: (theme) => set({ theme }),
      setApiKey: (apiKey) => {
        localStorage.setItem("opensdlc_api_key", apiKey)
        set({ apiKey })
      },
      setShowApiKeyDialog: (showApiKeyDialog) => set({ showApiKeyDialog }),
    }),
    {
      name: "opensdlc-settings",
      partialize: (state) => ({ theme: state.theme, apiKey: state.apiKey }),
    },
  ),
)
