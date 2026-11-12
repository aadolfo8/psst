import { useEffect, useState } from "react";

import ShareIcon from "../../components/ShareIcon";
import { enablePush, getPushState, type PushState } from "../../lib/push";
import ui from "../../styles/ui.module.css";
import c from "./chat.module.css";

// "Ahora no" se recuerda aparte en el chat y en la sala: son preguntas distintas.
const DISMISSED_KEY = { chat: "psst-push-dismissed", lobby: "psst-push-dismissed-lobby" };

type Props = {
  slug: string;
  /** La pregunta en negrita: cambia según lo que vayamos a avisar. */
  question?: string;
  /**
   * En la sala: no repite cómo instalar la app (ya lo dice su propio aviso) y, si la app está
   * instalada, sale como hoja flotante abajo, lo primero que ves al abrirla.
   */
  where?: "chat" | "lobby";
  floating?: boolean;
};

/**
 * Invita a activar los avisos push. En el chat sale cuando ya has recibido algún mensaje; en
 * la sala, desde el principio, para avisar del sorteo. En iPhone solo funcionan con la web
 * instalada en la pantalla de inicio, así que en el chat primero explica cómo instalarla.
 */
export default function PushPrompt({
  slug,
  question = "¿Te avisamos cuando te escriban?",
  where = "chat",
  floating = false,
}: Props) {
  const [state, setState] = useState<PushState | "loading">("loading");
  const [dismissed, setDismissed] = useState(() => remembered(DISMISSED_KEY[where]));
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    getPushState().then(setState);
  }, []);

  if (dismissed || state === "loading" || state === "on" || state === "unsupported") return null;
  if (where === "lobby" && state !== "off") return null;

  async function enable() {
    setWorking(true);
    setError(null);
    try {
      await enablePush(slug);
      setState("on");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "no se han podido activar");
      setState(await getPushState());
    } finally {
      setWorking(false);
    }
  }

  function dismiss() {
    remember(DISMISSED_KEY[where]);
    setDismissed(true);
  }

  return (
    <aside className={floating ? `${c.prompt} ${c.floating}` : c.prompt}>
      {state === "needs-install" ? (
        <>
          <p>
            <strong>¿Quieres que te avise cuando te escriban?</strong> En iPhone hace falta
            añadir psst a la pantalla de inicio: toca compartir
            <ShareIcon />y luego «añadir a pantalla de inicio». Ábrelo desde ahí y activa los
            avisos.
          </p>
          <button type="button" className={ui.linkButton} onClick={dismiss}>
            ahora no
          </button>
        </>
      ) : state === "denied" ? (
        <>
          <p>Los avisos están bloqueados en el navegador. Puedes permitirlos en sus ajustes.</p>
          <button type="button" className={ui.linkButton} onClick={dismiss}>
            entendido
          </button>
        </>
      ) : (
        <>
          <p>
            <strong>{question}</strong> Solo te avisaremos de lo importante, nada más.
          </p>
          {error && (
            <p className={ui.error} role="alert">
              {error}
            </p>
          )}
          <div className={c.promptActions}>
            <button
              type="button"
              className={`${ui.button} ${c.promptButton}`}
              onClick={enable}
              disabled={working}
            >
              activar avisos
            </button>
            <button type="button" className={ui.linkButton} onClick={dismiss}>
              ahora no
            </button>
          </div>
        </>
      )}
    </aside>
  );
}

// "Ahora no" se recuerda en este navegador; si no, la pregunta volvería en cada visita.
function remembered(key: string): boolean {
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function remember(key: string) {
  try {
    localStorage.setItem(key, "1");
  } catch {
    // Sin almacenamiento (modo privado): simplemente volverá a preguntar.
  }
}
