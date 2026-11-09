import { Box, Stack, Typography } from "@mui/material";

export type Zone = { to: number; label: string; color: string };

const format = (value: number, digits = 2) => value.toFixed(digits).replace(".", ",");

/**
 * A 1-D scale showing where a metric sits relative to the decision thresholds.
 * The hollow marker is the original image, the filled marker the processed one,
 * so the effect of the transformation reads as movement across a threshold.
 */
export default function ThresholdGauge({ title, max, zones, thresholds, before, after }: {
  title: string; max: number; zones: Zone[]; thresholds: number[]; before: number; after: number;
}) {
  const percent = (value: number) => `${Math.min(100, Math.max(0, (value / max) * 100))}%`;
  const left = Math.min(before, after);
  const right = Math.max(before, after);
  let start = 0;
  const segments = zones.map((zone) => { const segment = { ...zone, from: start }; start = zone.to; return segment; });
  const unchanged = Math.abs(after - before) < .005;
  return <Box>
    <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "baseline", gap: 2 }}>
      <Typography sx={{ fontWeight: 700, fontSize: 15 }}>{title}</Typography>
      <Typography sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums", color: "#0b57d0", whiteSpace: "nowrap" }}>{format(before)} → {format(after)}</Typography>
    </Stack>
    <Box sx={{ position: "relative", mt: 3.25, mb: 4.5 }} role="img" aria-label={`${title}: trước ${format(before)}, sau ${format(after)}; ngưỡng ${thresholds.map((value) => format(value, 0)).join(", ")} trên thang 0–${max}`}>
      <Box sx={{ display: "flex", height: 12, borderRadius: 6, overflow: "hidden" }}>
        {segments.map((zone) => <Box key={zone.label} sx={{ width: `${((zone.to - zone.from) / max) * 100}%`, bgcolor: zone.color }} />)}
      </Box>
      {segments.map((zone) => <Typography key={zone.label} sx={{ position: "absolute", top: 18, left: `${((zone.from + zone.to) / 2 / max) * 100}%`, transform: "translateX(-50%)", fontSize: 11.5, color: "text.secondary", whiteSpace: "nowrap" }}>{zone.label}</Typography>)}
      {thresholds.map((value) => <Box key={value} sx={{ position: "absolute", top: -4, bottom: -4, left: percent(value), width: 2, ml: "-1px", bgcolor: "#202124" }}>
        <Typography sx={{ position: "absolute", top: 34, left: "50%", transform: "translateX(-50%)", fontSize: 11.5, fontWeight: 700 }}>{format(value, 0)}</Typography>
      </Box>)}
      {/* Travel line from the original value to the processed value. */}
      {!unchanged && <Box sx={{ position: "absolute", top: -14, height: 2, left: percent(left), width: `calc(${percent(right)} - ${percent(left)})`, bgcolor: "#0b57d0", opacity: .5 }} />}
      <Box title={`Trước: ${format(before)}`} sx={{ position: "absolute", top: -21, left: percent(before), width: 16, height: 16, ml: "-8px", borderRadius: "50%", border: "3px solid #0b57d0", bgcolor: "#fff" }} />
      {!unchanged && <Box title={`Sau: ${format(after)}`} sx={{ position: "absolute", top: -21, left: percent(after), width: 16, height: 16, ml: "-8px", borderRadius: "50%", bgcolor: "#0b57d0" }} />}    </Box>
    <Stack direction="row" spacing={2} sx={{ fontSize: 12, color: "text.secondary" }}>
      <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: .75 }}><Box component="span" sx={{ width: 10, height: 10, borderRadius: "50%", border: "2px solid #0b57d0" }} />Ảnh gốc</Box>
      <Box component="span" sx={{ display: "inline-flex", alignItems: "center", gap: .75 }}><Box component="span" sx={{ width: 10, height: 10, borderRadius: "50%", bgcolor: "#0b57d0" }} />{unchanged ? "Không đổi sau xử lý" : "Sau xử lý"}</Box>
    </Stack>
  </Box>;
}
