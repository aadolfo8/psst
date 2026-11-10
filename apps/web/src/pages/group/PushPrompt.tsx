import { useEffect, useState } from "react";

import { enablePush, getPushState, type PushState } from "../../lib/push";
import ui from "../../styles/ui.module.css";
import c from "./chat.module.css";

const DISMISSED_KEY = "psst-push-dismissed";

/**
 * Invita a activar los avisos push. Se enseña en el chat cuando ya has recibido algún
 * mensaje: ahí es donde se entiende para qué sirven. En iPhone solo funcionan con la web
 * instalada en la pantalla de inicio, así que primero explica cómo instalarla.
 */
export default function PushPrompt({ slug }: { slug: string }) {
  const [state, setState] = useState<PushState | "loading">("loading");
  const [dismissed, setDismissed] = useState(() => remembered());
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);

  useEffect(() => {
    getPushState().then(setState);
  }, []);

  if (dismissed || state === "loading" || state === "on" || state === "unsupported") return null;

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
    remember();
    setDismissed(true);
  }

  return (
    <aside className={c.prompt}>
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
            <strong>¿Te avisamos cuando te escriban?</strong> Solo recibirás un aviso por
            mensaje, nada más.
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

function ShareIcon() {
  return (
    <svg
      className={c.shareIcon}
      width="16"
      height="18"
      viewBox="0 0 16 18"
      aria-label="icono de compartir"
      role="img"
    >
      <path
        d="M8 1v11M4.5 4.5L8 1l3.5 3.5M3 8H1.5v9h13V8H13"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// "Ahora no" se recuerda en este navegador; si no, la pregunta volvería en cada visita.
function remembered(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

function remember() {
  try {
    localStorage.setItem(DISMISSED_KEY, "1");
  } catch {
    // Sin almacenamiento (modo privado): simplemente volverá a preguntar.
  }
}
