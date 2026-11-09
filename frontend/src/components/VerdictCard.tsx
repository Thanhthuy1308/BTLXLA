import { motion } from "framer-motion";
import { Box, Stack, Typography } from "@mui/material";
import ConditionChips from "./ConditionChips";
import { fixed } from "../lib/format";
import { useCountUp } from "../lib/motion";
import { radius, reveal, tone } from "../lib/theme";
import type { AnalysisResult, Metric } from "../lib/types";

/** One before → after figure; the headline number counts up from the original value. */
function Kpi({ label, metric, digits = 2, unit = "", delay = 0 }: { label: string; metric: Metric; digits?: number; unit?: string; delay?: number }) {
  const delta = metric.after - metric.before;
  const unchanged = Math.abs(delta) < 10 ** -digits / 2;
  const shown = useCountUp(metric.before, metric.after, 750, 200 + delay);
  return <Box sx={{ p: 1.75, borderRadius: radius.card, bgcolor: tone.surfaceContainer }}>
    <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 650 }}>{label}</Typography>
    <Typography aria-label={`${label}: ${fixed(metric.after, digits)}${unit}`} sx={{ mt: .25, fontSize: 20, fontWeight: 700, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>{fixed(shown, digits)}{unit}</Typography>
    <Typography variant="body2" sx={{ fontVariantNumeric: "tabular-nums", color: unchanged ? "text.secondary" : tone.primary }}>
      từ {fixed(metric.before, digits)}{unit} · {unchanged ? "không đổi" : `${delta > 0 ? "+" : "−"}${fixed(Math.abs(delta), digits)}${unit}`}
    </Typography>
  </Box>;
}

/** The answer first: classification, applied operation, and the four headline measurements. */
export default function VerdictCard({ result }: { result: AnalysisResult }) {
  const identity = result.operation === "identity";
  return <motion.div {...reveal} transition={{ duration: .25 }}>
    <Box sx={{ p: { xs: 2, md: 2.5 }, mb: 3, borderRadius: radius.card, border: `1px solid ${tone.outline}`, bgcolor: "#fff" }}>
      <Stack direction={{ xs: "column", md: "row" }} sx={{ justifyContent: "space-between", gap: 1, alignItems: { md: "center" } }}>
        <Box>
          <Typography variant="overline" color="text.secondary" sx={{ display: "block" }}>KẾT LUẬN · {result.name}</Typography>
          <Box sx={{ mt: .5 }}><ConditionChips conditions={result.conditions} /></Box>
        </Box>
        <Typography color="text.secondary">{identity ? "Ảnh không vượt ngưỡng nào nên được giữ nguyên." : <>Đã áp dụng: <Box component="span" sx={{ fontWeight: 700, color: tone.onSurface }}>{result.operation_label}</Box></>}</Typography>
      </Stack>
      <Box sx={{ mt: 2, display: "grid", gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" }, gap: 1.5 }}>
        <Kpi label="μ — Mức xám trung bình" metric={result.metrics.mean_gray} />
        <Kpi label="σ — Độ lệch chuẩn" metric={result.metrics.std_gray} delay={80} />
        <Kpi label="Dải động (p2–p98)" metric={result.metrics.dynamic_range} digits={0} delay={160} />
        <Kpi label="Tỉ lệ biên Canny" metric={result.metrics.edge_ratio} unit="%" delay={240} />
      </Box>
    </Box>
  </motion.div>;
}
