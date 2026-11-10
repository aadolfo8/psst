import { useEffect, useRef } from "react";

import styles from "./LatticeWindow.module.css";

const IDLE_MS = 1800; // tras este tiempo sin mover el dedo, la luz vuelve a pasear sola

/**
 * Una ventana con celosía: detrás hay un nombre que solo se lee donde da la luz.
 * La luz sigue al dedo o al ratón; si nadie la mueve, pasea sola de lado a lado.
 * La posición se guarda en dos variables CSS (--x, --y) que usa la máscara.
 */
export function LatticeWindow({ hiddenName }: { hiddenName: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let lastPointer = 0;
    let frame = 0;

    function setSpot(x: number, y: number) {
      el!.style.setProperty("--x", `${x}px`);
      el!.style.setProperty("--y", `${y}px`);
    }

    function onPointerMove(event: PointerEvent) {
      const box = el!.getBoundingClientRect();
      lastPointer = performance.now();
      setSpot(event.clientX - box.left, event.clientY - box.top);
    }

    function wander(time: number) {
      if (performance.now() - lastPointer > IDLE_MS) {
        const { width, height } = el!.getBoundingClientRect();
        const x = width / 2 + Math.sin(time / 1300) * Math.min(width * 0.3, 260);
        const y = height / 2 + Math.sin(time / 700) * height * 0.08;
        setSpot(x, y);
      }
      frame = requestAnimationFrame(wander);
    }

    el.addEventListener("pointermove", onPointerMove);
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) setSpot(el.clientWidth / 2, el.clientHeight / 2);
    else frame = requestAnimationFrame(wander);

    return () => {
      el.removeEventListener("pointermove", onPointerMove);
      cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div ref={ref} className={styles.window} aria-hidden="true">
      <span className={styles.name}>{hiddenName}</span>
      <div className={styles.lattice} />
      <span className={styles.hint}>pasa el dedo</span>
    </div>
  );
}
