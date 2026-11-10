import { useState } from "react";
import { Link, useLoaderData } from "react-router";

import { inviteUrl } from "../lib/format";
import ui from "../styles/ui.module.css";
import type { shareLoader } from "./loaders";

export default function Share() {
  const group = useLoaderData<typeof shareLoader>();
  const [copied, setCopied] = useState(false);

  const url = inviteUrl(group.slug);
  const message = `Te apunto al amigo invisible "${group.name}". Entra con tu nombre y un PIN: ${url}`;
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(message)}`;

  async function copy() {
    await navigator.clipboard.writeText(url);
    setCopied(true);
  }

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <h1 className={ui.title}>Invita al grupo.</h1>
      <p className={ui.lead}>
        Comparte este enlace. Cada persona entra con su nombre y un PIN; no hace falta cuenta.
      </p>

      <section className={ui.block}>
        <input className={ui.input} value={url} readOnly aria-label="enlace del grupo" />
        <a className={ui.button} href={whatsappUrl} target="_blank" rel="noreferrer">
          compartir por WhatsApp
        </a>
        <button className={ui.ghost} type="button" onClick={copy}>
          {copied ? "enlace copiado" : "copiar enlace"}
        </button>
      </section>

      <Link to={`/g/${group.slug}`}>ir a la sala de espera</Link>
    </main>
  );
}
