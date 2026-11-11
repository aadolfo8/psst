/** Qué dispositivo y navegador son, para saber cómo se puede instalar la web. */

const ua = navigator.userAgent;

export const isIOS = /iPhone|iPad|iPod/.test(ua);

export const isAndroid = /Android/.test(ua);

/** Abierta desde la pantalla de inicio (PWA instalada), no desde una pestaña del navegador. */
export const isInstalled =
  window.matchMedia("(display-mode: standalone)").matches ||
  // Safari en iOS no soporta display-mode: lo marca con esta propiedad propia.
  (navigator as Navigator & { standalone?: boolean }).standalone === true;

/**
 * Navegador interno de una app (WhatsApp, Instagram, Facebook…). En iOS desde ahí no se
 * puede añadir a la pantalla de inicio: hay que abrir el enlace en Safari. Se reconoce
 * porque su user agent no incluye "Safari", o por el nombre de la app.
 */
export const isInAppBrowser = isIOS && (!/Safari/.test(ua) || /FBAN|FBAV|Instagram|Line\//.test(ua));
