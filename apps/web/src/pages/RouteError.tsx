import { isRouteErrorResponse, Link, useRouteError } from "react-router";

import ui from "../styles/ui.module.css";

/** Pantalla de error de las rutas: grupo inexistente, API caída, etc. */
export default function RouteError() {
  const error = useRouteError();
  const notFound = isRouteErrorResponse(error) && error.status === 404;

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <h1 className={ui.title}>{notFound ? "aquí no hay nada" : "algo ha fallado"}</h1>
      <p className={ui.lead}>
        {notFound
          ? "Si te han pasado un enlace, comprueba que lo has copiado entero."
          : "Vuelve a intentarlo dentro de un momento."}
      </p>
      <Link to="/" className={ui.textLink}>
        ir al inicio
      </Link>
    </main>
  );
}
