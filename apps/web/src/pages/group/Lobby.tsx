import { Link, useRevalidator } from "react-router";

import type { ExclusionOut, Me, ParticipantPublic } from "../../lib/api/client";
import { groupDetails } from "../../lib/format";
import { usePolling } from "../../lib/usePolling";
import ui from "../../styles/ui.module.css";
import AdminPanel from "./AdminPanel";
import Wishlist from "./Wishlist";

const POLL_INTERVAL_MS = 5000;

type Props = {
  me: Me;
  participants: ParticipantPublic[];
  exclusions: ExclusionOut[];
};

export default function Lobby({ me, participants, exclusions }: Props) {
  const { revalidate } = useRevalidator();
  // Vuelve a ejecutar el loader: así aparece quien se acaba de unir.
  usePolling(revalidate, POLL_INTERVAL_MS);

  const group = me.group;

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <h1 className={ui.title}>{group.name}</h1>
      <ul className={ui.details}>
        {groupDetails(group).map((detail) => (
          <li key={detail}>{detail}</li>
        ))}
      </ul>

      <section className={ui.block}>
        <h2 className={ui.subtitle}>apuntados ({participants.length})</h2>
        <ul className={ui.list}>
          {participants.map((p) => (
            <li key={p.id}>
              <span>{p.name}</span>
              <span className={ui.tags}>
                {p.id === me.id && <span className={ui.tag}>tú</span>}
                {p.is_admin && <span className={ui.tag}>organiza</span>}
              </span>
            </li>
          ))}
        </ul>
        {group.status === "open" && !me.is_admin && (
          <p className={ui.hint}>Cuando estéis todos, el organizador hará el sorteo.</p>
        )}
        {group.status === "closed" && !me.is_admin && (
          <p className={ui.hint}>Las inscripciones están cerradas. El sorteo será pronto.</p>
        )}
      </section>

      <Wishlist me={me} />

      {me.is_admin && (
        <AdminPanel group={group} participants={participants} exclusions={exclusions} />
      )}
    </main>
  );
}
