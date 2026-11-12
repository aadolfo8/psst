import { Link, useRevalidator } from "react-router";

import InstallPrompt from "../../components/InstallPrompt";
import { isInstalled } from "../../lib/platform";
import type {
  ExclusionOut,
  GroupPublic,
  GuessStatus,
  Me,
  ParticipantPublic,
} from "../../lib/api/client";
import { usePolling } from "../../lib/usePolling";
import ui from "../../styles/ui.module.css";
import AdminPanel from "./AdminPanel";
import DemoBar from "./DemoBar";
import g from "./group.module.css";
import GroupHeader from "./GroupHeader";
import Guess from "./Guess";
import PushPrompt from "./PushPrompt";
import Wishlist from "./Wishlist";

const POLL_INTERVAL_MS = 5000;

type Phase = GroupPublic["status"] | "unmasked";

const STEPS: { phase: Phase; label: string }[] = [
  { phase: "open", label: "apuntándose" },
  { phase: "closed", label: "inscripciones cerradas" },
  { phase: "drawn", label: "sorteo hecho" },
  { phase: "unmasked", label: "celosías quitadas" },
];

type Props = {
  me: Me;
  participants: ParticipantPublic[];
  exclusions: ExclusionOut[];
  unread: number;
  guess: GuessStatus | null;
};

export default function Lobby({ me, participants, exclusions, unread, guess }: Props) {
  const { revalidate } = useRevalidator();
  // Vuelve a ejecutar el loader: así aparece quien se acaba de unir.
  usePolling(revalidate, POLL_INTERVAL_MS);

  const group = me.group;
  const unmasked = group.unmasked_at != null;

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      {group.demo && <DemoBar me={me} />}
      <GroupHeader group={group} />
      <Steps phase={unmasked ? "unmasked" : group.status} />
      <InstallPrompt />
      {!unmasked && (
        <PushPrompt
          slug={group.slug}
          where="lobby"
          floating={isInstalled}
          question={
            group.status === "drawn"
              ? "¿Te avisamos cuando te escriban?"
              : "¿Te avisamos cuando se haga el sorteo?"
          }
        />
      )}

      {unmasked && (
        <section className={ui.block}>
          <h2 className={ui.subtitle}>se acabó el misterio</h2>
          <p className={ui.hint}>
            Se han quitado las celosías: ya puedes ver quién te regalaba y quién acertó su
            apuesta.
          </p>
          <Link className={ui.button} to={`/g/${group.slug}/resultados`}>
            ver quién regalaba a quién
          </Link>
          <Link className={unread > 0 ? ui.button : ui.ghost} to={`/g/${group.slug}/chat`}>
            chat
            {unread > 0 && <span className={g.badge}>{unread}</span>}
          </Link>
        </section>
      )}

      {group.status === "drawn" && !unmasked && (
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

      {/* key: en la demo, al cambiar de persona la apuesta empieza de cero. */}
      {guess && !unmasked && (
        <Guess key={me.id} me={me} participants={participants} guess={guess} />
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
        <AdminPanel
          group={group}
          participants={participants}
          exclusions={exclusions}
          guess={guess}
        />
      )}
      <InstallPrompt footer="after-dismiss" />
    </main>
  );
}

/** Barra de cuatro tramos con la fase en la que está el grupo. */
function Steps({ phase }: { phase: Phase }) {
  const current = STEPS.findIndex((step) => step.phase === phase);

  return (
    <ol className={g.steps} aria-label="fase del grupo">
      {STEPS.map((step, i) => {
        const state = i < current ? "done" : i === current ? "current" : "next";
        return (
          <li key={step.phase} data-state={state} aria-current={state === "current" ? "step" : undefined}>
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
