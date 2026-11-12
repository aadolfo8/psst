import { useEffect, useState, type FormEvent } from "react";
import { Link, useLoaderData, useNavigate } from "react-router";

import { DateField } from "../components/DateField";
import InstallPrompt from "../components/InstallPrompt";
import { LatticeWindow } from "../components/LatticeWindow";
import { PinField } from "../components/PinField";
import { api, errorMessage, type GroupPublic } from "../lib/api/client";
import { slugFromInput } from "../lib/groupSlug";
import { isInstalled } from "../lib/platform";
import ui from "../styles/ui.module.css";
import styles from "./Home.module.css";
import HowItWorks from "./HowItWorks";
import type { homeLoader } from "./loaders";

const STATUS_LABEL: Record<GroupPublic["status"], string> = {
  open: "apuntándose",
  closed: "inscripciones cerradas",
  drawn: "sorteo hecho",
};

export default function Home() {
  const { groups } = useLoaderData<typeof homeLoader>();

  return (
    <div className={styles.home}>
      <header className={styles.bar}>
        <span className={ui.logo}>psst</span>
        <Link to="/demo" className={styles.demoLink}>
          probar la demo
        </Link>
      </header>
      <LatticeWindow hiddenName="Lucía" />
      <main className={styles.content}>
        <div className={styles.intro}>
          <h1 className={styles.title}>
            pregúntale lo que quieras. <em>sin que sepa que eres tú.</em>
          </h1>
          <p className={ui.lead}>
            El amigo invisible por enlace, con un chat secreto entre quien regala y quien recibe.
            Sin cuentas: un nombre y un PIN.
          </p>
          <a href="#como-funciona" className={styles.howLink}>
            ver cómo funciona
          </a>
          <InstallPrompt />
          {groups.length > 0 && <MyGroups groups={groups} />}
          {/* La app instalada no comparte sesión con el navegador en iPhone: ahí no hay grupos
              que mostrar y la forma de volver es con el enlace. */}
          {groups.length === 0 && isInstalled && <OpenGroupForm />}
        </div>
        <CreateGroupForm />
      </main>
      <HowItWorks />
      <section id="empezar" className={styles.finale}>
        <h2 className={styles.title}>
          ¿empezamos? <em>tarda un minuto.</em>
        </h2>
        <div className={styles.finaleActions}>
          <button type="button" className={ui.button} onClick={goToForm}>
            crear tu grupo
          </button>
          <Link to="/demo" className={ui.ghost}>
            probar la demo
          </Link>
        </div>
      </section>
      <FloatingCreate />
      <div className={styles.footer}>
        <InstallPrompt footer="after-dismiss" />
      </div>
    </div>
  );
}

/** Sube al formulario de crear grupo y pone el cursor en el primer campo. */
function goToForm() {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById("crear")?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth" });
  document.getElementById("group-name")?.focus({ preventScroll: true });
}

/**
 * Botón flotante para crear el grupo: sale cuando ni el formulario ni la llamada del final
 * están a la vista, para que siempre haya a mano por dónde empezar.
 */
function FloatingCreate() {
  const [hidden, setHidden] = useState(true);

  useEffect(() => {
    const targets = ["crear", "empezar"]
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    const visible = new Set<Element>();
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) visible.add(entry.target);
        else visible.delete(entry.target);
      }
      setHidden(visible.size > 0);
    });
    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <button
      type="button"
      className={`${ui.button} ${styles.floating}`}
      data-hidden={hidden}
      tabIndex={hidden ? -1 : 0}
      aria-hidden={hidden}
      onClick={goToForm}
    >
      crea tu grupo
    </button>
  );
}

/** Los grupos en los que ya has entrado desde este navegador (o desde la app instalada). */
function MyGroups({ groups }: { groups: GroupPublic[] }) {
  return (
    <section className={`${ui.block} ${styles.groups}`}>
      <h2 className={ui.subtitle}>tus grupos</h2>
      <ul className={styles.groupList}>
        {groups.map((group) => (
          <li key={group.slug}>
            <Link to={`/g/${group.slug}`} className={styles.groupLink}>
              <span className={styles.groupName}>{group.name}</span>
              <span className={styles.groupStatus}>
                {group.demo ? "demo" : STATUS_LABEL[group.status]}
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Para volver a un grupo cuando no hay sesión guardada: pegas el enlace y entras con tu PIN. */
function OpenGroupForm() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const slug = slugFromInput(String(new FormData(event.currentTarget).get("link")));
    if (slug) navigate(`/g/${slug}`);
    else setError("no parece el enlace de un grupo");
  }

  return (
    <form className={`${ui.block} ${styles.groups}`} onSubmit={handleSubmit}>
      <h2 className={ui.subtitle}>volver a tu grupo</h2>
      <p className={ui.hint}>
        Pega el enlace del grupo que te mandaron. Entras con tu nombre y tu PIN.
      </p>
      <input
        className={ui.input}
        name="link"
        required
        inputMode="url"
        autoCapitalize="none"
        autoCorrect="off"
        placeholder="https://psst.hidan.es/g/…"
        aria-label="enlace del grupo"
        onChange={() => setError(null)}
      />
      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <button className={ui.button}>entrar al grupo</button>
    </form>
  );
}

function CreateGroupForm() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const budget = String(form.get("budget") ?? "");
    const exchangeDate = String(form.get("exchange_date") ?? "");

    setSending(true);
    setError(null);
    const { data, error } = await api.POST("/groups", {
      body: {
        name: String(form.get("name")),
        budget: budget ? Number(budget) : null,
        exchange_date: exchangeDate || null,
        admin_name: String(form.get("admin_name")),
        pin: String(form.get("pin")),
      },
    });
    setSending(false);

    if (data) navigate(`/g/${data.group.slug}/compartir`);
    else setError(errorMessage(error));
  }

  return (
    <form id="crear" className={`${ui.block} ${styles.form}`} onSubmit={handleSubmit}>
      <h2 className={ui.subtitle}>crea tu grupo</h2>

      <label className={ui.field}>
        nombre del grupo
        <input
          id="group-name"
          className={ui.input}
          name="name"
          required
          maxLength={80}
          placeholder="familia, oficina…"
        />
      </label>

      <label className={ui.field}>
        presupuesto por persona (€)
        <input
          className={ui.input}
          name="budget"
          type="number"
          min={1}
          max={1000}
          inputMode="numeric"
          placeholder="opcional"
        />
      </label>

      <DateField name="exchange_date" />

      <label className={ui.field}>
        tu nombre
        <input
          className={ui.input}
          name="admin_name"
          required
          maxLength={40}
          autoComplete="given-name"
        />
      </label>
      <PinField />
      <p className={ui.hint}>
        Tú también participas. Con tu nombre y el PIN podrás volver a entrar desde otro móvil.
      </p>

      {error && (
        <p className={ui.error} role="alert">
          {error}
        </p>
      )}
      <button className={ui.button} disabled={sending}>
        crear el grupo
      </button>
    </form>
  );
}
