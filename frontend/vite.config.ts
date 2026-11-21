import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const proxy = { "/api/v1": "http://127.0.0.1:8000" };

export default defineConfig({
  plugins: [react()],
  server: { proxy },
  preview: { proxy },

  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules")) {
            if (id.includes("@mui") || id.includes("@emotion")) {
              return "mui";
            }

            if (id.includes("recharts") || id.includes("d3-")) {
              return "charts";
            }

            if (id.includes("lucide-react")) {
              return "icons";
            }

            if (
              id.includes("react") ||
              id.includes("react-dom") ||
              id.includes("react-router")
            ) {
              return "react-vendor";
            }
          }
        },
      },
    },
  },
});
