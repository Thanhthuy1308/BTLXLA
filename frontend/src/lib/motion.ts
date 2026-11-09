import { useEffect, useState } from "react";

/** True when the visitor asked the OS to minimise animation. */
export function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

const easeOutCubic = (t: number) => 1 - (1 - t) ** 3;

/**
 * Animate a number from `from` to `to` (ease-out) and return the current value.
 * Restarts whenever either end changes; jumps straight to `to` with reduced motion.
 */
export function useCountUp(from: number, to: number, duration = 700, delay = 150) {
  const [value, setValue] = useState(prefersReducedMotion() ? to : from);
  useEffect(() => {
    if (prefersReducedMotion() || from === to) { setValue(to); return undefined; }
    let frame = 0;
    setValue(from);
    const start = performance.now() + delay;
    const tick = (now: number) => {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      setValue(from + (to - from) * easeOutCubic(t));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [from, to, duration, delay]);
  return value;
}
