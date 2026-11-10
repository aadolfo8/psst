import type { GroupPublic } from "./api/client";

const dateFormat = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "long" });

/** "30 € por persona", "intercambio el 24 de diciembre"… en líneas separadas. */
export function groupDetails(group: GroupPublic): string[] {
  const details: string[] = [];
  if (group.budget) details.push(`${group.budget} € por persona`);
  if (group.exchange_date) {
    // "2026-12-24" se interpreta como UTC; con T00:00 se usa la fecha local.
    const date = new Date(`${group.exchange_date}T00:00`);
    details.push(`intercambio el ${dateFormat.format(date)}`);
  }
  return details;
}

export function inviteUrl(slug: string): string {
  return `${window.location.origin}/g/${slug}`;
}
