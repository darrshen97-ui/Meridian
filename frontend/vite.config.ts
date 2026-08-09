import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Build output goes straight into the backend's static dir — Node is a build-time
// dependency only, never a runtime one (brief §15).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../app/static",
    emptyOutDir: true,
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8787",
      "/health": "http://127.0.0.1:8787",
    },
  },
});
