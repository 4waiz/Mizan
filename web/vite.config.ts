import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api and / health to the FastAPI backend so the SPA talks same-origin in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
