import { Link, useLoaderData } from "react-router";

import type { ResultPair } from "../../lib/api/client";
import ui from "../../styles/ui.module.css";
import type { resultsLoader } from "../loaders";
import DemoBar from "./DemoBar";
import s from "./results.module.css";

/**
 * Con las celosías ya quitadas: quién te regalaba, quién acertó su apuesta (detectives),
 * a quién no descubrió nadie (espías) y la cadena completa del sorteo.
 */
export default function Results() {
  const { me, pairs } = useLoaderData<typeof resultsLoader>();
  const group = me.group;

  const mine = pairs.find((p) => p.receiver.id === me.id);
  const detectives = pairs.filter((p) => p.guessed_right).map((p) => p.receiver.name);
  const spies = pairs.filter((p) => !p.guessed_right).map((p) => p.giver.name);

  return (
    <main className={ui.page}>
      <Link to="/" className={ui.logo}>
        psst
      </Link>
      {group.demo && <DemoBar me={me} />}
      <h1 className={ui.title}>se acabó el misterio</h1>

      {mine && (
        <section className={s.mine}>
          <span className={s.label}>te regalaba</span>
          <span className={s.name}>{mine.giver.name}</span>
          <span className={s.label}>{myGuessText(mine)}</span>
        </section>
      )}

      <section className={ui.block}>
        <h2 className={ui.subtitle}>detectives</h2>
        <p className={ui.hint}>Acertaron quién les regalaba.</p>
        <Names names={detectives} empty="Nadie acertó. Buen trabajo, espías." />
      </section>

      <section className={ui.block}>
        <h2 className={ui.subtitle}>espías</h2>
        <p className={ui.hint}>Nadie descubrió que regalaban ellos.</p>
        <Names names={spies} empty="Todos fueron descubiertos." />
      </section>

      <section className={ui.block}>
        <h2 className={ui.subtitle}>la cadena</h2>
        <ol className={s.chain}>
          {pairs.map((pair) => (
            <li key={pair.giver.id}>
              <p className={s.link}>
                <strong>{pair.giver.name}</strong> regalaba a <strong>{pair.receiver.name}</strong>
              </p>
              <p className={s.bet} data-right={pair.guessed_right}>
                {betText(pair)}
              </p>
            </li>
          ))}
        </ol>
      </section>

      <Link to={`/g/${group.slug}/chat`} className={ui.ghost}>
        ir al chat
      </Link>
      <Link to={`/g/${group.slug}`} className={ui.textLink}>
        volver a la sala
      </Link>
    </main>
  );
}

function myGuessText(pair: ResultPair): string {
  if (!pair.receiver_guess) return "no llegaste a apostar";
  if (pair.guessed_right) return "y lo adivinaste";
  return `tú apostaste por ${pair.receiver_guess.name}`;
}

function betText(pair: ResultPair): string {
  const who = pair.receiver.name;
  if (!pair.receiver_guess) return `${who} no apostó`;
  if (pair.guessed_right) return `${who} lo adivinó`;
  return `${who} apostó por ${pair.receiver_guess.name}`;
}

function Names({ names, empty }: { names: string[]; empty: string }) {
  if (names.length === 0) return <p className={ui.muted}>{empty}</p>;
  return (
    <ul className={s.names}>
      {names.map((name) => (
        <li key={name}>{name}</li>
      ))}
    </ul>
  );
}
