import { useState, type FormEvent } from "react";
import { Link, useRevalidator } from "react-router";

import { PinField } from "../../components/PinField";
import { api, errorMessage, type GroupPublic } from "../../lib/api/client";
import { groupDetails } from "../../lib/format";
import ui from "../../styles/ui.module.css";

type Mode = "join" | "login";

export default function JoinScreen({ group }: { group: GroupPublic }) {
  const { revalidate } = useRevalidator();
  // Con las inscripciones cerradas solo tiene sentido volver a entrar.
  const [mode, setMode] = useState<Mode>(group.status === "open" ? "join" : "login");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = { name: String(form.get("name")), pin: String(form.get("pin")) };
    const path = { params: { path: { slug: group.slug } } };

    setSending(true);
    setError(null);
    const { error } =
      mode === "join"
        ? await api.POST("/groups/{slug}/participants", { ...path, body })
        : await api.POST("/groups/{slug}/sessions", { ...path, body });
    setSending(false);

    // Con la cookie ya puesta, el loader devuelve la sala de espera.
    if (!error) await revalidate();
    else setError(errorMessage(error));
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
  }

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <h1 className={ui.title}>{group.name}</h1>
      <ul className={ui.details}>
        {groupDetails(group).map((detail) => (
          <li key={detail}>{detail}</li>
        ))}
      </ul>

      <form className={ui.block} onSubmit={handleSubmit}>
        <h2 className={ui.subtitle}>{mode === "join" ? "únete al grupo" : "vuelve a entrar"}</h2>
        <label className={ui.field}>
          tu nombre
          <input
            className={ui.input}
            name="name"
            required
            maxLength={40}
            autoComplete="given-name"
          />
        </label>
        <PinField label={mode === "join" ? "elige un PIN de 4 cifras" : "tu PIN"} />
        {mode === "join" && (
          <p className={ui.hint}>
            El PIN sirve para volver a entrar desde otro móvil o si borras el navegador. No hace
            falta email ni teléfono.
          </p>
        )}

        {error && (
          <p className={ui.error} role="alert">
            {error}
          </p>
        )}
        <button className={ui.button} disabled={sending}>
          {mode === "join" ? "unirme" : "entrar"}
        </button>

        {group.status === "open" && (
          <button
            type="button"
            className={ui.linkButton}
            onClick={() => switchMode(mode === "join" ? "login" : "join")}
          >
            {mode === "join" ? "ya estoy apuntado" : "todavía no estoy apuntado"}
          </button>
        )}
      </form>

      {group.status !== "open" && (
        <p className={ui.hint}>
          Las inscripciones están cerradas. Si ya estabas apuntado, entra con tu nombre y tu PIN.
        </p>
      )}
    </main>
  );
}
