import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import { DateField } from "../components/DateField";
import { LatticeWindow } from "../components/LatticeWindow";
import { PinField } from "../components/PinField";
import { api, errorMessage } from "../lib/api/client";
import ui from "../styles/ui.module.css";
import styles from "./Home.module.css";

export default function Home() {
  return (
    <div className={styles.home}>
      <header className={styles.bar}>
        <span className={ui.logo}>psst</span>
      </header>
      <LatticeWindow hiddenName="Lucía" />
      <main className={styles.content}>
        <div className={styles.intro}>
          <h1 className={styles.title}>
            pregúntale lo que quieras. <em>sin que sepa que eres tú.</em>
          </h1>
          <p className={ui.lead}>
            El amigo invisible por enlace, con un chat secreto entre quien regala y quien recibe.
            Sin cuentas: un nombre y un PIN.
          </p>
        </div>
        <CreateGroupForm />
      </main>
    </div>
  );
}

function CreateGroupForm() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

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
    <form className={`${ui.block} ${styles.form}`} onSubmit={handleSubmit}>
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

      <label className={ui.field}>
        presupuesto por persona (€)
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

      <DateField name="exchange_date" />

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
        crear el grupo
      </button>
    </form>
  );
}
