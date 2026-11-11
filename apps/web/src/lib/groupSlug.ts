/**
 * Saca el código de un grupo de lo que pegue la persona: el enlace entero
 * (https://psst.hidan.es/g/abcdefghjk, con o sin /chat detrás) o solo el código.
 * Devuelve null si no se parece a un código (10 letras o cifras, ver SLUG_LENGTH en la API).
 */
export function slugFromInput(input: string): string | null {
  const text = input.trim().toLowerCase();
  const fromLink = text.match(/\/g\/([a-z0-9]+)/);
  const candidate = fromLink ? fromLink[1] : text;
  return /^[a-z0-9]{10}$/.test(candidate) ? candidate : null;
}
