import { useState } from "react";

import ui from "../styles/ui.module.css";
import styles from "./DateField.module.css";

/** Fechas típicas de un amigo invisible: [mes (0 = enero), día, nombre]. */
const OCCASIONS: [number, number, string][] = [
  [11, 24, "nochebuena"],
  [11, 25, "navidad"],
  [11, 31, "nochevieja"],
  [0, 6, "reyes"],
];

const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"];

const monthYear = new Intl.DateTimeFormat("es-ES", { month: "long", year: "numeric" });
const shortDate = new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short" });
const longDate = new Intl.DateTimeFormat("es-ES", {
  weekday: "long",
  day: "numeric",
  month: "long",
});

/** "AAAA-MM-DD" en hora local (el formato que espera la API). */
function toIso(date: Date): string {
  return date.toLocaleDateString("sv-SE");
}

function fromIso(iso: string): Date {
  return new Date(`${iso}T00:00`); // con T00:00 se interpreta en hora local, no en UTC
}

function startOfToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

/** La próxima vez que cae cada fecha típica, de la más cercana a la más lejana. */
function upcomingOccasions(today: Date) {
  return OCCASIONS.map(([month, day, label]) => {
    let date = new Date(today.getFullYear(), month, day);
    if (date < today) date = new Date(today.getFullYear() + 1, month, day);
    return { iso: toIso(date), date, label };
  }).sort((a, b) => a.date.getTime() - b.date.getTime());
}

/**
 * Fecha del intercambio: accesos directos a las fechas típicas y, si no es ninguna, un
 * calendario propio. El valor viaja en un input oculto con `name` para leerlo con FormData.
 */
export function DateField({ name }: { name: string }) {
  const today = startOfToday();
  const occasions = upcomingOccasions(today);

  const [value, setValue] = useState<string | null>(null);
  const [calendarOpen, setCalendarOpen] = useState(false);

  const isOccasion = occasions.some((o) => o.iso === value);

  function pickOccasion(iso: string) {
    setValue(value === iso ? null : iso); // pulsar otra vez la quita
    setCalendarOpen(false);
  }

  return (
    <fieldset className={styles.field}>
      <legend className={styles.legend}>fecha del intercambio</legend>
      <input type="hidden" name={name} value={value ?? ""} />

      <div className={styles.chips}>
        {occasions.map((o) => (
          <button
            key={o.iso}
            type="button"
            className={styles.chip}
            aria-pressed={value === o.iso}
            onClick={() => pickOccasion(o.iso)}
          >
            <span className={styles.chipDate}>{shortDate.format(o.date)}</span>
            <span className={styles.chipLabel}>{o.label}</span>
          </button>
        ))}
        <button
          type="button"
          className={`${styles.chip} ${styles.other}`}
          aria-pressed={value !== null && !isOccasion}
          aria-expanded={calendarOpen}
          onClick={() => setCalendarOpen(!calendarOpen)}
        >
          <CalendarIcon />
          {value !== null && !isOccasion ? shortDate.format(fromIso(value)) : "elegir otro día"}
        </button>
      </div>

      {calendarOpen && (
        <Calendar
          today={today}
          selected={value}
          onSelect={(iso) => {
            setValue(iso);
            setCalendarOpen(false);
          }}
        />
      )}

      <p className={ui.hint}>
        {value ? (
          <>
            {longDate.format(fromIso(value))}.{" "}
            <button type="button" className={ui.linkButton} onClick={() => setValue(null)}>
              quitar fecha
            </button>
          </>
        ) : (
          "Opcional. Podéis decidirla más adelante."
        )}
      </p>
    </fieldset>
  );
}

function Calendar({
  today,
  selected,
  onSelect,
}: {
  today: Date;
  selected: string | null;
  onSelect: (iso: string) => void;
}) {
  // Mes que se está viendo: el de la fecha elegida o, si no hay, el actual.
  const [month, setMonth] = useState(() => {
    const base = selected ? fromIso(selected) : today;
    return new Date(base.getFullYear(), base.getMonth(), 1);
  });

  const year = month.getFullYear();
  const monthIndex = month.getMonth();
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  // Huecos antes del día 1 para que la semana empiece en lunes (getDay: 0 = domingo).
  const leadingBlanks = (month.getDay() + 6) % 7;
  const isCurrentMonth = year === today.getFullYear() && monthIndex === today.getMonth();

  function moveMonth(delta: number) {
    setMonth(new Date(year, monthIndex + delta, 1));
  }

  return (
    <div className={styles.calendar}>
      <div className={styles.calendarHead}>
        <button
          type="button"
          className={styles.navButton}
          onClick={() => moveMonth(-1)}
          disabled={isCurrentMonth}
          aria-label="mes anterior"
        >
          <Chevron direction="left" />
        </button>
        <span className={styles.monthName} aria-live="polite">
          {monthYear.format(month)}
        </span>
        <button
          type="button"
          className={styles.navButton}
          onClick={() => moveMonth(1)}
          aria-label="mes siguiente"
        >
          <Chevron direction="right" />
        </button>
      </div>

      <div className={styles.grid}>
        {WEEKDAYS.map((day) => (
          <span key={day} className={styles.weekday} aria-hidden="true">
            {day}
          </span>
        ))}
        {Array.from({ length: leadingBlanks }, (_, i) => (
          <span key={`blank-${i}`} />
        ))}
        {Array.from({ length: daysInMonth }, (_, i) => {
          const date = new Date(year, monthIndex, i + 1);
          const iso = toIso(date);
          return (
            <button
              key={iso}
              type="button"
              className={styles.day}
              data-today={iso === toIso(today) || undefined}
              aria-pressed={iso === selected}
              aria-label={longDate.format(date)}
              disabled={date < today}
              onClick={() => onSelect(iso)}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function CalendarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <rect x="2" y="3.5" width="14" height="12" rx="3" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M2 7.5h14M6 2v3M12 2v3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function Chevron({ direction }: { direction: "left" | "right" }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <path
        d={direction === "left" ? "M10 3L5 8l5 5" : "M6 3l5 5-5 5"}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
