import { useEffect, useRef } from "react";

import type { ChatRole, MessageOut } from "./api/client";

/** Lo que empuja el servidor por el websocket (ver routers/ws.py en la API). */
export type ChatEvent =
  | { type: "message"; role: ChatRole; message: MessageOut }
  | { type: "read"; role: ChatRole }
  | { type: "typing"; role: ChatRole };

const RECONNECT_MIN_MS = 1000;
const RECONNECT_MAX_MS = 15000;

function socketUrl(slug: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  // Mismo origen que la web: la cookie de sesión viaja sola (proxy de Vite / Caddy).
  return `${protocol}//${window.location.host}/api/groups/${slug}/ws`;
}

/**
 * Mantiene abierto el websocket del chat mientras la pantalla está montada.
 * Si se cae, vuelve a conectar esperando cada vez un poco más, y al reconectar avisa
 * (`onReconnect`) para que la pantalla vuelva a pedir lo que se haya perdido mientras tanto.
 * Devuelve `sendTyping(role)` para avisar de que estás escribiendo.
 */
export function useChatSocket(
  slug: string,
  onEvent: (event: ChatEvent) => void,
  onReconnect: () => void,
) {
  const socket = useRef<WebSocket | null>(null);
  // Refs para que el efecto no se reinicie cada vez que cambian los callbacks.
  const handlers = useRef({ onEvent, onReconnect });
  useEffect(() => {
    handlers.current = { onEvent, onReconnect };
  });

  useEffect(() => {
    let closed = false;
    let hadConnected = false;
    let retryDelay = RECONNECT_MIN_MS;
    let retryTimer = 0;

    function connect() {
      const ws = new WebSocket(socketUrl(slug));
      socket.current = ws;

      ws.onopen = () => {
        retryDelay = RECONNECT_MIN_MS;
        if (hadConnected) handlers.current.onReconnect();
        hadConnected = true;
      };
      ws.onmessage = (event) => {
        handlers.current.onEvent(JSON.parse(event.data) as ChatEvent);
      };
      ws.onclose = () => {
        socket.current = null;
        if (closed) return;
        retryTimer = window.setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, RECONNECT_MAX_MS);
      };
    }

    connect();
    return () => {
      closed = true;
      clearTimeout(retryTimer);
      socket.current?.close();
    };
  }, [slug]);

  function sendTyping(role: ChatRole) {
    if (socket.current?.readyState === WebSocket.OPEN) {
      socket.current.send(JSON.stringify({ type: "typing", role }));
    }
  }

  return { sendTyping };
}
