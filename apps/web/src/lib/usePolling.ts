import { useEffect, useRef } from "react";

/**
 * Llama a `callback` cada `intervalMs` mientras la pestaña está visible, y también nada
 * más volver a ella. Es el "tiempo real" de la sala de espera hasta que haya websockets.
 */
export function usePolling(callback: () => void, intervalMs: number) {
  const latest = useRef(callback);
  useEffect(() => {
    latest.current = callback;
  });

  useEffect(() => {
    const tick = () => {
      if (document.visibilityState === "visible") latest.current();
    };
    const id = setInterval(tick, intervalMs);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
  }, [intervalMs]);
}
