import { Link } from "react-router";

import ui from "../styles/ui.module.css";

export default function NotFound() {
  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <h1 className={ui.title}>aquí no hay nada</h1>
      <p className={ui.lead}>Si te han pasado un enlace, comprueba que lo has copiado entero.</p>
      <Link to="/" className={ui.textLink}>
        ir al inicio
      </Link>
    </main>
  );
}
