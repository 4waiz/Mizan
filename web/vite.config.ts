import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api and / health to the FastAPI backend so the SPA talks same-origin in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // fail loudly if 5173 is taken instead of silently using 5174
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
