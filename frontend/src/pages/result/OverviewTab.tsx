import { Box, Stack, Typography } from "@mui/material";
import ComparisonPanel from "../../components/ComparisonPanel";
import { ClassificationCases, MetricExplanation, OverviewParagraphs } from "../../components/Explanations";
import InfoHint from "../../components/InfoHint";
import InteractiveHistogram from "../../components/InteractiveHistogram";
import type { AnalysisResult } from "../../lib/types";

export default function OverviewTab({ result }: { result: AnalysisResult }) {
  const first = result.stages[0];
  const last = result.stages[result.stages.length - 1];
  return <Box>
    <ComparisonPanel result={result} />
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.25fr .75fr" }, gap: 5, alignItems: "start" }}>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="overline" color="text.secondary">PHÂN BỐ 256 MỨC XÁM</Typography>
        <Typography variant="h3" sx={{ mt: .25, mb: 1.5 }}>Histogram trước và sau xử lý<InfoHint text={`${result.interpretation.histogram.definition} ${result.interpretation.histogram.reading}`} /></Typography>
        <InteractiveHistogram key={result.job_id} before={first.hist} after={last.hist} meanBefore={first.mean} meanAfter={last.mean} unchanged={result.operation === "identity"} />
      </Box>
      <Box>
        <Typography variant="overline" color="text.secondary">THÔNG SỐ VÀ NGƯỠNG</Typography>
        <Typography color="text.secondary" sx={{ mt: .25 }}>{result.interpretation.summary}</Typography>
        <Stack spacing={2.1} sx={{ mt: 2.25 }}>
          <MetricExplanation guide={result.interpretation.metrics.mean_gray} metric={result.metrics.mean_gray} />
          <MetricExplanation guide={result.interpretation.metrics.std_gray} metric={result.metrics.std_gray} />
        </Stack>
      </Box>
    </Box>
    <OverviewParagraphs items={result.interpretation.overview} />
    <ClassificationCases result={result} />
  </Box>;
}
