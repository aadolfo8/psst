import { useState } from "react";
import { Link, useLoaderData } from "react-router";

import { api, errorMessage, type RevealedReceiver } from "../../lib/api/client";
import { groupDetails } from "../../lib/format";
import ui from "../../styles/ui.module.css";
import type { revealLoader } from "../loaders";
import r from "./reveal.module.css";

/**
 * A quién le regalas. El nombre está detrás de dos hojas de celosía; al pulsar se pide a la
 * API, se pinta desenfocado detrás de las hojas y estas se abren (ver reveal.module.css).
 * Si ya lo habías visto, la ventana sale abierta y sin animación.
 */
export default function Reveal() {
  const { me, receiver: alreadySeen } = useLoaderData<typeof revealLoader>();
  const [receiver, setReceiver] = useState<RevealedReceiver | null>(alreadySeen);
  // Solo es true si se abre ahora: es lo que activa la animación.
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const group = me.group;

  async function open() {
    setSending(true);
    setError(null);
    const { data, error } = await api.POST("/groups/{slug}/me/reveal", {
      params: { path: { slug: group.slug } },
    });
    setSending(false);

    if (data) {
      setReceiver(data.receiver);
      setOpening(true);
    } else {
      setError(errorMessage(error));
    }
  }

  const windowClass = [r.window, opening && r.opening].filter(Boolean).join(" ");
  const afterClass = opening ? r.after : undefined;

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <h1 className={ui.title}>te toca regalar a</h1>

      <div className={windowClass}>
        {receiver && (
          <span className={r.name} aria-live="polite">
            {receiver.name}
          </span>
        )}
        {(!receiver || opening) && (
          <>
            <div className={`${ui.lattice} ${r.leaf} ${r.left}`} aria-hidden="true" />
            <div className={`${ui.lattice} ${r.leaf} ${r.right}`} aria-hidden="true" />
            <div className={`${ui.lattice} ${r.shadow}`} aria-hidden="true" />
          </>
        )}
      </div>

      {!receiver && (
        <>
          <p className={ui.hint}>Solo lo vas a ver tú. Nadie más sabrá a quién le regalas.</p>
          {error && (
            <p className={ui.error} role="alert">
              {error}
            </p>
          )}
          <button type="button" className={ui.button} disabled={sending} onClick={open}>
            abrir la celosía
          </button>
        </>
      )}

      {receiver && (
        <div className={afterClass}>
          <div className={r.details}>
            {groupDetails(group).length > 0 && (
              <ul className={r.facts}>
                {groupDetails(group).map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            )}

            <section className={ui.block}>
              <h2 className={ui.subtitle}>su lista de deseos</h2>
              {receiver.wishlist ? (
                <p className={r.wishlist}>{receiver.wishlist}</p>
              ) : (
                <p className={ui.hint}>
                  Todavía no ha escrito nada. Si la escribe, la verás aquí.
                </p>
              )}
            </section>

            <Link to={`/g/${group.slug}/chat`} className={ui.button}>
              preguntarle algo en secreto
            </Link>
            <Link to={`/g/${group.slug}`} className={ui.textLink}>
              volver a la sala
            </Link>
          </div>
        </div>
      )}
    </main>
  );
}
