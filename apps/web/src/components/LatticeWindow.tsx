import { useEffect, useRef } from "react";

import styles from "./LatticeWindow.module.css";

const IDLE_MS = 1800; // tras este tiempo sin mover el dedo, la luz vuelve a pasear sola
const HIDDEN = "-999px"; // la luz fuera de la ventana: no se lee nada

type Props = {
  hiddenName: string;
  /**
   * Si la luz pasea sola cuando nadie la mueve. En el inicio sí, para que se vea qué hay
   * detrás. En el revelado no: el nombre solo se lee donde está tu dedo, y al soltarlo se
   * vuelve a tapar, para que nadie que mire de reojo lo vea.
   */
  wander?: boolean;
  className?: string;
};

/**
 * Una ventana con celosía: detrás hay un nombre que solo se lee donde da la luz.
 * La luz sigue al dedo o al ratón. La posición se guarda en dos variables CSS (--x, --y)
 * que usa la máscara.
 */
export function LatticeWindow({ hiddenName, wander = true, className }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let lastPointer = 0;
    let frame = 0;

    function setSpot(x: string, y: string) {
      el!.style.setProperty("--x", x);
      el!.style.setProperty("--y", y);
    }

    function onPointerMove(event: PointerEvent) {
      const box = el!.getBoundingClientRect();
      lastPointer = performance.now();
      setSpot(`${event.clientX - box.left}px`, `${event.clientY - box.top}px`);
    }

    function hide() {
      setSpot(HIDDEN, HIDDEN);
    }

    function walk(time: number) {
      if (performance.now() - lastPointer > IDLE_MS) {
        const { width, height } = el!.getBoundingClientRect();
        const x = width / 2 + Math.sin(time / 1300) * Math.min(width * 0.3, 260);
        const y = height / 2 + Math.sin(time / 700) * height * 0.08;
        setSpot(`${x}px`, `${y}px`);
      }
      frame = requestAnimationFrame(walk);
    }

    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerdown", onPointerMove);

    if (wander) {
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduceMotion) setSpot("50%", "50%");
      else frame = requestAnimationFrame(walk);
    } else {
      // Sin paseo, la luz solo existe mientras hay un dedo o un ratón encima.
      hide();
      for (const type of ["pointerleave", "pointerup", "pointercancel"]) {
        el.addEventListener(type, hide);
      }
    }

    return () => {
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerdown", onPointerMove);
      for (const type of ["pointerleave", "pointerup", "pointercancel"]) {
        el.removeEventListener(type, hide);
      }
      cancelAnimationFrame(frame);
    };
  }, [wander]);

  return (
    <div
      ref={ref}
      className={[styles.window, className].filter(Boolean).join(" ")}
      aria-hidden="true"
    >
      <span className={styles.name}>{hiddenName}</span>
      <div className={styles.lattice} />
      <span className={styles.hint}>pasa el dedo</span>
    </div>
  );
}
