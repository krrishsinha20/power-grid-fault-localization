import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Reads VITE_API_BASE_URL from the environment at build/dev time.
// See .env.example for what to set this to in different environments.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
  },
  preview: {
    host: true,
    port: 4173,
  },
});
