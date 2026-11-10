import type { GroupPublic } from "../../lib/api/client";
import { groupDetails } from "../../lib/format";
import ui from "../../styles/ui.module.css";
import g from "./group.module.css";

/**
 * Cabecera del grupo: el nombre sobre fondo sombra con una celosía que se desvanece a la derecha,
 * y debajo el presupuesto y la fecha. En la pantalla de unirse lleva "te invitan a".
 */
export default function GroupHeader({ group, invite = false }: { group: GroupPublic; invite?: boolean }) {
  const details = groupDetails(group);

  return (
    <header className={g.header}>
      <div className={`${ui.lattice} ${g.headerLattice}`} aria-hidden="true" />
      <h1 className={g.groupName}>
        {invite && <span className={g.invite}>te invitan a </span>}
        <em>{group.name}</em>
      </h1>
      {details.length > 0 && (
        <ul className={g.facts}>
          {details.map((detail) => (
            <li key={detail}>{detail}</li>
          ))}
        </ul>
      )}
    </header>
  );
}
