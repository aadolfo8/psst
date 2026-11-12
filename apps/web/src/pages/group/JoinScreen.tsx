import { useState, type FormEvent } from "react";
import { Link, useRevalidator } from "react-router";

import { PinField } from "../../components/PinField";
import { api, errorMessage, type GroupPublic } from "../../lib/api/client";
import ui from "../../styles/ui.module.css";
import g from "./group.module.css";
import GroupHeader from "./GroupHeader";

type Mode = "join" | "login";

/**
 * Lo que ve quien abre el enlace sin sesión. Arriba elige si es nuevo o si ya estaba en el
 * grupo (desde otro móvil, o porque borró el navegador): son dos formularios casi iguales y
 * confundirlos es el error más habitual.
 */
export default function JoinScreen({ group }: { group: GroupPublic }) {
  const { revalidate } = useRevalidator();
  const isOpen = group.status === "open";
  // Con las inscripciones cerradas solo tiene sentido volver a entrar.
  const [mode, setMode] = useState<Mode>(isOpen ? "join" : "login");
  const [error, setError] = useState<string | null>(null);
  // El nombre ya existe en el grupo: casi seguro que es la misma persona que vuelve.
  const [nameTaken, setNameTaken] = useState(false);
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = { name: String(form.get("name")), pin: String(form.get("pin")) };
    const path = { params: { path: { slug: group.slug } } };

    setSending(true);
    setError(null);
    setNameTaken(false);
    const { error, response } =
      mode === "join"
        ? await api.POST("/groups/{slug}/participants", { ...path, body })
        : await api.POST("/groups/{slug}/sessions", { ...path, body });
    setSending(false);

    // Con la cookie ya puesta, el loader devuelve la sala de espera.
    if (!error) {
      await revalidate();
      return;
    }
    setError(errorMessage(error));
    setNameTaken(mode === "join" && response.status === 409 && isOpen);
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    setNameTaken(false);
  }

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <GroupHeader group={group} invite />

      {isOpen && (
        <div className={g.modeSwitch} role="group" aria-label="cómo entras">
          <button
            type="button"
            aria-pressed={mode === "join"}
            onClick={() => switchMode("join")}
          >
            soy nuevo
          </button>
          <button
            type="button"
            aria-pressed={mode === "login"}
            onClick={() => switchMode("login")}
          >
            ya estoy dentro
          </button>
        </div>
      )}

      <form className={ui.block} onSubmit={handleSubmit}>
        <h2 className={ui.subtitle}>{mode === "join" ? "únete al grupo" : "vuelve a entrar"}</h2>
        <p className={ui.hint}>
          {mode === "join"
            ? "Es la primera vez que entras: elige tu nombre y un PIN."
            : "Ya te apuntaste antes, en este móvil o en otro: entra con el mismo nombre y PIN."}
        </p>
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
        {/* key={mode}: al cambiar de modo el PIN se vacía. El que eliges al unirte no es el
            de siempre, y no queremos mandarlo al volver a entrar. */}
        <PinField key={mode} label={mode === "join" ? "elige un PIN de 4 cifras" : "tu PIN"} />
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
        {nameTaken && (
          // El nombre escrito se queda en el campo: solo falta poner el PIN de siempre.
          <button type="button" className={ui.ghost} onClick={() => switchMode("login")}>
            soy yo, entrar con mi PIN
          </button>
        )}
        <button className={ui.button} disabled={sending}>
          {mode === "join" ? "unirme" : "entrar"}
        </button>
      </form>

      {!isOpen && (
        <p className={ui.hint}>
          Las inscripciones están cerradas. Si ya estabas apuntado, entra con tu nombre y tu PIN.
        </p>
      )}
    </main>
  );
}
