import { api, type PushSubscriptionIn } from "./api/client";

/**
 * Avisos push desde el navegador. Pasos para activarlos en un dispositivo:
 * 1. pedir permiso de notificaciones;
 * 2. suscribirse en el servicio de push del navegador con la clave pública VAPID de la API;
 * 3. guardar esa suscripción en la API, asociada a tu sesión en el grupo.
 */

export type PushState =
  | "unsupported" // navegador sin push (o iOS sin instalar en la pantalla de inicio)
  | "needs-install" // iOS: hay que añadir la web a la pantalla de inicio primero
  | "denied" // el permiso se negó en el navegador; solo se puede cambiar en sus ajustes
  | "off"
  | "on";

const isIOS = /iPhone|iPad|iPod/.test(navigator.userAgent);
const isInstalled = window.matchMedia("(display-mode: standalone)").matches;

export async function getPushState(): Promise<PushState> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
    return isIOS && !isInstalled ? "needs-install" : "unsupported";
  }
  if (Notification.permission === "denied") return "denied";
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  return subscription ? "on" : "off";
}

/** Activa los avisos en este dispositivo. Lanza un Error con un texto para mostrar si falla. */
export async function enablePush(slug: string): Promise<void> {
  const { data } = await api.GET("/push/public-key");
  if (!data) throw new Error("los avisos no están disponibles ahora mismo");

  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("sin permiso no podemos avisarte");

  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: base64UrlToBytes(data.public_key),
  });

  const { response } = await api.PUT("/groups/{slug}/me/push", {
    params: { path: { slug } },
    body: subscription.toJSON() as PushSubscriptionIn,
  });
  if (!response.ok) {
    await subscription.unsubscribe();
    throw new Error("no se ha podido guardar el aviso; vuelve a intentarlo");
  }
}

export async function disablePush(slug: string): Promise<void> {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  if (!subscription) return;
  await api.DELETE("/groups/{slug}/me/push", {
    params: { path: { slug } },
    body: subscription.toJSON() as PushSubscriptionIn,
  });
  await subscription.unsubscribe();
}

/** La clave VAPID viene en base64url; pushManager.subscribe la quiere en bytes. */
function base64UrlToBytes(value: string): Uint8Array<ArrayBuffer> {
  const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
