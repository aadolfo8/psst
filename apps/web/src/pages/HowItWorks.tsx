import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

import ui from "../styles/ui.module.css";
import s from "./HowItWorks.module.css";

type Step = { title: string; text: string; scene: ReactNode };

const STEPS: Step[] = [
  {
    title: "crea el grupo y pásalo por WhatsApp",
    text: "Le pones nombre, presupuesto y fecha. El mensaje con el enlace ya va escrito: solo tienes que enviarlo.",
    scene: <ShareScene />,
  },
  {
    title: "cada uno entra con su nombre y un PIN",
    text: "Sin cuentas, sin email y sin teléfono. Cada persona escribe su lista de deseos para dar pistas.",
    scene: <JoinScene />,
  },
  {
    title: "el sorteo, y cada uno abre su celosía",
    text: "Nadie se toca a sí mismo y puedes evitar parejas. Solo tú ves a quién le regalas: tampoco el organizador.",
    scene: <RevealScene />,
  },
  {
    title: "pregúntale sin que sepa que eres tú",
    text: "Un chat secreto entre quien regala y quien recibe. Tú sabes con quién hablas; al otro lado solo se ve una celosía.",
    scene: <ChatScene />,
  },
  {
    title: "el día del intercambio, fuera celosías",
    text: "El organizador las quita y todos descubren quién les regalaba. Y quién acertó su apuesta.",
    scene: <UnmaskScene />,
  },
];

/**
 * "Así funciona": una pista de cinco pantallas de alto con una pantalla fija dentro. Arriba,
 * el título y el progreso; en el centro, la escena del paso activo a todo tamaño; debajo, su
 * frase. El paso activo sale de cuánto se ha recorrido la pista, y cada escena se anima solo
 * con CSS (data-active). Con movimiento reducido no se anima nada.
 */
export default function HowItWorks() {
  const [active, setActive] = useState(0);
  const track = useRef<HTMLElement>(null);

  useEffect(() => {
    // Se calcula en cada scroll (una vez por fotograma), así funciona también si saltas.
    let frame = 0;
    function update() {
      frame = 0;
      const el = track.current;
      if (!el) return;
      const { top, height } = el.getBoundingClientRect();
      const run = height - window.innerHeight;
      const progress = Math.min(0.999, Math.max(0, -top / run));
      setActive(Math.floor(progress * STEPS.length));
    }
    function onScroll() {
      if (!frame) frame = requestAnimationFrame(update);
    }
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <section id="como-funciona" ref={track} className={s.track} aria-labelledby="how-title">
      <div className={s.screen}>
        <div className={s.top}>
          <h2 id="how-title" className={s.heading}>
            así funciona
          </h2>
          <div className={s.progress} aria-hidden="true">
            {STEPS.map((step, i) => (
              <span key={step.title} data-active={i === active} />
            ))}
          </div>
        </div>

        <div className={s.stage} aria-hidden="true">
          {STEPS.map((step, i) => (
            <div key={step.title} className={s.scene} data-active={i === active}>
              {step.scene}
            </div>
          ))}
        </div>

        <ol className={s.captions}>
          {STEPS.map((step, i) => (
            <li key={step.title} className={s.caption} data-active={i === active}>
              <h3 className={s.captionTitle}>{step.title}</h3>
              <p className={s.captionText}>{step.text}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

// --- Escenas: solo HTML y CSS. Cada pieza animada lleva su orden en --i. -----------------

/** El orden de aparición de una pieza: el CSS lo usa para escalonar los retrasos. */
function order(i: number): CSSProperties {
  return { "--i": i } as CSSProperties;
}

/** El enlace detrás de una celosía: una luz lo recorre y luego se abre del todo. */
function ShareScene() {
  return (
    <div className={s.share}>
      <div className={s.linkWindow}>
        <span className={s.link}>psst.hidan.es/g/k3f9</span>
        <span className={s.light} />
      </div>
      <p className={s.message}>
        «Te apunto al amigo invisible <b>familia</b>. Entra con tu nombre y un PIN»
      </p>
    </div>
  );
}

function JoinScene() {
  const people = ["Ana", "Luis", "Marta", "Pablo", "Lucía", "Mario"];
  return (
    <div className={s.join}>
      <div className={s.people}>
        {people.map((name, i) => (
          <span key={name} className={s.person} style={order(i)}>
            <span className={s.star}>{name[0]}</span>
            {name}
          </span>
        ))}
      </div>
      <div className={s.pin}>
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={s.pinBox} style={order(i)} />
        ))}
      </div>
    </div>
  );
}

function RevealScene() {
  return (
    <div className={s.reveal}>
      <span className={s.label}>te toca regalar a</span>
      <div className={s.window}>
        <span className={s.revealName}>Mario</span>
        <span className={`${ui.lattice} ${s.leaf} ${s.left}`} />
        <span className={`${ui.lattice} ${s.leaf} ${s.right}`} />
      </div>
    </div>
  );
}

/** El chat como lo ve quien recibe: quien le escribe es solo una celosía. */
function ChatScene() {
  const lines: { text: string; mine: boolean }[] = [
    { text: "¿Qué talla de camiseta usas?", mine: false },
    { text: "Una M. ¿Quién eres?", mine: true },
    { text: "Eso no te lo puedo decir", mine: false },
  ];
  return (
    <div className={s.chat}>
      <div className={s.chatHead}>
        <span className={s.avatarFrame}>
          <span className={`${ui.lattice} ${s.avatar}`} />
        </span>
        <span>
          quien te regala
          <small className={s.chatSub}>así lo ve Mario</small>
        </span>
      </div>
      {lines.map((line, i) => (
        <p
          key={line.text}
          className={`${s.bubble} ${line.mine ? s.mine : s.theirs} ${s.pop}`}
          style={order(i)}
        >
          {line.text}
        </p>
      ))}
      <span className={`${s.typing} ${s.pop}`} style={order(lines.length)}>
        <span />
        <span />
        <span />
      </span>
    </div>
  );
}

function UnmaskScene() {
  const rows = [
    ["Ana", "Luis"],
    ["Luis", "Marta"],
    ["Marta", "Ana"],
  ];
  return (
    <div className={s.unmask}>
      <span className={s.label}>quién regalaba a quién</span>
      <ul className={s.results}>
        {rows.map(([giver, receiver], i) => (
          <li key={giver}>
            <span className={s.resultGiver} style={order(i)}>
              {giver}
              <span className={`${ui.lattice} ${s.cover}`} />
            </span>
            <span className={s.giftTo}>regalaba a</span>
            <span>{receiver}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
