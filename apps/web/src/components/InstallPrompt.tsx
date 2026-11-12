import { useState, useSyncExternalStore } from "react";

import { promptInstall, useInstallMode, type InstallMode } from "../lib/install";
import { isInAppBrowser } from "../lib/platform";
import ui from "../styles/ui.module.css";
import s from "./InstallPrompt.module.css";
import ShareIcon from "./ShareIcon";

const DISMISSED_KEY = "psst-install-dismissed";

/**
 * Invita a instalar psst como app. En Android abre el diálogo del navegador con un toque;
 * en iPhone no hay forma de hacerlo desde código, así que explica los pasos.
 */
export default function InstallPrompt({ footer }: { footer?: "always" | "after-dismiss" }) {
  const mode = useInstallMode();
  const dismissed = useSyncExternalStore(subscribeDismissed, () => dismissedNow);
  const [showSteps, setShowSteps] = useState(false);

  if (mode === "installed" || mode === "unavailable") return null;

  function dismiss() {
    remember();
    setShowSteps(false);
  }

  // Sin `footer` es la tarjeta grande, mientras no digas "ahora no". Con `footer` es un
  // enlace pequeño al pie: "always" en páginas sin tarjeta; "after-dismiss" en las que la
  // tienen, para que salga en cuanto la descartes y no estén las dos a la vez.
  const visible = footer === "always" || (footer === "after-dismiss") === dismissed;
  if (!visible) return null;

  if (footer) {
    return (
      <footer className={s.discreet}>
        <button
          type="button"
          className={ui.linkButton}
          onClick={mode === "prompt" ? promptInstall : () => setShowSteps((open) => !open)}
        >
          instalar la app
        </button>
        {showSteps && <Steps mode={mode} />}
      </footer>
    );
  }

  return (
    <aside className={s.prompt}>
      <p>
        <strong>¿Te la instalas como app?</strong> Se abre a pantalla completa desde tu
        pantalla de inicio y puede avisarte cuando te escriban.
      </p>

      {showSteps && <Steps mode={mode} />}

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

function Steps({ mode }: { mode: InstallMode }) {
  if (mode === "ios") {
    return (
      <p>
        {isInAppBrowser ? "Primero ábrelo en Safari: desde este navegador no se puede instalar. " : ""}
        Toca compartir
        <ShareIcon />y luego «añadir a pantalla de inicio». Ábrelo desde ahí. En iPhone la app
        no comparte la sesión con Safari: la primera vez pega el enlace del grupo y entra con tu
        nombre y tu PIN.
      </p>
    );
  }
  if (mode === "manual") {
    return (
      <p>
        Abre el menú del navegador (los tres puntos) y toca «instalar aplicación» o «añadir a
        pantalla de inicio». Ábrelo desde ahí.
      </p>
    );
  }
  return null;
}

// "Ahora no" se recuerda en este navegador; si no, volvería a salir en cada visita.
function remembered(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

// Las dos versiones del aviso (tarjeta y enlace al pie) comparten este estado.
let dismissedNow = remembered();
const dismissedListeners = new Set<() => void>();

function subscribeDismissed(listener: () => void) {
  dismissedListeners.add(listener);
  return () => {
    dismissedListeners.delete(listener);
  };
}

function remember() {
  dismissedNow = true;
  dismissedListeners.forEach((listener) => listener());
  try {
    localStorage.setItem(DISMISSED_KEY, "1");
  } catch {
    // Sin almacenamiento (modo privado): simplemente volverá a preguntar.
  }
}
