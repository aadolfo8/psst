import { useState, type FormEvent } from "react";
import { useRevalidator } from "react-router";

import {
  api,
  errorMessage,
  type GuessStatus,
  type Me,
  type ParticipantPublic,
} from "../../lib/api/client";
import ui from "../../styles/ui.module.css";
import g from "./group.module.css";

type Props = { me: Me; participants: ParticipantPublic[]; guess: GuessStatus };

/**
 * "¿Quién crees que te regala?". Se puede cambiar hasta que el organizador quite las
 * celosías; hasta entonces nadie ve las apuestas de los demás, solo cuántas hay.
 */
export default function Guess({ me, participants, guess }: Props) {
  // Estado local: el polling de la sala no pisa lo que estás eligiendo.
  const [selected, setSelected] = useState(guess.guessed?.id ?? "");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const { revalidate } = useRevalidator();

  const others = participants.filter((p) => p.id !== me.id);
  const unchanged = selected === (guess.guessed?.id ?? "");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    setSending(true);
    setError(null);
    const { error } = await api.PUT("/groups/{slug}/guess", {
      params: { path: { slug: me.group.slug } },
      body: { guessed_id: selected },
    });
    if (!error) await revalidate();
    else setError(errorMessage(error));
    setSending(false);
  }

  return (
    <form className={ui.block} onSubmit={handleSubmit}>
      <h2 className={ui.subtitle}>¿quién crees que te regala?</h2>
      <p className={ui.hint}>
        Nadie verá tu apuesta hasta que el organizador quite las celosías. Entonces se sabrá
        quién acertó. Puedes cambiarla cuando quieras.
      </p>
      <label className={ui.field}>
        mi apuesta
        <select
          className={ui.input}
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
        >
          <option value="" disabled>
            elige a alguien
          </option>
          {others.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <div className={g.wishFooter}>
        {unchanged && guess.guessed ? (
          <span className={g.saved}>
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
              <path
                d="M3 8.5l3 3 7-7"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            apostado por {guess.guessed.name}
          </span>
        ) : (
          <button className={ui.button} disabled={sending || !selected || unchanged}>
            {sending ? "apostando…" : guess.guessed ? "cambiar apuesta" : "apostar"}
          </button>
        )}
        <span className={g.counter}>
          {guess.guessers} de {guess.participants} han apostado
        </span>
      </div>
    </form>
  );
}
