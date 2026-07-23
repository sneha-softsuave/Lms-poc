import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api to the FastAPI backend so the SPA and API share an origin in dev.
//
// The target MUST be 127.0.0.1, not "localhost". Node 17+ returns DNS results in
// resolver order instead of forcing IPv4, and on Windows "localhost" resolves to
// ::1 first. uvicorn binds 127.0.0.1 (IPv4) only, so a "localhost" target makes
// the proxy dial ::1:8000, get ECONNREFUSED, and answer 404 with an empty body —
// a login that fails while the backend logs nothing at all.
const API_TARGET = process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true, // fail loudly rather than silently moving to 3001
    proxy: {
      "/api": API_TARGET,
      "/media": API_TARGET,
    },
  },
});
