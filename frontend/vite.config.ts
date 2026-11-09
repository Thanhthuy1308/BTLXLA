import { defineConfig } from "vite";
import path from "node:path";

export default defineConfig({
  // GitHub Pages serves the project under /BTLXLA/; the workflow sets VITE_BASE.
  // Local development and the Docker image keep the site root.
  base: process.env.VITE_BASE ?? "/",
  // `import.meta.dirname` is the forward-compatible ESM equivalent of
  // `__dirname`, keeping the source alias stable as Vite changes its loader.
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  server: { proxy: { "/api": "http://127.0.0.1:5000", "/results": "http://127.0.0.1:5000" } },
});
