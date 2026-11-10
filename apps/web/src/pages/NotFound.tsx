import { Link } from "react-router";

import styles from "./Home.module.css";

export default function NotFound() {
  return (
    <main className={styles.page}>
      <span className={styles.logo}>psst</span>
      <h1 className={styles.title}>Aquí no hay nada.</h1>
      <p className={styles.lead}>
        Si te han pasado un enlace, comprueba que lo has copiado entero.
      </p>
      <Link to="/">ir al inicio</Link>
    </main>
  );
}
