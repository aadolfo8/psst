/**
 * Loaders de React Router: piden los datos antes de pintar cada pantalla.
 * Tras una acción (unirse, guardar, añadir exclusión…) basta con `revalidate()`
 * para que se vuelvan a ejecutar y la pantalla muestre el estado nuevo.
 */
import { data, type LoaderFunctionArgs } from "react-router";

import { api } from "../lib/api/client";

function slugFrom(params: LoaderFunctionArgs["params"]): string {
  return params.slug ?? "";
}

// Lo que se lanza con throw lo recoge el ErrorBoundary de la ruta (RouteError).
function loadFailed(status: number) {
  return status === 404
    ? data("no existe ningún grupo con ese enlace", { status })
    : data("no se ha podido cargar el grupo", { status });
}

async function fetchPublicGroup(slug: string) {
  const { data: group, response } = await api.GET("/groups/{slug}", {
    params: { path: { slug } },
  });
  if (!group) throw loadFailed(response.status);
  return group;
}

export async function shareLoader({ params }: LoaderFunctionArgs) {
  return fetchPublicGroup(slugFrom(params));
}

/**
 * Sala de espera. Si hay sesión en este grupo devuelve todo lo de la sala; si no,
 * solo la info pública para la pantalla de unirse.
 */
export async function groupLoader({ params }: LoaderFunctionArgs) {
  const slug = slugFrom(params);
  const path = { params: { path: { slug } } };

  const { data: me, response } = await api.GET("/groups/{slug}/me", path);
  if (response.status === 401) {
    return { kind: "guest" as const, group: await fetchPublicGroup(slug) };
  }
  if (!me) throw loadFailed(response.status);

  const [participants, exclusions] = await Promise.all([
    api.GET("/groups/{slug}/participants", path),
    me.is_admin ? api.GET("/groups/{slug}/exclusions", path) : null,
  ]);
  return {
    kind: "member" as const,
    me,
    participants: participants.data ?? [],
    exclusions: exclusions?.data ?? [],
  };
}
