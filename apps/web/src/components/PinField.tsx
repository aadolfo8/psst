import { useState, type SyntheticEvent } from "react";

import ui from "../styles/ui.module.css";
import styles from "./PinField.module.css";

const LENGTH = 4;

/**
 * PIN de 4 cifras pintado como cuatro casillas. Por debajo es un solo input invisible que
 * las cubre: se escribe (o se pega) de corrido y el borrado funciona como en cualquier campo.
 * Usa `name="pin"` para leerlo con FormData.
 */
export function PinField({ label = "PIN de 4 cifras" }: { label?: string }) {
  const [value, setValue] = useState("");

  // El cursor siempre al final: así nunca se edita una cifra del medio sin verlo.
  function keepCaretAtEnd(event: SyntheticEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    input.setSelectionRange(input.value.length, input.value.length);
  }

  return (
    <label className={ui.field}>
      {label}
      <span className={styles.pin}>
        {Array.from({ length: LENGTH }, (_, i) => (
          <span
            key={i}
            className={styles.box}
            data-filled={i < value.length || undefined}
            data-active={i === Math.min(value.length, LENGTH - 1) || undefined}
            aria-hidden="true"
          />
        ))}
        <input
          className={styles.input}
          name="pin"
          value={value}
          onChange={(e) => setValue(e.target.value.replace(/\D/g, "").slice(0, LENGTH))}
          onSelect={keepCaretAtEnd}
          inputMode="numeric"
          pattern="[0-9]{4}"
          minLength={LENGTH}
          maxLength={LENGTH}
          required
          autoComplete="off"
          title="4 cifras"
        />
      </span>
    </label>
  );
}
