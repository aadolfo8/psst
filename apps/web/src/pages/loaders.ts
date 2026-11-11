/**
 * Loaders de React Router: piden los datos antes de pintar cada pantalla.
 * Tras una acción (unirse, guardar, añadir exclusión…) basta con `revalidate()`
 * para que se vuelvan a ejecutar y la pantalla muestre el estado nuevo.
 */
import { data, redirect, type LoaderFunctionArgs } from "react-router";

import { api, type GroupPublic } from "../lib/api/client";
import { isInstalled } from "../lib/platform";

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

/**
 * Inicio. Pide los grupos en los que este navegador ya tiene sesión. Con la app instalada
 * (que siempre arranca aquí) y un solo grupo, entra directamente a él; en el navegador no se
 * redirige, para no rebotar a quien viene a crear un grupo nuevo.
 */
export async function homeLoader() {
  // Solo al arrancar: si no, el logo «psst» de las pantallas del grupo (que enlaza a /)
  // devolvería siempre al grupo y nunca se podría llegar al inicio desde la app.
  const launching = launchedAtHome;
  launchedAtHome = false;

  const groups = await fetchMyGroups();
  if (launching && isInstalled && groups.length === 1) throw redirect(`/g/${groups[0].slug}`);
  return { groups };
}

// La app instalada arranca en "/" (start_url del manifest).
let launchedAtHome = location.pathname === "/";

async function fetchMyGroups(): Promise<GroupPublic[]> {
  try {
    const { data: groups } = await api.GET("/me/groups");
    return groups ?? [];
  } catch {
    // Sin conexión o API caída: el inicio tiene que abrir igual, solo sin "tus grupos".
    return [];
  }
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

  const drawn = me.group.status === "drawn";
  const [participants, exclusions, chat, guess] = await Promise.all([
    api.GET("/groups/{slug}/participants", path),
    me.is_admin ? api.GET("/groups/{slug}/exclusions", path) : null,
    drawn ? api.GET("/groups/{slug}/chat", path) : null,
    drawn ? api.GET("/groups/{slug}/guess", path) : null,
  ]);
  return {
    kind: "member" as const,
    me,
    participants: participants.data ?? [],
    exclusions: exclusions?.data ?? [],
    unread: (chat?.data?.as_giver ?? 0) + (chat?.data?.as_receiver ?? 0),
    guess: guess?.data ?? null,
  };
}

/**
 * Revelado. Sin sesión o sin sorteo, de vuelta a la sala. Si ya habías visto tu resultado se
 * pide aquí mismo y la pantalla sale abierta; si no, el nombre no se pide hasta que pulsas
 * "abrir la celosía" (así no está en la página antes de tiempo).
 */
export async function revealLoader({ params }: LoaderFunctionArgs) {
  const slug = slugFrom(params);
  const path = { params: { path: { slug } } };

  const { data: me, response } = await api.GET("/groups/{slug}/me", path);
  if (response.status === 401) throw redirect(`/g/${slug}`);
  if (!me) throw loadFailed(response.status);
  if (me.group.status !== "drawn") throw redirect(`/g/${slug}`);

  if (!me.revealed) return { me, receiver: null };
  const { data: revealed, response: revealResponse } = await api.POST(
    "/groups/{slug}/me/reveal",
    path,
  );
  if (!revealed) throw loadFailed(revealResponse.status);
  return { me, receiver: revealed.receiver };
}

/** /demo: crea un grupo de ejemplo, entra como Lucía y lleva a su sala. */
export async function demoLoader() {
  const { data, response } = await api.POST("/demo");
  if (!data) throw loadFailed(response.status);
  return redirect(`/g/${data.group.slug}`);
}

/**
 * Chat. Siempre está la conversación con quien te regala; la de a quien regalas solo si ya
 * has abierto la celosía (hasta entonces el nombre no debe aparecer en esta pantalla).
 */
export async function chatLoader({ params }: LoaderFunctionArgs) {
  const slug = slugFrom(params);
  const path = { params: { path: { slug } } };

  const { data: me, response } = await api.GET("/groups/{slug}/me", path);
  if (response.status === 401) throw redirect(`/g/${slug}`);
  if (!me) throw loadFailed(response.status);
  if (me.group.status !== "drawn") throw redirect(`/g/${slug}`);

  const role = (value: "giver" | "receiver") => ({ params: { path: { slug, role: value } } });
  const [asReceiver, asGiver, revealed] = await Promise.all([
    api.GET("/groups/{slug}/chat/{role}", role("receiver")),
    me.revealed ? api.GET("/groups/{slug}/chat/{role}", role("giver")) : null,
    me.revealed ? api.POST("/groups/{slug}/me/reveal", path) : null,
  ]);
  if (!asReceiver.data) throw loadFailed(asReceiver.response.status);

  return {
    me,
    asReceiver: asReceiver.data.messages,
    asGiver: asGiver?.data?.messages ?? null,
    receiverName: revealed?.data?.receiver.name ?? null,
    // Solo cuando el organizador ya ha quitado las celosías.
    giverName: asReceiver.data.giver_name ?? null,
  };
}

/** Resultados: quién regalaba a quién y quién acertó. Solo con las celosías quitadas. */
export async function resultsLoader({ params }: LoaderFunctionArgs) {
  const slug = slugFrom(params);
  const path = { params: { path: { slug } } };

  const { data: me, response } = await api.GET("/groups/{slug}/me", path);
  if (response.status === 401) throw redirect(`/g/${slug}`);
  if (!me) throw loadFailed(response.status);
  if (!me.group.unmasked_at) throw redirect(`/g/${slug}`);

  const { data: results, response: resultsResponse } = await api.GET(
    "/groups/{slug}/results",
    path,
  );
  if (!results) throw loadFailed(resultsResponse.status);
  return { me, pairs: results.pairs };
}
