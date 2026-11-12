import { useState, type FormEvent } from "react";
import { Link, useRevalidator } from "react-router";

import {
  api,
  errorMessage,
  type ExclusionOut,
  type GroupPublic,
  type GuessStatus,
  type ParticipantPublic,
} from "../../lib/api/client";
import { WhatsAppIcon } from "../../components/WhatsAppIcon";
import { inviteUrl } from "../../lib/format";
import ui from "../../styles/ui.module.css";
import g from "./group.module.css";
import UnmaskDialog from "./UnmaskDialog";

type Props = {
  group: GroupPublic;
  participants: ParticipantPublic[];
  exclusions: ExclusionOut[];
  guess: GuessStatus | null;
};

/** Lo que solo ve el organizador: invitar, cerrar inscripciones, exclusiones y sorteo. */
export default function AdminPanel({ group, participants, exclusions, guess }: Props) {
  const { revalidate } = useRevalidator();
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  // A quién se va a quitar: se pide confirmación en la misma fila antes de borrar.
  const [removing, setRemoving] = useState<string | null>(null);
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

  async function removeParticipant(id: string) {
    await run(() =>
      api.DELETE("/groups/{slug}/participants/{participant_id}", {
        params: { path: { slug: group.slug, participant_id: id } },
      }),
    );
    setRemoving(null);
  }

  function setStatus(status: "open" | "closed") {
    run(() => api.PATCH("/groups/{slug}", { ...path, body: { status } }));
  }

  function makeDraw() {
    run(() => api.POST("/groups/{slug}/draw", path));
  }

  const isOpen = group.status === "open";
  const isDrawn = group.status === "drawn";
  const unmasked = group.unmasked_at != null;
  const seen = participants.filter((p) => p.has_revealed).length;
  const others = participants.filter((p) => !p.is_admin);

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
            : "Nadie nuevo puede unirse; el enlace solo sirve para volver a entrar."}
        </p>
        {!isDrawn && others.length > 0 && (
          <details className={g.removeList}>
            <summary>quitar a alguien</summary>
            <p className={ui.hint}>
              Por si alguien se ha apuntado dos veces o por error. Se borran también sus
              exclusiones.
            </p>
            <ul className={g.pairs}>
              {others.map((p) => (
                <li key={p.id} className={g.pair}>
                  {removing === p.id ? (
                    <>
                      <span>¿quitar a {p.name}?</span>
                      <span className={g.confirm}>
                        <button
                          type="button"
                          className={ui.linkButton}
                          disabled={sending}
                          onClick={() => removeParticipant(p.id)}
                        >
                          sí, quitar
                        </button>
                        <button
                          type="button"
                          className={ui.linkButton}
                          onClick={() => setRemoving(null)}
                        >
                          cancelar
                        </button>
                      </span>
                    </>
                  ) : (
                    <>
                      <span>{p.name}</span>
                      <button
                        type="button"
                        className={g.remove}
                        disabled={sending}
                        onClick={() => setRemoving(p.id)}
                        aria-label={`quitar a ${p.name} del grupo`}
                      >
                        <CrossIcon />
                      </button>
                    </>
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}
        <div className={g.actions}>
          {isOpen && (
            <Link className={ui.ghost} to={`/g/${group.slug}/compartir`}>
              invitar a más gente
            </Link>
          )}
          {!isDrawn && (
            <button
              type="button"
              className={isOpen ? ui.button : ui.ghost}
              disabled={sending}
              onClick={() => setStatus(isOpen ? "closed" : "open")}
            >
              {isOpen ? "cerrar inscripciones" : "reabrir inscripciones"}
            </button>
          )}
        </div>
      </div>

      <div className={g.adminPart}>
        <h3 className={ui.subtitle}>exclusiones</h3>
        <p className={ui.hint}>
          {isDrawn
            ? "El sorteo ya está hecho: las exclusiones no se pueden cambiar."
            : "Parejas que no pueden tocarse entre sí, en ningún sentido. Por ejemplo, una pareja que ya se hace regalos."}
        </p>

        {exclusions.length > 0 && (
          <ul className={g.pairs}>
            {exclusions.map((e) => (
              <li key={e.id} className={g.pair}>
                <span>{e.participant_a.name}</span>
                <NoMatchIcon />
                <span>{e.participant_b.name}</span>
                {!isDrawn && (
                  <button
                    type="button"
                    className={g.remove}
                    disabled={sending}
                    onClick={() => removeExclusion(e.id)}
                    aria-label={`quitar la exclusión entre ${e.participant_a.name} y ${e.participant_b.name}`}
                  >
                    <CrossIcon />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}

        {!isDrawn && participants.length < 2 && (
          <p className={ui.muted}>Hacen falta al menos dos personas apuntadas.</p>
        )}
        {!isDrawn && participants.length >= 2 && (
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

      <div className={g.adminPart}>
        <div className={g.partHead}>
          <h3 className={ui.subtitle}>sorteo</h3>
          <span className={g.state} data-open={isDrawn}>
            {isDrawn ? "hecho" : "pendiente"}
          </span>
        </div>
        <p className={ui.hint}>
          {isOpen && "Cuando cierres las inscripciones podrás hacer el sorteo."}
          {group.status === "closed" &&
            "Cada persona descubrirá desde su móvil a quién le regala. Nadie más lo verá, tampoco tú."}
          {isDrawn &&
            (seen === 0
              ? "Mientras nadie haya mirado su resultado, puedes repetirlo."
              : `${seen} de ${participants.length} ya lo han visto, así que el sorteo no se puede repetir.`)}
        </p>
        {group.status === "closed" && (
          <button type="button" className={ui.button} disabled={sending} onClick={makeDraw}>
            hacer el sorteo
          </button>
        )}
        {isDrawn && seen < participants.length && <DrawnNotice group={group} />}
        {isDrawn && seen === 0 && (
          <button type="button" className={ui.ghost} disabled={sending} onClick={makeDraw}>
            repetir el sorteo
          </button>
        )}
      </div>

      {isDrawn && (
        <div className={g.adminPart}>
          <div className={g.partHead}>
            <h3 className={ui.subtitle}>celosías</h3>
            <span className={g.state} data-open={unmasked}>
              {unmasked ? "quitadas" : "puestas"}
            </span>
          </div>
          <p className={ui.hint}>
            {unmasked
              ? "Ya todos saben quién les regalaba."
              : "El día del intercambio, quítalas: todos verán quién les regalaba y quién acertó su apuesta."}
          </p>
          {!unmasked && <UnmaskDialog slug={group.slug} guess={guess} />}
        </div>
      )}

      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
    </section>
  );
}

/**
 * Tras el sorteo: a quien tenga los avisos activados le llega una push, pero a la mayoría
 * hay que decírselo. El mensaje de WhatsApp ya va redactado, con el enlace del grupo.
 */
function DrawnNotice({ group }: { group: GroupPublic }) {
  const message = `Ya está hecho el sorteo de "${group.name}". Entra con tu nombre y tu PIN para descubrir a quién le regalas: ${inviteUrl(group.slug)}`;
  return (
    <div className={g.drawnNotice}>
      <p className={ui.hint}>
        Avisa al grupo de que ya pueden entrar. A quien tenga los avisos activados le ha
        llegado uno.
      </p>
      <a
        className={ui.button}
        href={`https://wa.me/?text=${encodeURIComponent(message)}`}
        target="_blank"
        rel="noreferrer"
      >
        <WhatsAppIcon />
        avisar por WhatsApp
      </a>
    </div>
  );
}

function CrossIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true">
      <path d="M3 3l8 8M11 3l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
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
