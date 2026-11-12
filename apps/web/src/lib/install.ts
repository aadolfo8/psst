import { useSyncExternalStore } from "react";

import { isAndroid, isInstalled, isIOS } from "./platform";

/**
 * Instalar la web como app. En Android (Chrome) el navegador avisa con el evento
 * `beforeinstallprompt` y se puede abrir su diálogo de instalación desde un botón nuestro.
 * En iOS no existe esa API: solo se puede explicar cómo hacerlo a mano.
 */

export type InstallMode =
  | "installed" // ya está instalada y abierta como app: no hay nada que ofrecer
  | "prompt" // Android/Chrome: un botón abre el diálogo de instalación
  | "ios" // iPhone/iPad: hay que añadirla a la pantalla de inicio a mano
  | "installing" // aceptaste el diálogo y el navegador la está instalando
  | "done" // instalada desde esta pestaña: hay que abrirla desde la pantalla de inicio
  | "manual" // Android sin evento (lo descartaste antes, ya estaba instalada…): desde el menú
  | "unavailable"; // escritorio u otro navegador que no la ofrece

type BeforeInstallPromptEvent = Event & {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

// El navegador lanza el evento una sola vez y puede hacerlo antes de que React pinte nada.
// Por eso se escucha aquí, al importar el módulo, y no dentro de un componente.
const INSTALLED_KEY = "psst-installed";
let deferred: BeforeInstallPromptEvent | null = null;
let installing = false;
let justInstalled = false;
// En la pestaña del navegador no hay forma fiable de saber si la app ya está instalada.
// Lo recordamos al instalarla; si Chrome vuelve a ofrecer instalarla, es que se desinstaló.
let installedBefore = readFlag();
const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((listener) => listener());
}

window.addEventListener("beforeinstallprompt", (event) => {
  event.preventDefault(); // evita la mini-barra por defecto: el botón lo pintamos nosotros
  deferred = event as BeforeInstallPromptEvent;
  installedBefore = false;
  writeFlag(false);
  notify();
});

window.addEventListener("appinstalled", () => {
  deferred = null;
  installing = false;
  justInstalled = true;
  writeFlag(true);
  notify();
});

export function getInstallMode(): InstallMode {
  if (isInstalled) return "installed";
  if (justInstalled) return "done";
  if (installing) return "installing";
  if (deferred) return "prompt";
  if (installedBefore) return "installed";
  if (isIOS) return "ios";
  // Chrome deja de lanzar el evento si descartaste el diálogo antes: el menú sigue funcionando.
  if (isAndroid) return "manual";
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
  // navegador lance otro. Mientras el diálogo está abierto se da por "instalando" para que
  // la tarjeta no cambie a las instrucciones a mano.
  deferred = null;
  installing = true;
  notify();
  await event.prompt();
  const { outcome } = await event.userChoice;
  // Si lo acepta, sigue "instalando" hasta que llegue `appinstalled`.
  if (outcome === "dismissed") {
    installing = false;
    notify();
  }
}

function readFlag(): boolean {
  try {
    return localStorage.getItem(INSTALLED_KEY) === "1";
  } catch {
    return false;
  }
}

function writeFlag(value: boolean) {
  try {
    if (value) localStorage.setItem(INSTALLED_KEY, "1");
    else localStorage.removeItem(INSTALLED_KEY);
  } catch {
    // Sin almacenamiento (modo privado): no pasa nada, solo no lo recordará.
  }
}

export function useInstallMode(): InstallMode {
  return useSyncExternalStore(subscribe, getInstallMode);
}
