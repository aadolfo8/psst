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
    text: "Sin cuentas, sin email y sin teléfono. Cada persona escribe su lista de deseos para darte pistas.",
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
 * "Así funciona": una ventana fija que cambia de escena según bajas. El paso activo se
 * calcula con el scroll y su escena se anima solo con CSS (data-active). Con movimiento
 * reducido no se anima nada.
 */
export default function HowItWorks() {
  const [active, setActive] = useState(0);
  const steps = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    // El paso activo es el último cuyo borde de arriba ya ha pasado una línea de la pantalla.
    // En escritorio la línea va al 40 %; en el móvil, al 65 %, justo debajo de la ventana fija.
    // Se calcula en cada scroll (una vez por fotograma), así funciona también si saltas.
    let frame = 0;
    function update() {
      frame = 0;
      const wide = window.matchMedia("(min-width: 860px)").matches;
      const line = window.innerHeight * (wide ? 0.4 : 0.65);
      let current = 0;
      steps.current.forEach((step, i) => {
        if (step && step.getBoundingClientRect().top < line) current = i;
      });
      setActive(current);
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
    <section id="como-funciona" className={s.story} aria-labelledby="how-title">
      <h2 id="how-title" className={s.heading}>
        así funciona
      </h2>
      <div className={s.layout}>
        <div className={s.stage} aria-hidden="true">
          {STEPS.map((step, i) => (
            <div key={step.title} className={s.scene} data-active={i === active}>
              {step.scene}
            </div>
          ))}
          <div className={s.progress}>
            {STEPS.map((step, i) => (
              <span key={step.title} data-active={i === active} />
            ))}
          </div>
        </div>

        <ol className={s.steps}>
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              ref={(el) => {
                steps.current[i] = el;
              }}
              data-step={i}
              data-active={i === active}
              className={s.step}
            >
              <span className={s.number}>{i + 1}</span>
              <h3 className={s.stepTitle}>{step.title}</h3>
              <p className={s.stepText}>{step.text}</p>
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

function ShareScene() {
  const words = 'Te apunto al amigo invisible "Familia". Entra con tu nombre y un PIN:'.split(" ");
  return (
    <div className={s.phone}>
      <span className={s.chatName}>familia</span>
      <p className={`${s.bubble} ${s.mine}`}>
        {words.map((word, i) => (
          <span key={i} className={s.word} style={order(i)}>
            {word}{" "}
          </span>
        ))}
        <span
          className={`${s.word} ${s.link}`}
          style={order(words.length)}
        >
          psst.hidan.es/g/k3f9
        </span>
      </p>
      <span className={s.sent} style={order(words.length + 2)}>
        enviado
      </span>
    </div>
  );
}

function JoinScene() {
  const people = ["Ana", "Luis", "Marta", "Pablo", "Lucía", "Mario"];
  return (
    <div className={s.phone}>
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
    <div className={s.phone}>
      <span className={s.revealLabel}>te toca regalar a</span>
      <div className={s.window}>
        <span className={s.revealName}>Mario</span>
        <span className={`${ui.lattice} ${s.leaf} ${s.left}`} />
        <span className={`${ui.lattice} ${s.leaf} ${s.right}`} />
      </div>
    </div>
  );
}

function ChatScene() {
  const lines: { text: string; mine: boolean }[] = [
    { text: "¿Qué talla de camiseta usas?", mine: true },
    { text: "Una M. ¿Quién eres?", mine: false },
    { text: "Eso no te lo puedo decir", mine: true },
  ];
  return (
    <div className={s.phone}>
      <div className={s.chatHead}>
        <span className={`${ui.lattice} ${s.avatar}`} />
        <span>quien te regala</span>
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
      <span className={s.typing} style={order(lines.length)}>
        escribiendo…
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
    <div className={s.phone}>
      <span className={s.revealLabel}>quién regalaba a quién</span>
      <ul className={s.results}>
        {rows.map(([giver, receiver], i) => (
          <li key={giver} style={order(i)}>
            <span className={s.resultGiver}>
              {giver}
              <span className={`${ui.lattice} ${s.cover}`} />
            </span>
            <span className={s.arrow}>regalaba a</span>
            <span>{receiver}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
