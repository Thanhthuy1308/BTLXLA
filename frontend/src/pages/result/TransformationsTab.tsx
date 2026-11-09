import { Box, Typography } from "@mui/material";
import { TransformExplanations } from "../../components/Explanations";
import { useLightbox } from "../../components/Lightbox";
import PipelineStrip from "../../components/PipelineStrip";
import { fixed } from "../../lib/format";
import type { AnalysisResult } from "../../lib/types";

export default function TransformationsTab({ result }: { result: AnalysisResult }) {
  const viewer = useLightbox();
  const items = result.stages.map((item, index) => ({ src: item.url, title: `${index + 1}. ${item.label}`, detail: `μ = ${fixed(item.mean)} · σ = ${fixed(item.std)} · ${item.note}` }));
  return <Box>
    <Typography variant="overline" color="text.secondary">QUY TRÌNH XỬ LÝ · BẤM ẢNH ĐỂ PHÓNG TO</Typography>
    <Box sx={{ mt: 1 }}><PipelineStrip stages={result.stages} onOpen={(index) => viewer.open(items, index)} /></Box>
    <TransformExplanations guides={result.interpretation.transformations} />
    {viewer.element}
  </Box>;
}
