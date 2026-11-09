import { Box } from "@mui/material";

/**
 * Compact 256-bin histogram rendered as an SVG area. The y-scale ignores the two
 * end bins so a clipped spike at 0 or 255 cannot flatten the rest of the shape,
 * matching the server-side histogram figure.
 */
export default function MiniHistogram({ hist, mean, height = 44 }: { hist: number[]; mean: number; height?: number }) {
  const peak = Math.max(1, ...hist.slice(1, 255));
  const points = hist.map((value, level) => `${level},${60 - Math.min(1, value / peak) * 58}`).join(" ");
  return <Box component="svg" viewBox="0 0 256 60" preserveAspectRatio="none" aria-hidden="true" sx={{ width: "100%", height, display: "block", bgcolor: "#f1f3f4", borderRadius: .5 }}>
    <polygon points={`0,60 ${points} 255,60`} fill="#0b57d0" fillOpacity={.85} />
    <line x1={mean} x2={mean} y1={0} y2={60} stroke="#b3261e" strokeWidth={2} vectorEffect="non-scaling-stroke" />
  </Box>;
}
