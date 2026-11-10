import createClient from "openapi-fetch";

import type { components, paths } from "./schema";

/**
 * Cliente tipado de la API. Los tipos salen de `schema.d.ts`, que se genera a partir del
 * OpenAPI de FastAPI con `pnpm gen:api`: si la API cambia, TypeScript avisa aquí.
 *
 * Las rutas van a `/api` en el mismo origen (proxy de Vite en desarrollo, Caddy en
 * producción), así que el navegador envía la cookie de sesión sin configurar nada.
 */
export const api = createClient<paths>({ baseUrl: "/api" });

type Schemas = components["schemas"];
export type Me = Schemas["Me"];
export type GroupPublic = Schemas["GroupPublic"];
export type ParticipantPublic = Schemas["ParticipantPublic"];
export type ExclusionOut = Schemas["ExclusionOut"];
export type RevealedReceiver = Schemas["RevealedReceiver"];

/** Mensaje para mostrar a partir del cuerpo de una respuesta de error de la API. */
export function errorMessage(error: unknown): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") return detail;
  // 422 de Pydantic: una lista de errores de validación pensada para programadores.
  if (Array.isArray(detail)) return "revisa los datos: hay algún campo que no es válido";
  return "algo ha fallado; vuelve a intentarlo";
}
