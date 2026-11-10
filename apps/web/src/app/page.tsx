import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.page}>
      <span className={styles.logo}>psst</span>
      <h1 className={styles.title}>
        A <span role="img" aria-label="nombre oculto" className={styles.bar} /> le toca
        regalarte.
      </h1>
      <p className={styles.lead}>
        El amigo invisible por enlace. Cada uno ve solo su nombre y puede preguntar a
        su persona sin que sepa quién es.
      </p>
      <p className={styles.note}>En construcción.</p>
    </main>
  );
}
