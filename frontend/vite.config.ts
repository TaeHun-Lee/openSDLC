import path from "path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes("node_modules/shiki") || id.includes("node_modules/@shikijs")) {
            return "shiki"
          }
          if (id.includes("node_modules/recharts") || id.includes("node_modules/d3-")) {
            return "recharts"
          }
          if (id.includes("node_modules/@radix-ui")) {
            return "radix"
          }
        },
      },
    },
  },
})
