import ui from "../styles/ui.module.css";

/** Campo de PIN de 4 cifras. Usa `name="pin"` para leerlo con FormData. */
export function PinField({ label = "PIN de 4 cifras" }: { label?: string }) {
  return (
    <label className={ui.field}>
      {label}
      <input
        className={`${ui.input} ${ui.pin}`}
        name="pin"
        type="password"
        inputMode="numeric"
        pattern="[0-9]{4}"
        minLength={4}
        maxLength={4}
        required
        autoComplete="off"
        title="4 cifras"
      />
    </label>
  );
}
