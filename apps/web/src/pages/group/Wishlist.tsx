import { useState, type FormEvent } from "react";

import { api, errorMessage, type Me } from "../../lib/api/client";
import ui from "../../styles/ui.module.css";

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
        maxLength={1000}
        aria-label="tu lista de deseos"
        placeholder="me encantaría…"
      />
      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <button className={ui.ghost} disabled={sending || unchanged}>
        {unchanged && saved ? "guardada" : "guardar"}
      </button>
    </form>
  );
}
