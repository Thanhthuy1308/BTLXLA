import { useEffect, useRef } from "react";
import { Box, Stack, Typography } from "@mui/material";

/**
 * Landing-page "converter" animation.
 *
 * A scan line sweeps across a dark sample image. Pixels behind the line show the
 * real enhanced output produced by the Python pipeline; pixels inside the moving
 * band are rendered as flickering mosaic blocks to suggest per-pixel processing;
 * pixels ahead of the line are still the original. Below the image the 256-bin
 * histogram and μ/σ readouts morph in step with the sweep. Every number is computed
 * in the browser from the two displayed images, using the same luminance weights
 * as the server (0.299R + 0.587G + 0.114B), so the animation never shows invented data.
 */

type ImageStats = { mean: number; std: number; hist: Float32Array };

const PRIMARY = "#0b57d0";
// Timeline (ms): hold original → sweep → hold result → cross-fade back.
const HOLD_START = 900;
const SWEEP = 3000;
const HOLD_END = 1900;
const RESET = 700;
const CYCLE = HOLD_START + SWEEP + HOLD_END + RESET;

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Không tải được ${src}`));
    image.src = src;
  });
}

/** Grayscale mean, standard deviation and 256-bin histogram of one image. */
function measure(image: HTMLImageElement): ImageStats {
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d", { willReadFrequently: true })!;
  context.drawImage(image, 0, 0);
  const { data } = context.getImageData(0, 0, canvas.width, canvas.height);
  const hist = new Float32Array(256);
  let sum = 0;
  let sumSquares = 0;
  const count = data.length / 4;
  for (let index = 0; index < data.length; index += 4) {
    const gray = Math.round(0.299 * data[index] + 0.587 * data[index + 1] + 0.114 * data[index + 2]);
    hist[gray] += 1;
    sum += gray;
    sumSquares += gray * gray;
  }
  const mean = sum / count;
  return { mean, std: Math.sqrt(Math.max(0, sumSquares / count - mean * mean)), hist };
}

/** Downscaled copy drawn back with smoothing off gives the blocky "pixel" look. */
function mosaic(image: HTMLImageElement, columns: number): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = columns;
  canvas.height = Math.max(1, Math.round(columns * image.naturalHeight / image.naturalWidth));
  canvas.getContext("2d")!.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas;
}

const smooth = (value: number) => value * value * (3 - 2 * value);
const format = (value: number, digits = 1) => value.toFixed(digits).replace(".", ",");

/** Map elapsed time to sweep position (0–1) and the cross-fade alpha of the reset phase. */
function timeline(elapsed: number) {
  const t = elapsed % CYCLE;
  if (t < HOLD_START) return { sweep: 0, fade: 0, phase: "start" as const };
  if (t < HOLD_START + SWEEP) return { sweep: smooth((t - HOLD_START) / SWEEP), fade: 0, phase: "sweep" as const };
  if (t < HOLD_START + SWEEP + HOLD_END) return { sweep: 1, fade: 0, phase: "done" as const };
  return { sweep: 1, fade: (t - HOLD_START - SWEEP - HOLD_END) / RESET, phase: "reset" as const };
}

export default function PixelConverter({ originalSrc, enhancedSrc }: { originalSrc: string; enhancedSrc: string }) {
  const imageCanvas = useRef<HTMLCanvasElement>(null);
  const histogramCanvas = useRef<HTMLCanvasElement>(null);
  const meanText = useRef<HTMLSpanElement>(null);
  const stdText = useRef<HTMLSpanElement>(null);
  const stageText = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    let frame = 0;
    let cancelled = false;
    let visible = true;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const observers: { disconnect(): void }[] = [];

    Promise.all([loadImage(originalSrc), loadImage(enhancedSrc)]).then(([original, enhanced]) => {
      if (cancelled || !imageCanvas.current || !histogramCanvas.current) return;
      const before = measure(original);
      const after = measure(enhanced);
      const view = imageCanvas.current;
      const chart = histogramCanvas.current;
      const context = view.getContext("2d")!;
      const chartContext = chart.getContext("2d")!;
      const ratio = original.naturalHeight / original.naturalWidth;
      let blocks = mosaic(enhanced, 64);
      let blockSize = 1;

      /** Match the canvas backing store to its CSS size and device pixel ratio. */
      const resize = () => {
        // 1.5× is visually indistinguishable here and draws ~44% fewer pixels than 2×.
        const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
        const width = Math.max(1, Math.round(view.clientWidth * dpr));
        view.width = width;
        view.height = Math.round(width * ratio);
        chart.width = Math.max(1, Math.round(chart.clientWidth * dpr));
        chart.height = Math.max(1, Math.round(chart.clientHeight * dpr));
        const columns = Math.max(24, Math.round(view.clientWidth / 9));
        blocks = mosaic(enhanced, columns);
        blockSize = width / columns;
      };
      resize();
      const resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(view);
      observers.push(resizeObserver);
      const intersection = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; });
      intersection.observe(view);
      observers.push(intersection);

      const drawImage = (sweep: number, fade: number, now: number) => {
        const { width, height } = view;
        context.imageSmoothingEnabled = true;
        context.drawImage(original, 0, 0, width, height);
        const band = Math.max(blockSize * 6, width * 0.14);
        const scan = sweep * (width + band);
        const done = Math.max(0, scan - band);

        // Converted region: the real enhanced output.
        if (done > 0) {
          context.save();
          context.beginPath();
          context.rect(0, 0, done, height);
          context.clip();
          context.globalAlpha = 1 - fade;
          context.drawImage(enhanced, 0, 0, width, height);
          context.restore();
        }

        // Processing band: enhanced colours rendered as visible pixel blocks.
        if (sweep > 0 && sweep < 1) {
          const left = Math.max(0, scan - band);
          const right = Math.min(width, scan);
          context.save();
          context.beginPath();
          context.rect(left, 0, right - left, height);
          context.clip();
          context.imageSmoothingEnabled = false;
          context.drawImage(blocks, 0, 0, width, height);
          // A few blocks flash per frame, as if being recomputed one at a time.
          const rows = Math.ceil(height / blockSize);
          const columns = Math.ceil((right - left) / blockSize);
          const seed = Math.floor(now / 70);
          for (let index = 0; index < 26; index += 1) {
            const hash = Math.abs(Math.sin((seed + index) * 12.9898 + index * 78.233) * 43758.5453) % 1;
            const hash2 = Math.abs(Math.sin((seed - index) * 4.1414 + index * 1.618) * 24634.6345) % 1;
            const x = left + Math.floor(hash * columns) * blockSize;
            const y = Math.floor(hash2 * rows) * blockSize;
            context.fillStyle = index % 3 === 0 ? "rgba(255,255,255,.55)" : "rgba(11,87,208,.45)";
            context.fillRect(x, y, blockSize, blockSize);
          }
          // Pixel grid inside the band makes the block structure readable.
          context.strokeStyle = "rgba(255,255,255,.12)";
          context.lineWidth = 1;
          context.beginPath();
          for (let x = Math.floor(left / blockSize) * blockSize; x <= right; x += blockSize) { context.moveTo(x, 0); context.lineTo(x, height); }
          for (let y = 0; y <= height; y += blockSize) { context.moveTo(left, y); context.lineTo(right, y); }
          context.stroke();
          context.restore();

          // Scan line with a soft glow.
          context.save();
          context.shadowColor = PRIMARY;
          context.shadowBlur = 18;
          context.fillStyle = "#8ab4f8";
          context.fillRect(Math.min(scan, width) - 2, 0, 3, height);
          context.restore();
        }
      };

      const drawHistogram = (mix: number) => {
        const { width, height } = chart;
        chartContext.clearRect(0, 0, width, height);
        const values = new Float32Array(256);
        let peak = 1;
        for (let level = 0; level < 256; level += 1) {
          values[level] = before.hist[level] * (1 - mix) + after.hist[level] * mix;
          // Ignore the two end bins for scaling so a clipped spike cannot flatten the rest.
          if (level > 0 && level < 255) peak = Math.max(peak, values[level]);
        }
        const barWidth = width / 256;
        chartContext.fillStyle = PRIMARY;
        for (let level = 0; level < 256; level += 1) {
          const barHeight = Math.min(1, values[level] / peak) * (height - 4);
          chartContext.fillRect(level * barWidth, height - barHeight, Math.max(1, barWidth - .3), barHeight);
        }
        const mean = before.mean * (1 - mix) + after.mean * mix;
        chartContext.fillStyle = "#b3261e";
        chartContext.fillRect((mean / 255) * width - 1, 0, 2, height);
        if (meanText.current) meanText.current.textContent = format(mean);
        if (stdText.current) stdText.current.textContent = format(before.std * (1 - mix) + after.std * mix);
      };

      const label = (phase: string, sweep: number) => {
        if (!stageText.current) return;
        stageText.current.textContent =
          phase === "start" ? "Ảnh gốc — thiếu sáng" :
          phase === "sweep" ? (sweep < .5 ? "Đang hiệu chỉnh Gamma…" : "Đang kéo giãn tương phản…") :
          phase === "done" ? "Hoàn tất cải thiện" : "Quay lại ảnh gốc…";
      };

      if (reducedMotion) {
        // No animation: show a static half/half comparison.
        drawImage(.5, 0, 0);
        drawHistogram(1);
        label("done", 1);
        return;
      }

      const start = performance.now();
      // 30 fps is plenty for the sweep; during the two hold phases nothing moves,
      // so the frame is drawn once on entry and then left alone.
      let last = 0;
      let heldPhase = "";
      const tick = (now: number) => {
        if (cancelled) return;
        frame = requestAnimationFrame(tick);
        if (!visible || now - last < 1000 / 30) return;
        last = now;
        const { sweep, fade, phase } = timeline(now - start);
        const holding = phase === "start" || phase === "done";
        if (holding && heldPhase === phase) return;
        heldPhase = holding ? phase : "";
        drawImage(sweep, fade, now);
        drawHistogram(sweep * (1 - fade));
        label(phase, sweep);
      };
      frame = requestAnimationFrame(tick);
    }).catch(() => { /* The hero is decorative; a failed load simply leaves the frame empty. */ });

    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      observers.forEach((observer) => observer.disconnect());
    };
  }, [originalSrc, enhancedSrc]);

  return <Box sx={{ borderRadius: "12px", overflow: "hidden", bgcolor: "#0f1115", color: "#e8eaed" }}>
    <Box component="canvas" ref={imageCanvas} role="img" aria-label="Minh hoạ quá trình cải thiện một ảnh thiếu sáng: ảnh tối được xử lý từng vùng pixel thành ảnh sáng và rõ hơn" sx={{ width: "100%", display: "block" }} />
    <Box sx={{ px: 2, pt: 1.5, pb: 1.75 }}>
      <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "baseline", gap: 2, flexWrap: "wrap" }}>
        <Typography component="span" ref={stageText} sx={{ fontSize: 13, fontWeight: 700, color: "#8ab4f8" }}>Ảnh gốc — thiếu sáng</Typography>
        <Typography component="span" sx={{ fontSize: 13, fontVariantNumeric: "tabular-nums", color: "#bdc1c6" }}>
          μ = <Box component="span" ref={meanText} sx={{ color: "#fff", fontWeight: 700 }}>–</Box>
          {"   "}σ = <Box component="span" ref={stdText} sx={{ color: "#fff", fontWeight: 700 }}>–</Box>
        </Typography>
      </Stack>
      <Box component="canvas" ref={histogramCanvas} aria-hidden="true" sx={{ width: "100%", height: 56, display: "block", mt: 1, bgcolor: "rgba(255,255,255,.04)", borderRadius: .5 }} />
      <Stack direction="row" sx={{ justifyContent: "space-between", mt: .4 }}>
        <Typography sx={{ fontSize: 11, color: "#9aa0a6" }}>0</Typography>
        <Typography sx={{ fontSize: 11, color: "#9aa0a6" }}>Histogram 256 mức xám</Typography>
        <Typography sx={{ fontSize: 11, color: "#9aa0a6" }}>255</Typography>
      </Stack>
    </Box>
  </Box>;
}
