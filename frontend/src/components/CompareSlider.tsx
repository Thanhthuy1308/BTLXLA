import { useState } from "react";
import type { ChangeEvent } from "react";
import { Box, Typography } from "@mui/material";

/**
 * Before/after comparison: the "before" image is clipped to the left of a handle the
 * user drags. A native range input covers the frame, so mouse, touch and keyboard
 * (arrow keys) all work and screen readers announce the split position.
 */
export default function CompareSlider({ before, after, beforeLabel = "Trước", afterLabel = "Sau" }: {
  before: string; after: string; beforeLabel?: string; afterLabel?: string;
}) {
  const [position, setPosition] = useState(50);
  const chip = { position: "absolute", top: 10, px: 1, py: .25, borderRadius: 1, bgcolor: "rgba(0,0,0,.62)", color: "#fff", fontSize: 12, fontWeight: 700, pointerEvents: "none" } as const;
  return <Box sx={{ position: "relative", borderRadius: 1.5, overflow: "hidden", bgcolor: "#0f1115", userSelect: "none", touchAction: "pan-y" }}>
    <Box component="img" src={after} alt={`${afterLabel} xử lý`} draggable={false} sx={{ display: "block", width: "100%", height: "auto" }} />
    <Box component="img" src={before} alt={beforeLabel} draggable={false} sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", clipPath: `inset(0 ${100 - position}% 0 0)` }} />
    <Box aria-hidden="true" sx={{ position: "absolute", top: 0, bottom: 0, left: `${position}%`, width: 2, ml: "-1px", bgcolor: "#fff", pointerEvents: "none" }}>
      <Box sx={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: 36, height: 36, borderRadius: "50%", bgcolor: "#fff", color: "#0b57d0", display: "grid", placeItems: "center", fontSize: 15, fontWeight: 700, letterSpacing: "-.1em" }}>‹ ›</Box>
    </Box>
    <Typography sx={{ ...chip, left: 10 }}>{beforeLabel}</Typography>
    <Typography sx={{ ...chip, right: 10 }}>{afterLabel}</Typography>
    <Box component="input" type="range" min={0} max={100} step={0.5} value={position}
      onChange={(event: ChangeEvent<HTMLInputElement>) => setPosition(Number(event.target.value))}
      aria-label="Kéo để so sánh ảnh trước và sau xử lý" aria-valuetext={`${Math.round(position)}% ảnh gốc`}
      sx={{ position: "absolute", inset: 0, width: "100%", height: "100%", m: 0, opacity: 0, cursor: "ew-resize",
        "&:focus-visible + .focus-ring": { opacity: 1 } }} />
    <Box className="focus-ring" aria-hidden="true" sx={{ position: "absolute", inset: 0, border: "3px solid #8ab4f8", borderRadius: 1.5, opacity: 0, pointerEvents: "none" }} />
  </Box>;
}
