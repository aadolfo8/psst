import "@fontsource-variable/onest/wght.css";
import "@fontsource-variable/reem-kufi/wght.css";
import "./globals.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";

import { router } from "./router";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
