import "@fontsource-variable/onest/wght.css";
import "@fontsource-variable/reem-kufi/wght.css";
import "./globals.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";
import { registerSW } from "virtual:pwa-register";

import { router } from "./router";

// Registra el service worker (src/sw.ts); si hay versión nueva, se activa sola.
registerSW({ immediate: true });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
