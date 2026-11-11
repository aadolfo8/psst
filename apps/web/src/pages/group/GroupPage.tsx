import { useLoaderData } from "react-router";

import type { groupLoader } from "../loaders";
import JoinScreen from "./JoinScreen";
import Lobby from "./Lobby";

/** /g/:slug es el enlace de invitación: sin sesión muestra unirse; con sesión, la sala. */
export default function GroupPage() {
  const data = useLoaderData<typeof groupLoader>();

  if (data.kind === "guest") return <JoinScreen group={data.group} />;
  return (
    <Lobby
      me={data.me}
      participants={data.participants}
      exclusions={data.exclusions}
      unread={data.unread}
      guess={data.guess}
    />
  );
}
