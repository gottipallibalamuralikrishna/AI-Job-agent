import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxy = { "/api/v1": "http://127.0.0.1:8000" };
const allowedHosts = ["sb-5hdnemp9p58o.vercel.run"];

export default defineConfig({
  plugins: [react()],
  server: { proxy, allowedHosts },
  preview: { proxy, allowedHosts },
});
