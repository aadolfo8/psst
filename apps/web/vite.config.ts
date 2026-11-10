import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // La web llama a /api/... en su mismo origen; en desarrollo Vite lo reenvía a FastAPI
    // (en producción lo hará Caddy). Así la cookie de sesión es del dominio de la web.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
