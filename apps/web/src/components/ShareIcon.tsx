import s from "./ShareIcon.module.css";

/** El icono de "compartir" de iOS (cuadrado con flecha hacia arriba), para las instrucciones. */
export default function ShareIcon() {
  return (
    <svg
      className={s.icon}
      width="16"
      height="18"
      viewBox="0 0 16 18"
      aria-label="icono de compartir"
      role="img"
    >
      <path
        d="M8 1v11M4.5 4.5L8 1l3.5 3.5M3 8H1.5v9h13V8H13"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
