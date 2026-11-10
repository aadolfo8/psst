import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { PinField } from "../components/PinField";
import { api, errorMessage } from "../lib/api/client";
import ui from "../styles/ui.module.css";
import styles from "./Home.module.css";

export default function Home() {
  return (
    <main className={ui.page}>
      <span className={ui.logo}>psst</span>
      <h1 className={styles.title}>
        A <span role="img" aria-label="nombre oculto" className={styles.bar} /> le toca
        regalarte.
      </h1>
      <p className={styles.lead}>
        El amigo invisible por enlace. Cada uno ve solo su nombre y puede preguntar a su persona
        sin que sepa quién es.
      </p>
      <CreateGroupForm />
    </main>
  );
}

function CreateGroupForm() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const today = new Date().toLocaleDateString("sv-SE"); // formato AAAA-MM-DD en hora local

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const budget = String(form.get("budget") ?? "");
    const exchangeDate = String(form.get("exchange_date") ?? "");

    setSending(true);
    setError(null);
    const { data, error } = await api.POST("/groups", {
      body: {
        name: String(form.get("name")),
        budget: budget ? Number(budget) : null,
        exchange_date: exchangeDate || null,
        admin_name: String(form.get("admin_name")),
        pin: String(form.get("pin")),
      },
    });
    setSending(false);

    if (data) navigate(`/g/${data.group.slug}/compartir`);
    else setError(errorMessage(error));
  }

  return (
    <form className={ui.block} onSubmit={handleSubmit}>
      <h2 className={ui.subtitle}>crea tu grupo</h2>

      <label className={ui.field}>
        nombre del grupo
        <input
          className={ui.input}
          name="name"
          required
          maxLength={80}
          placeholder="familia, oficina…"
        />
      </label>

      <div className={ui.row}>
        <label className={ui.field}>
          presupuesto (€)
          <input
            className={ui.input}
            name="budget"
            type="number"
            min={1}
            max={1000}
            inputMode="numeric"
            placeholder="opcional"
          />
        </label>
        <label className={ui.field}>
          fecha
          <input className={ui.input} name="exchange_date" type="date" min={today} />
        </label>
      </div>

      <label className={ui.field}>
        tu nombre
        <input
          className={ui.input}
          name="admin_name"
          required
          maxLength={40}
          autoComplete="given-name"
        />
      </label>
      <PinField />
      <p className={ui.hint}>
        Tú también participas. Con tu nombre y el PIN podrás volver a entrar desde otro móvil.
      </p>

      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <button className={ui.button} disabled={sending}>
        crear grupo
      </button>
    </form>
  );
}
