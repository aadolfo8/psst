import { useEffect, useState } from "react";
import { useRevalidator } from "react-router";

import { api, type Me, type ParticipantPublic } from "../../lib/api/client";
import g from "./group.module.css";

/**
 * Barra del modo demo: dice como quién estás viendo la app y deja cambiar de persona sin PIN.
 * Así se ve el chat desde los dos lados: Lucía sabe que le regala a Mario; Mario solo ve a
 * "su amigo invisible". Solo aparece en grupos demo (la API no deja cambiar en los demás).
 */
export default function DemoBar({ me }: { me: Me }) {
  const { revalidate } = useRevalidator();
  const [people, setPeople] = useState<ParticipantPublic[]>([]);
  const [switching, setSwitching] = useState(false);
  const slug = me.group.slug;

  useEffect(() => {
    api
      .GET("/groups/{slug}/participants", { params: { path: { slug } } })
      .then(({ data }) => setPeople(data ?? []));
  }, [slug]);

  async function switchTo(name: string) {
    setSwitching(true);
    await api.POST("/groups/{slug}/demo/switch", { params: { path: { slug } }, body: { name } });
    // Con la cookie nueva, los loaders devuelven lo que ve esa persona.
    await revalidate();
    setSwitching(false);
  }

  return (
    <aside className={g.demo} aria-label="modo demo">
      <span className={g.demoLabel}>demo</span>
      <span className={g.demoText}>
        estás viendo la app como <strong>{me.name}</strong>. cambia de persona:
      </span>
      <div className={g.demoPeople}>
        {people
          .filter((p) => p.id !== me.id)
          .map((p) => (
            <button
              key={p.id}
              type="button"
              className={g.demoPerson}
              disabled={switching}
              onClick={() => switchTo(p.name)}
            >
              {p.name}
            </button>
          ))}
      </div>
    </aside>
  );
}
