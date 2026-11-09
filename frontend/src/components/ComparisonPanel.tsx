import { Box, Stack, Typography } from "@mui/material";
import CompareSlider from "./CompareSlider";
import ThresholdGauge from "./ThresholdGauge";
import { conditionTone, radius, tone } from "../lib/theme";
import type { AnalysisResult } from "../lib/types";

/** Before/after slider plus threshold gauges: what changed, and relative to which rule. */
export default function ComparisonPanel({ result }: { result: AnalysisResult }) {
  const { thresholds, metrics } = result;
  const identity = result.operation === "identity";
  return <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.15fr .85fr" }, gap: { xs: 3, lg: 5 }, alignItems: "start", mb: 4 }}>
    <Box>
      <Typography variant="overline" color="text.secondary">{identity ? "ẢNH ĐƯỢC GIỮ NGUYÊN" : "SO SÁNH TRƯỚC – SAU · KÉO ĐỂ XEM"}</Typography>
      <Box sx={{ mt: .75 }}>{identity
        ? <Box component="img" src={result.original_url} alt="Ảnh gốc được giữ nguyên" sx={{ width: "100%", maxHeight: 560, objectFit: "contain", display: "block", borderRadius: radius.media, bgcolor: tone.surfaceContainer }} />
        : <CompareSlider before={result.original_url} after={result.enhanced_url} beforeLabel="Ảnh gốc" afterLabel="Sau xử lý" />}</Box>
    </Box>
    <Box>
      <Typography variant="overline" color="text.secondary">VỊ TRÍ SO VỚI NGƯỠNG</Typography>
      <Stack spacing={3} sx={{ mt: 1.5 }}>
        <ThresholdGauge title="μ — Độ sáng (thang 0–255)" max={255} before={metrics.mean_gray.before} after={metrics.mean_gray.after}
          thresholds={[thresholds.dark_mean, thresholds.bright_mean]}
          zones={[{ to: thresholds.dark_mean, label: "Tối", color: conditionTone.dark.zone }, { to: thresholds.bright_mean, label: "Trung bình", color: conditionTone.mid.zone }, { to: 255, label: "Sáng", color: conditionTone.bright.zone }]} />
        <ThresholdGauge title="σ — Độ tương phản (thang 0–128)" max={128} before={metrics.std_gray.before} after={metrics.std_gray.after}
          thresholds={[thresholds.low_contrast_std]}
          zones={[{ to: thresholds.low_contrast_std, label: "Tương phản thấp", color: conditionTone.lowContrast.zone }, { to: 128, label: "Đạt", color: conditionTone.ok.zone }]} />
      </Stack>
    </Box>
  </Box>;
}
