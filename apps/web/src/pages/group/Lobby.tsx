import { Link, useRevalidator } from "react-router";

import type { ExclusionOut, GroupPublic, Me, ParticipantPublic } from "../../lib/api/client";
import { usePolling } from "../../lib/usePolling";
import ui from "../../styles/ui.module.css";
import AdminPanel from "./AdminPanel";
import g from "./group.module.css";
import GroupHeader from "./GroupHeader";
import Wishlist from "./Wishlist";

const POLL_INTERVAL_MS = 5000;

const STEPS: { status: GroupPublic["status"]; label: string }[] = [
  { status: "open", label: "apuntándose" },
  { status: "closed", label: "inscripciones cerradas" },
  { status: "drawn", label: "sorteo hecho" },
];

type Props = {
  me: Me;
  participants: ParticipantPublic[];
  exclusions: ExclusionOut[];
  unread: number;
};

export default function Lobby({ me, participants, exclusions, unread }: Props) {
  const { revalidate } = useRevalidator();
  // Vuelve a ejecutar el loader: así aparece quien se acaba de unir.
  usePolling(revalidate, POLL_INTERVAL_MS);

  const group = me.group;

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      <GroupHeader group={group} />
      <Steps status={group.status} />

      {group.status === "drawn" && (
        <section className={ui.block}>
          <h2 className={ui.subtitle}>el sorteo está hecho</h2>
          <p className={ui.hint}>
            {me.revealed
              ? "Ya sabes a quién le regalas. Puedes volver a verlo cuando quieras."
              : "Ya puedes descubrir a quién le regalas. Solo lo vas a ver tú."}
          </p>
          <Link
            className={me.revealed ? ui.ghost : ui.button}
            to={`/g/${group.slug}/revelado`}
          >
            {me.revealed ? "ver a quién le regalo" : "descubrir a quién le regalo"}
          </Link>
          <Link className={unread > 0 ? ui.button : ui.ghost} to={`/g/${group.slug}/chat`}>
            chat secreto
            {unread > 0 && <span className={g.badge}>{unread}</span>}
          </Link>
        </section>
      )}

      <section className={ui.block}>
        <div className={g.sectionHead}>
          <h2 className={ui.subtitle}>apuntados</h2>
          <span className={g.count}>{participants.length}</span>
        </div>
        <ul className={g.people}>
          {participants.map((p) => (
            <Person key={p.id} participant={p} isMe={p.id === me.id} />
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

/** Barra de tres tramos con la fase en la que está el grupo. */
function Steps({ status }: { status: GroupPublic["status"] }) {
  const current = STEPS.findIndex((step) => step.status === status);

  return (
    <ol className={g.steps} aria-label="fase del grupo">
      {STEPS.map((step, i) => {
        const state = i < current ? "done" : i === current ? "current" : "next";
        return (
          <li key={step.status} data-state={state} aria-current={state === "current" ? "step" : undefined}>
            {step.label}
          </li>
        );
      })}
    </ol>
  );
}

function Person({ participant, isMe }: { participant: ParticipantPublic; isMe: boolean }) {
  // [...nombre][0] coge la primera letra aunque sea un carácter compuesto (tildes, emojis).
  const initial = [...participant.name][0]?.toUpperCase();
  const role = [isMe && "tú", participant.is_admin && "organiza"].filter(Boolean).join(" y ");

  return (
    <li className={isMe ? `${g.person} ${g.mine}` : g.person}>
      <span className={g.star} aria-hidden="true">
        {initial}
      </span>
      <span className={g.personName}>{participant.name}</span>
      {role && <span className={g.role}>{role}</span>}
      {participant.has_revealed && <span className={g.seen}>ya lo ha visto</span>}
    </li>
  );
}
