import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { Box, Typography } from "@mui/material";
import { prefersReducedMotion } from "../lib/motion";
import { radius } from "../lib/theme";

/** Keyframes (time in ms, handle position in %) of the one-off "you can drag this" hint. */
const HINT = [[0, 50], [550, 68], [1250, 32], [1750, 50]] as const;
const easeInOut = (t: number) => (t < .5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

/**
 * Before/after comparison: the "before" image is clipped to the left of a handle the
 * user drags. A native range input covers the frame, so mouse, touch and keyboard
 * (arrow keys) all work and screen readers announce the split position.
 * When a new pair loads, the handle sweeps once to show that it can be dragged;
 * any interaction (or reduced motion) cancels that hint.
 */
export default function CompareSlider({ before, after, beforeLabel = "Trước", afterLabel = "Sau" }: {
  before: string; after: string; beforeLabel?: string; afterLabel?: string;
}) {
  const [position, setPosition] = useState(50);
  const touched = useRef(false);

  useEffect(() => {
    touched.current = false;
    setPosition(50);
    if (prefersReducedMotion()) return undefined;
    let frame = 0;
    const start = performance.now() + 700;
    const tick = (now: number) => {
      if (touched.current) return;
      const elapsed = now - start;
      if (elapsed >= 0) {
        const index = HINT.findIndex(([time]) => time > elapsed);
        if (index === -1) { setPosition(50); return; }
        const [t0, p0] = HINT[index - 1] ?? HINT[0];
        const [t1, p1] = HINT[index];
        setPosition(p0 + (p1 - p0) * easeInOut((elapsed - t0) / (t1 - t0)));
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [before, after]);

  const stopHint = () => { touched.current = true; };
  const chip = { position: "absolute", top: 10, px: 1, py: .25, borderRadius: radius.pill, bgcolor: "rgba(0,0,0,.62)", color: "#fff", fontSize: 12, fontWeight: 700, pointerEvents: "none" } as const;
  return <Box sx={{ position: "relative", borderRadius: radius.media, overflow: "hidden", bgcolor: "#0f1115", userSelect: "none", touchAction: "pan-y" }}>
    <Box component="img" src={after} alt={`${afterLabel} xử lý`} draggable={false} sx={{ display: "block", width: "100%", height: "auto" }} />
    <Box component="img" src={before} alt={beforeLabel} draggable={false} sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", clipPath: `inset(0 ${100 - position}% 0 0)` }} />
    <Box aria-hidden="true" sx={{ position: "absolute", top: 0, bottom: 0, left: `${position}%`, width: 2, ml: "-1px", bgcolor: "#fff", pointerEvents: "none" }}>
      <Box sx={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: 36, height: 36, borderRadius: "50%", bgcolor: "#fff", color: "#0b57d0", display: "grid", placeItems: "center", fontSize: 15, fontWeight: 700, letterSpacing: "-.1em" }}>‹ ›</Box>
    </Box>
    <Typography sx={{ ...chip, left: 10 }}>{beforeLabel}</Typography>
    <Typography sx={{ ...chip, right: 10 }}>{afterLabel}</Typography>
    <Box component="input" type="range" min={0} max={100} step={0.5} value={position}
      onPointerDown={stopHint} onKeyDown={stopHint} onFocus={stopHint}
      onChange={(event: ChangeEvent<HTMLInputElement>) => { stopHint(); setPosition(Number(event.target.value)); }}
      aria-label="Kéo để so sánh ảnh trước và sau xử lý" aria-valuetext={`${Math.round(position)}% ảnh gốc`}
      sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", m: 0, opacity: 0, cursor: "ew-resize",
        "&:focus-visible + .focus-ring": { opacity: 1 } }} />
    <Box className="focus-ring" aria-hidden="true" sx={{ position: "absolute", inset: 0, border: "3px solid #8ab4f8", borderRadius: radius.media, opacity: 0, pointerEvents: "none" }} />
  </Box>;
}
