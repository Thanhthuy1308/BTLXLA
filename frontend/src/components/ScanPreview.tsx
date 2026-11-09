import { useEffect, useRef } from "react";
import { Box } from "@mui/material";
import { prefersReducedMotion } from "../lib/motion";
import { radius } from "../lib/theme";

const SWEEP_MS = 2200;
const PAUSE_MS = 350;
const FPS = 30;

/** Offscreen copy of `source` drawn at `width × height`, optionally through a CSS filter. */
function layer(source: CanvasImageSource, width: number, height: number, filter = "none", smoothing = true) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d")!;
  context.filter = filter;
  context.imageSmoothingEnabled = smoothing;
  context.drawImage(source, 0, 0, width, height);
  return canvas;
}

/**
 * Waiting animation on the user's own image: a scan line sweeps across it in a
 * loop, pixels behind the line are shown lifted (brighter, more contrast), and a
 * band of flickering mosaic blocks marks the area "being processed". It only
 * suggests the work in progress — the real result comes from the server.
 *
 * Performance: canvas filters cost ~8 ms per frame at this size (measured), so the
 * brightened image and the brightened mosaic are rendered once into offscreen
 * layers; each frame only copies clipped regions. Capped at 30 fps and 1.5× DPR.
 */
export default function ScanPreview({ src }: { src: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !src) return undefined;
    let frame = 0;
    let cancelled = false;
    const image = new Image();
    image.onload = () => {
      if (cancelled) return;
      const context = canvas.getContext("2d")!;
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const width = Math.round(canvas.clientWidth * dpr);
      const height = Math.round(width * image.naturalHeight / image.naturalWidth);
      canvas.width = width;
      canvas.height = height;
      const columns = Math.max(24, Math.round(canvas.clientWidth / 10));
      const block = width / columns;
      const rows = Math.max(1, Math.round(columns * height / width));

      const base = layer(image, width, height);
      const lifted = layer(image, width, height, "brightness(1.45) contrast(1.15)");
      const tiny = layer(image, columns, rows);
      const mosaic = layer(layer(tiny, columns, rows, "brightness(1.3)"), width, height, "none", false);

      const draw = (sweep: number, now: number) => {
        context.drawImage(base, 0, 0);
        const band = Math.max(block * 5, width * .12);
        const scan = sweep * (width + band);
        const done = Math.min(width, Math.max(0, scan - band));
        if (done > 0) context.drawImage(lifted, 0, 0, done, height, 0, 0, done, height);
        if (sweep > 0 && sweep < 1) {
          const left = Math.max(0, scan - band);
          const right = Math.min(width, scan);
          if (right > left) context.drawImage(mosaic, left, 0, right - left, height, left, 0, right - left, height);
          const seed = Math.floor(now / 80);
          for (let index = 0; index < 18; index += 1) {
            const a = Math.abs(Math.sin((seed + index) * 12.9898) * 43758.5453) % 1;
            const b = Math.abs(Math.sin((seed - index) * 4.1414) * 24634.6345) % 1;
            context.fillStyle = index % 3 === 0 ? "rgba(255,255,255,.5)" : "rgba(11,87,208,.45)";
            context.fillRect(left + Math.floor(a * ((right - left) / block)) * block, Math.floor(b * (height / block)) * block, block, block);
          }
          context.fillStyle = "#8ab4f8";
          context.fillRect(Math.min(scan, width) - 2, 0, 3, height);
        }
      };

      if (prefersReducedMotion()) { draw(.55, 0); return; }
      const start = performance.now();
      let last = 0;
      const tick = (now: number) => {
        if (cancelled) return;
        frame = requestAnimationFrame(tick);
        if (now - last < 1000 / FPS) return;
        last = now;
        const t = (now - start) % (SWEEP_MS + PAUSE_MS);
        draw(Math.min(1, t / SWEEP_MS), now);
      };
      frame = requestAnimationFrame(tick);
    };
    image.src = src;
    return () => { cancelled = true; cancelAnimationFrame(frame); };
  }, [src]);

  return <Box component="canvas" ref={canvasRef} aria-hidden="true" sx={{ width: "100%", display: "block", borderRadius: radius.media, bgcolor: "#0f1115" }} />;
}
