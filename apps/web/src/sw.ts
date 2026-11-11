/// <reference lib="webworker" />
/**
 * Service worker de psst. Dos cosas:
 * 1. Guarda en caché los ficheros de la web (los inyecta vite-plugin-pwa en __WB_MANIFEST)
 *    para que abra sin conexión y arranque al instante como app instalada.
 * 2. Recibe las notificaciones push y las muestra; al tocarlas abre el chat.
 *
 * Las llamadas a /api nunca se cachean: siempre van a la red.
 */
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";

declare const self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();

// Cualquier ruta de la SPA (/g/abc/chat…) se sirve con el index.html cacheado.
// En desarrollo no hay precaché (Vite sirve todo al vuelo), así que esta ruta no existe.
if (!import.meta.env.DEV) {
  const appShell = createHandlerBoundToURL("/index.html");
  registerRoute(new NavigationRoute(appShell, { denylist: [/^\/api\//] }));
}

// Una versión nueva del service worker toma el control sin esperar a cerrar todas las pestañas.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

/** Lo que manda la API en cada push (ver push_payload en routers/chat.py). */
type PushPayload = { title: string; body: string; url: string };

self.addEventListener("push", (event) => {
  if (!event.data) return;
  const payload = event.data.json() as PushPayload;
  event.waitUntil(
    self.registration.showNotification(payload.title, {
      body: payload.body,
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      tag: payload.url, // varios mensajes del mismo chat se agrupan en un aviso
      data: { url: payload.url },
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data as { url: string }).url;
  event.waitUntil(openChat(url));
});

/** Si la app ya está abierta, la trae al frente y navega; si no, abre una ventana nueva. */
async function openChat(url: string) {
  const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  const existing = windows[0];
  if (existing) {
    await existing.focus();
    await existing.navigate(url);
  } else {
    await self.clients.openWindow(url);
  }
}
