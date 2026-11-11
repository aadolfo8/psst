import { useSyncExternalStore } from "react";

import { isInstalled, isIOS } from "./platform";

/**
 * Instalar la web como app. En Android (Chrome) el navegador avisa con el evento
 * `beforeinstallprompt` y se puede abrir su diálogo de instalación desde un botón nuestro.
 * En iOS no existe esa API: solo se puede explicar cómo hacerlo a mano.
 */

export type InstallMode =
  | "installed" // ya está instalada y abierta como app: no hay nada que ofrecer
  | "prompt" // Android/Chrome: un botón abre el diálogo de instalación
  | "ios" // iPhone/iPad: hay que añadirla a la pantalla de inicio a mano
  | "unavailable"; // el navegador no la ofrece (o todavía no)

type BeforeInstallPromptEvent = Event & {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

// El navegador lanza el evento una sola vez y puede hacerlo antes de que React pinte nada.
// Por eso se escucha aquí, al importar el módulo, y no dentro de un componente.
let deferred: BeforeInstallPromptEvent | null = null;
let installed = isInstalled;
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault(); // evita la mini-barra por defecto: el botón lo pintamos nosotros
  deferred = event as BeforeInstallPromptEvent;
  notify();
});

window.addEventListener("appinstalled", () => {
  deferred = null;
  installed = true;
  notify();
});

export function getInstallMode(): InstallMode {
  if (installed) return "installed";
  if (deferred) return "prompt";
  if (isIOS) return "ios";
  return "unavailable";
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Abre el diálogo de instalación del navegador. Solo tiene efecto en el modo "prompt". */
export async function promptInstall(): Promise<void> {
  if (!deferred) return;
  const event = deferred;
  // El evento solo sirve una vez: se acepte o se rechace, hay que esperar a que el
  // navegador lance otro.
  deferred = null;
  notify();
  await event.prompt();
  await event.userChoice;
}

export function useInstallMode(): InstallMode {
  return useSyncExternalStore(subscribe, getInstallMode);
}
