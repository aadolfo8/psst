import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      // Service worker propio (src/sw.ts): hace falta para manejar las push.
      strategies: "injectManifest",
      srcDir: "src",
      filename: "sw.ts",
      registerType: "autoUpdate",
      // En desarrollo también hay service worker, para poder probar las push.
      devOptions: { enabled: true, type: "module" },
      manifest: {
        name: "psst",
        short_name: "psst",
        description: "El amigo invisible por enlace, con un chat secreto.",
        lang: "es",
        start_url: "/",
        display: "standalone",
        background_color: "#1d2a8c",
        theme_color: "#1d2a8c",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
    }),
  ],
  server: {
    port: 3000,
    // La web llama a /api/... en su mismo origen; en desarrollo Vite lo reenvía a FastAPI
    // (en producción lo hará Caddy). Así la cookie de sesión es del dominio de la web.
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        ws: true, // también el websocket del chat
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
