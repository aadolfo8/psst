import { useState } from "react";

import { promptInstall, useInstallMode } from "../lib/install";
import { isInAppBrowser } from "../lib/platform";
import ui from "../styles/ui.module.css";
import s from "./InstallPrompt.module.css";
import ShareIcon from "./ShareIcon";

const DISMISSED_KEY = "psst-install-dismissed";

/**
 * Invita a instalar psst como app. En Android abre el diálogo del navegador con un toque;
 * en iPhone no hay forma de hacerlo desde código, así que explica los pasos.
 */
export default function InstallPrompt() {
  const mode = useInstallMode();
  const [dismissed, setDismissed] = useState(() => remembered());
  const [showSteps, setShowSteps] = useState(false);

  if (dismissed || (mode !== "prompt" && mode !== "ios")) return null;

  function dismiss() {
    remember();
    setDismissed(true);
  }

  return (
    <aside className={s.prompt}>
      <p>
        <strong>¿Te la instalas como app?</strong> Se abre a pantalla completa desde tu
        pantalla de inicio y puede avisarte cuando te escriban.
      </p>

      {mode === "ios" && showSteps && (
        <p>
          {isInAppBrowser
            ? "Primero ábrelo en Safari: desde este navegador no se puede instalar. "
            : ""}
          Toca compartir
          <ShareIcon />y luego «añadir a pantalla de inicio». Ábrelo desde ahí.
        </p>
      )}

      <div className={s.actions}>
        {mode === "prompt" ? (
          <button type="button" className={`${ui.button} ${s.button}`} onClick={promptInstall}>
            instalar la app
          </button>
        ) : (
          !showSteps && (
            <button
              type="button"
              className={`${ui.button} ${s.button}`}
              onClick={() => setShowSteps(true)}
            >
              cómo instalarla
            </button>
          )
        )}
        <button type="button" className={ui.linkButton} onClick={dismiss}>
          ahora no
        </button>
      </div>
    </aside>
  );
}

// "Ahora no" se recuerda en este navegador; si no, volvería a salir en cada visita.
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
