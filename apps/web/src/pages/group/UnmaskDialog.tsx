import { useRef, useState, type FormEvent } from "react";
import { useRevalidator } from "react-router";

import {
  api,
  errorMessage,
  isUnmaskPhrase,
  UNMASK_PHRASE,
  type GuessStatus,
} from "../../lib/api/client";
import ui from "../../styles/ui.module.css";
import g from "./group.module.css";

type Props = { slug: string; guess: GuessStatus | null };

/**
 * Botón "quitar las celosías" del organizador. No se puede deshacer, así que abre un
 * diálogo que explica lo que va a pasar y pide escribir la frase de confirmación.
 * Es un <dialog> nativo con showModal(): bloquea el resto de la página y se cierra con Esc,
 * pero no es un confirm() del navegador.
 */
export default function UnmaskDialog({ slug, guess }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const { revalidate } = useRevalidator();
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const missing = guess ? guess.participants - guess.guessers : 0;

  function open() {
    setText("");
    setError(null);
    dialog.current?.showModal();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isUnmaskPhrase(text)) return;
    setSending(true);
    setError(null);
    const { error } = await api.POST("/groups/{slug}/unmask", {
      params: { path: { slug } },
      body: { confirm: text },
    });
    if (error) {
      setError(errorMessage(error));
      setSending(false);
      return;
    }
    dialog.current?.close();
    await revalidate();
    setSending(false);
  }

  return (
    <>
      <button type="button" className={ui.ghost} onClick={open}>
        quitar las celosías
      </button>

      <dialog ref={dialog} className={g.dialog} aria-labelledby="unmask-title">
        <form className={ui.form} onSubmit={handleSubmit}>
          <h2 id="unmask-title" className={ui.subtitle}>
            ¿quitar las celosías?
          </h2>
          <ul className={g.consequences}>
            <li>Todos verán quién les regalaba, también en el chat.</li>
            <li>Se cierran las apuestas y se publica quién acertó.</li>
            <li>
              <strong>No se puede deshacer.</strong> Hazlo cuando ya os hayáis dado los regalos.
            </li>
          </ul>
          {missing > 0 && (
            <p className={g.warning}>
              {missing === 1
                ? "Falta 1 persona por apostar."
                : `Faltan ${missing} personas por apostar.`}
            </p>
          )}
          <label className={ui.field}>
            para confirmar, escribe «{UNMASK_PHRASE}»
            <input
              className={ui.input}
              value={text}
              onChange={(event) => setText(event.target.value)}
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
          </label>
          {error && (
            <p className={ui.error} role="alert">
              {error}
            </p>
          )}
          <div className={g.dialogActions}>
            <button className={ui.button} disabled={sending || !isUnmaskPhrase(text)}>
              {sending ? "quitando…" : "quitar las celosías"}
            </button>
            <button
              type="button"
              className={ui.ghost}
              disabled={sending}
              onClick={() => dialog.current?.close()}
            >
              cancelar
            </button>
          </div>
        </form>
      </dialog>
    </>
  );
}
