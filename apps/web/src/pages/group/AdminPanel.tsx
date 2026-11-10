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
import g from "./group.module.css";

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
    <section className={g.admin} aria-labelledby="admin-title">
      <div className={`${ui.lattice} ${g.adminLattice}`} aria-hidden="true" />
      <h2 id="admin-title" className={g.adminTitle}>
        tu panel de organizador
      </h2>
      <p className={g.adminLead}>Esto solo lo ves tú.</p>

      <div className={g.adminPart}>
        <div className={g.partHead}>
          <h3 className={ui.subtitle}>inscripciones</h3>
          <span className={g.state} data-open={isOpen}>
            {isOpen ? "abiertas" : "cerradas"}
          </span>
        </div>
        <p className={ui.hint}>
          {isOpen
            ? "Cualquiera con el enlace puede unirse. Ciérralas cuando estéis todos."
            : "Nadie nuevo puede unirse; el enlace solo sirve para volver a entrar. El sorteo llegará en la siguiente fase."}
        </p>
        <div className={g.actions}>
          {isOpen && (
            <Link className={ui.ghost} to={`/g/${group.slug}/compartir`}>
              invitar a más gente
            </Link>
          )}
          <button
            type="button"
            className={isOpen ? ui.button : ui.ghost}
            disabled={sending}
            onClick={() => setStatus(isOpen ? "closed" : "open")}
          >
            {isOpen ? "cerrar inscripciones" : "reabrir inscripciones"}
          </button>
        </div>
      </div>

      <div className={g.adminPart}>
        <h3 className={ui.subtitle}>exclusiones</h3>
        <p className={ui.hint}>
          Parejas que no pueden tocarse entre sí, en ningún sentido. Por ejemplo, una pareja que
          ya se hace regalos.
        </p>

        {exclusions.length > 0 && (
          <ul className={g.pairs}>
            {exclusions.map((e) => (
              <li key={e.id} className={g.pair}>
                <span>{e.participant_a.name}</span>
                <NoMatchIcon />
                <span>{e.participant_b.name}</span>
                <button
                  type="button"
                  className={g.remove}
                  disabled={sending}
                  onClick={() => removeExclusion(e.id)}
                  aria-label={`quitar la exclusión entre ${e.participant_a.name} y ${e.participant_b.name}`}
                >
                  <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
                    <path
                      d="M3 3l8 8M11 3l-8 8"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
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
      </div>

      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

/** Dos estrellas separadas por una raya: "no se tocan entre sí". */
function NoMatchIcon() {
  return (
    <svg width="34" height="16" viewBox="0 0 34 16" role="img" aria-label="no se tocan">
      <path d="M6 1l1.6 4.4L12 7 7.6 8.6 6 13 4.4 8.6 0 7l4.4-1.6z" fill="currentColor" />
      <path d="M28 1l1.6 4.4L34 7l-4.4 1.6L28 13l-1.6-4.4L22 7l4.4-1.6z" fill="currentColor" />
      <path d="M14 12.5l6-11" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
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
