import { useEffect, useMemo, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import { Box, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { count, fixed } from "../lib/format";
import { tone } from "../lib/theme";

type Series = { key: "before" | "after"; label: string; hist: number[]; mean: number; color: string };
type Scale = "linear" | "log";

const HEIGHT = 250;
const PAD = { left: 52, right: 12, top: 14, bottom: 30 };
const TICKS = [0, 50, 100, 150, 200, 255];

/**
 * Before/after 256-bin histogram drawn in the browser from the counts the Python
 * pipeline returned, so every bar is the server's number. Hover (or ←/→ when
 * focused) reads the exact pixel count at a grey level; a log scale reveals small
 * populations that a linear axis flattens.
 */
export default function InteractiveHistogram({ before, after, meanBefore, meanAfter, unchanged = false }: {
  before: number[]; after: number[]; meanBefore: number; meanAfter: number; unchanged?: boolean;
}) {
  const frame = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  const [scale, setScale] = useState<Scale>("linear");
  const [visible, setVisible] = useState<string[]>(unchanged ? ["before"] : ["before", "after"]);
  const [level, setLevel] = useState<number | null>(null);

  useEffect(() => {
    const element = frame.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)));
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const series: Series[] = useMemo(() => [
    { key: "before", label: "Ảnh gốc", hist: before, mean: meanBefore, color: tone.before },
    { key: "after", label: "Sau xử lý", hist: after, mean: meanAfter, color: tone.primary },
  ], [before, after, meanBefore, meanAfter]);
  const shown = series.filter((item) => visible.includes(item.key));
  const totals = { before: before.reduce((a, b) => a + b, 0), after: after.reduce((a, b) => a + b, 0) };

  const plotWidth = width - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const binWidth = plotWidth / 256;
  // Linear: ignore the two end bins so a clipped spike cannot flatten the shape (the
  // spike is drawn to the top and labelled). Log: every bin fits on the axis.
  const linearPeak = Math.max(1, ...shown.flatMap((item) => item.hist.slice(1, 255)));
  const logPeak = Math.log1p(Math.max(1, ...shown.flatMap((item) => item.hist)));
  const y = (value: number) => {
    const ratio = scale === "log" ? Math.log1p(value) / logPeak : Math.min(1, value / linearPeak);
    return PAD.top + plotHeight * (1 - ratio);
  };
  const x = (bin: number) => PAD.left + bin * binWidth;

  const area = (hist: number[]) => {
    let path = `M${x(0)},${PAD.top + plotHeight}`;
    hist.forEach((value, bin) => { const top = y(value); path += `L${x(bin)},${top}L${x(bin + 1)},${top}`; });
    return `${path}L${x(256)},${PAD.top + plotHeight}Z`;
  };

  const pick = (event: PointerEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const bin = Math.floor((event.clientX - bounds.left - PAD.left) / binWidth);
    setLevel(bin >= 0 && bin <= 255 ? bin : null);
  };
  const keys = (event: KeyboardEvent) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.shiftKey ? 10 : 1;
    setLevel((current) => Math.min(255, Math.max(0, (current ?? 128) + (event.key === "ArrowRight" ? step : -step))));
  };

  const yTicks = scale === "linear" ? [0, linearPeak / 2, linearPeak] : [];
  const clipped = scale === "linear" ? shown.flatMap((item) => [0, 255].filter((bin) => item.hist[bin] > linearPeak).map((bin) => ({ ...item, bin }))) : [];
  const tooltipLeft = level === null ? 0 : Math.min(width - 200, Math.max(0, x(level) - 100));

  return <Box>
    <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", gap: 1, mb: 1 }}>
      <ToggleButtonGroup size="small" value={visible} onChange={(_, value: string[]) => value.length && setVisible(value)} aria-label="Chuỗi dữ liệu hiển thị" sx={{ "& .MuiToggleButton-root": { textTransform: "none", px: 1.25, fontWeight: 650, gap: .75 } }}>
        {series.map((item) => <ToggleButton key={item.key} value={item.key} disabled={unchanged && item.key === "after"}><Box component="span" sx={{ width: 10, height: 10, borderRadius: .5, bgcolor: item.color, opacity: .8 }} />{item.label}</ToggleButton>)}
      </ToggleButtonGroup>
      <ToggleButtonGroup size="small" exclusive value={scale} onChange={(_, value: Scale | null) => value && setScale(value)} aria-label="Thang trục tung" sx={{ "& .MuiToggleButton-root": { textTransform: "none", px: 1.25, fontWeight: 650 } }}>
        <ToggleButton value="linear">Thang tuyến tính</ToggleButton><ToggleButton value="log">Thang log</ToggleButton>
      </ToggleButtonGroup>
    </Stack>
    <Box ref={frame} sx={{ position: "relative", border: `1px solid ${tone.outline}`, borderRadius: 1 }}>
      <svg width={width} height={HEIGHT} role="img" tabIndex={0} onKeyDown={keys} onPointerMove={pick} onPointerLeave={() => setLevel(null)} onBlur={() => setLevel(null)}
        aria-label={`Histogram 256 mức xám. Ảnh gốc μ = ${fixed(meanBefore)}${unchanged ? "" : `, sau xử lý μ = ${fixed(meanAfter)}`}. Dùng phím mũi tên để đọc từng mức xám.`}
        style={{ display: "block", outline: "none", touchAction: "pan-y" }}>
        {yTicks.map((tick) => <g key={tick}>
          <line x1={PAD.left} x2={width - PAD.right} y1={y(tick)} y2={y(tick)} stroke={tone.outline} />
          <text x={PAD.left - 6} y={y(tick) + 4} textAnchor="end" fontSize={11} fill={tone.onSurfaceVariant}>{count(tick)}</text>
        </g>)}
        {scale === "log" && <text x={PAD.left - 6} y={PAD.top + 10} textAnchor="end" fontSize={11} fill={tone.onSurfaceVariant}>log</text>}
        {shown.map((item) => <path key={item.key} d={area(item.hist)} fill={item.color} fillOpacity={shown.length > 1 ? .45 : .75} />)}
        {shown.map((item) => <line key={`mean-${item.key}`} x1={PAD.left + (item.mean / 256) * plotWidth} x2={PAD.left + (item.mean / 256) * plotWidth} y1={PAD.top} y2={PAD.top + plotHeight} stroke={item.color} strokeWidth={2} strokeDasharray="5 4" />)}
        {clipped.map((item) => <text key={`${item.key}-${item.bin}`} x={x(item.bin) + (item.bin === 0 ? 4 : -4)} y={PAD.top + 12 + (item.key === "after" ? 13 : 0)} textAnchor={item.bin === 0 ? "start" : "end"} fontSize={11} fontWeight={700} fill={tone.error}>
          ▲ {item.label.toLowerCase()} · mức {item.bin}: {count(item.hist[item.bin])} px
        </text>)}
        <line x1={PAD.left} x2={width - PAD.right} y1={PAD.top + plotHeight} y2={PAD.top + plotHeight} stroke={tone.onSurfaceVariant} />
        {TICKS.map((tick) => <text key={tick} x={x(tick + .5)} y={HEIGHT - 10} textAnchor="middle" fontSize={11} fill={tone.onSurfaceVariant}>{tick}</text>)}
        {level !== null && <rect x={x(level)} y={PAD.top} width={Math.max(1.5, binWidth)} height={plotHeight} fill={tone.onSurface} fillOpacity={.35} />}
      </svg>
      {level !== null && <Box role="status" sx={{ position: "absolute", top: 8, left: tooltipLeft, width: 200, p: 1, borderRadius: 1, bgcolor: "rgba(32,33,36,.92)", color: "#fff", pointerEvents: "none", fontSize: 12.5, lineHeight: 1.5 }}>
        <Box sx={{ fontWeight: 700 }}>Mức xám {level}</Box>
        {shown.map((item) => <Box key={item.key}>{item.label}: {count(item.hist[level])} px ({fixed((item.hist[level] / Math.max(1, totals[item.key])) * 100)}%)</Box>)}
      </Box>}
    </Box>
    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: .75 }}>
      Trục hoành: mức xám 0 (đen) → 255 (trắng). Trục tung: số pixel. Nét đứt: μ của từng ảnh. Rê chuột hoặc dùng phím ←/→ để đọc giá trị.
    </Typography>
  </Box>;
}
