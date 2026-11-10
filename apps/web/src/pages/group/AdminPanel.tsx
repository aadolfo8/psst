import { useState, type FormEvent } from "react";
import { Link, useRevalidator } from "react-router";

import {
  api,
  errorMessage,
  type ExclusionOut,
  type GroupPublic,
  type ParticipantPublic,
} from "../../lib/api/client";
import ui from "../../styles/ui.module.css";

type Props = {
  group: GroupPublic;
  participants: ParticipantPublic[];
  exclusions: ExclusionOut[];
};

/** Lo que solo ve el organizador: invitar, exclusiones y cerrar inscripciones. */
export default function AdminPanel({ group, participants, exclusions }: Props) {
  const { revalidate } = useRevalidator();
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const path = { params: { path: { slug: group.slug } } };

  /** Ejecuta una llamada a la API y, si va bien, recarga los datos de la sala. */
  async function run(call: () => Promise<{ error?: unknown }>) {
    setSending(true);
    setError(null);
    const { error } = await call();
    if (error) setError(errorMessage(error));
    else await revalidate();
    setSending(false);
  }

  function addExclusion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const body = {
      participant_a_id: String(form.get("a")),
      participant_b_id: String(form.get("b")),
    };
    run(() => api.POST("/groups/{slug}/exclusions", { ...path, body }));
  }

  function removeExclusion(id: string) {
    run(() =>
      api.DELETE("/groups/{slug}/exclusions/{exclusion_id}", {
        params: { path: { slug: group.slug, exclusion_id: id } },
      }),
    );
  }

  function setStatus(status: "open" | "closed") {
    run(() => api.PATCH("/groups/{slug}", { ...path, body: { status } }));
  }

  const isOpen = group.status === "open";

  return (
    <>
      <section className={ui.block}>
        <h2 className={ui.subtitle}>invitar</h2>
        <p className={ui.hint}>
          {isOpen
            ? "Comparte el enlace del grupo por WhatsApp o cópialo."
            : "Las inscripciones están cerradas: el enlace solo sirve para volver a entrar."}
        </p>
        <Link className={ui.ghost} to={`/g/${group.slug}/compartir`}>
          compartir enlace
        </Link>
      </section>

      <section className={ui.block}>
        <h2 className={ui.subtitle}>exclusiones</h2>
        <p className={ui.hint}>
          Parejas que no pueden tocarse entre sí, en ningún sentido. Por ejemplo, una pareja que
          ya se hace regalos.
        </p>

        {exclusions.length > 0 && (
          <ul className={ui.list}>
            {exclusions.map((e) => (
              <li key={e.id}>
                <span>
                  {e.participant_a.name} y {e.participant_b.name}
                </span>
                <button
                  type="button"
                  className={ui.linkButton}
                  disabled={sending}
                  onClick={() => removeExclusion(e.id)}
                >
                  quitar
                </button>
              </li>
            ))}
          </ul>
        )}

        {participants.length < 2 ? (
          <p className={ui.muted}>Hacen falta al menos dos personas apuntadas.</p>
        ) : (
          <form className={ui.form} onSubmit={addExclusion}>
            <div className={ui.row}>
              <ParticipantSelect name="a" label="persona" participants={participants} />
              <ParticipantSelect name="b" label="no puede tocarle a" participants={participants} />
            </div>
            <button className={ui.ghost} disabled={sending}>
              añadir exclusión
            </button>
          </form>
        )}
      </section>

      <section className={ui.block}>
        <h2 className={ui.subtitle}>inscripciones</h2>
        <p className={ui.hint}>
          {isOpen
            ? "Abiertas: cualquiera con el enlace puede unirse. Ciérralas cuando estéis todos."
            : "Cerradas: nadie nuevo puede unirse. El sorteo llegará en la siguiente fase."}
        </p>
        <button
          type="button"
          className={isOpen ? ui.button : ui.ghost}
          disabled={sending}
          onClick={() => setStatus(isOpen ? "closed" : "open")}
        >
          {isOpen ? "cerrar inscripciones" : "reabrir inscripciones"}
        </button>
      </section>

      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
    </>
  );
}

function ParticipantSelect({
  name,
  label,
  participants,
}: {
  name: string;
  label: string;
  participants: ParticipantPublic[];
}) {
  return (
    <label className={ui.field}>
      {label}
      <select className={ui.input} name={name} required defaultValue="">
        <option value="" disabled>
          elige
        </option>
        {participants.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </label>
  );
}
