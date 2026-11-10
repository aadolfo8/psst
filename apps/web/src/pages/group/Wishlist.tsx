import { useState, type FormEvent } from "react";

import { api, errorMessage, type Me } from "../../lib/api/client";
import ui from "../../styles/ui.module.css";
import g from "./group.module.css";

const MAX_LENGTH = 1000;

export default function Wishlist({ me }: { me: Me }) {
  // Estado local: el polling de la sala no pisa lo que estás escribiendo.
  const [text, setText] = useState(me.wishlist);
  const [saved, setSaved] = useState(me.wishlist);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError(null);
    const { data, error } = await api.PUT("/groups/{slug}/me/wishlist", {
      params: { path: { slug: me.group.slug } },
      body: { wishlist: text },
    });
    setSending(false);

    if (data) {
      setText(data.wishlist);
      setSaved(data.wishlist);
    } else {
      setError(errorMessage(error));
    }
  }

  const unchanged = text.trim() === saved;

  return (
    <form className={ui.block} onSubmit={handleSubmit}>
      <h2 className={ui.subtitle}>tu lista de deseos</h2>
      <p className={ui.hint}>
        La verá solo quien te regale. Tallas, gustos, lo que ya tienes… cuanto más concreta,
        mejor.
      </p>
      <textarea
        className={ui.input}
        value={text}
        onChange={(event) => setText(event.target.value)}
        maxLength={MAX_LENGTH}
        aria-label="tu lista de deseos"
        placeholder="me encantaría…"
      />
      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <div className={g.wishFooter}>
        {unchanged && saved ? (
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
            guardada
          </span>
        ) : (
          <button className={unchanged ? ui.ghost : ui.button} disabled={sending || unchanged}>
            {sending ? "guardando…" : "guardar"}
          </button>
        )}
        <span className={g.counter}>
          {text.length}/{MAX_LENGTH}
        </span>
      </div>
    </form>
  );
}
