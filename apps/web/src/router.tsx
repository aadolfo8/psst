import { createBrowserRouter } from "react-router";

import GroupPage from "./pages/group/GroupPage";
import Home from "./pages/Home";
import { groupLoader, shareLoader } from "./pages/loaders";
import NotFound from "./pages/NotFound";
import RouteError from "./pages/RouteError";
import Share from "./pages/Share";

export const router = createBrowserRouter([
  { path: "/", Component: Home },
  {
    path: "/g/:slug",
    loader: groupLoader,
    Component: GroupPage,
    ErrorBoundary: RouteError,
    // Mientras carga la primera vez no se pinta nada: la API responde en milisegundos.
    HydrateFallback: () => null,
  },
  {
    path: "/g/:slug/compartir",
    loader: shareLoader,
    Component: Share,
    ErrorBoundary: RouteError,
    HydrateFallback: () => null,
  },
  { path: "*", Component: NotFound },
]);
