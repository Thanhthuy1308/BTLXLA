import { useState } from "react";
import { Box, Button, Collapse, Divider, Stack, Typography } from "@mui/material";
import InfoHint from "./InfoHint";
import { fixed } from "../lib/format";
import { tone } from "../lib/theme";
import type { AnalysisResult, Metric, MetricGuide, Paragraph, TransformGuide } from "../lib/types";

/** One measured quantity and the threshold rule it was checked against. */
export function MetricExplanation({ guide, metric }: { guide: MetricGuide; metric: Metric }) {
  return <Box sx={{ borderLeft: `3px solid ${guide.triggered ? tone.primary : "#dadce0"}`, pl: 1.75, py: .35 }}>
    <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "baseline", gap: 2 }}><Typography sx={{ fontWeight: 700 }}>{guide.symbol} — {guide.name}<InfoHint text={`${guide.definition} ${guide.effect}`} /></Typography><Typography sx={{ whiteSpace: "nowrap", fontWeight: 700, color: guide.triggered ? tone.primary : tone.onSurface }}>{fixed(metric.before)} → {fixed(metric.after)}</Typography></Stack>
    <Typography variant="body2" sx={{ mt: .4 }}><Box component="span" sx={{ fontWeight: 700 }}>Quy tắc:</Box> {guide.rule} <Box component="span" sx={{ color: guide.triggered ? tone.primary : "text.secondary" }}>({guide.triggered ? "thỏa điều kiện" : "không thỏa điều kiện"})</Box></Typography>
  </Box>;
}

/** Show only the case produced by this run; the full rule table is one click away. */
export function ClassificationCases({ result }: { result: AnalysisResult }) {
  const [open, setOpen] = useState(false);
  const { mean_gray, std_gray } = result.interpretation.metrics;
  const cases = [
    { active: mean_gray.triggered && std_gray.triggered, title: "Trường hợp 1: Ảnh tối và tương phản thấp", text: "μ < 85 và σ < 45: hiệu chỉnh Gamma, sau đó kéo giãn tương phản." },
    { active: mean_gray.triggered && !std_gray.triggered, title: "Trường hợp 2: Ảnh tối", text: "μ < 85 và σ ≥ 45: hiệu chỉnh Gamma để làm sáng vùng tối." },
    { active: !mean_gray.triggered && std_gray.triggered, title: "Trường hợp 3: Ảnh tương phản thấp", text: "μ ≥ 85 và σ < 45: kéo giãn tương phản để mở rộng dải mức xám." },
    { active: !mean_gray.triggered && !std_gray.triggered, title: "Trường hợp 4: Chưa có dấu hiệu tối hoặc tương phản thấp", text: "μ ≥ 85 và σ ≥ 45: giữ nguyên giá trị mức xám ban đầu." },
  ];
  const current = cases.find((item) => item.active)!;
  const caseBox = (item: typeof cases[number]) => <Box key={item.title} sx={{ borderLeft: `3px solid ${item.active ? tone.primary : "#dadce0"}`, pl: 1.5, py: .25 }}><Typography sx={{ fontWeight: 700, color: item.active ? tone.primary : tone.onSurface }}>{item.title}{item.active ? " — kết quả hiện tại" : ""}</Typography><Typography variant="body2" color="text.secondary">{item.text}</Typography></Box>;
  return <Box sx={{ mt: 4 }}>
    <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center", gap: 2 }}>
      <Typography variant="overline" color="text.secondary">QUY TẮC PHÂN LOẠI</Typography>
      <Button size="small" onClick={() => setOpen((value) => !value)} aria-expanded={open} sx={{ minHeight: 32 }}>{open ? "Thu gọn" : "Xem cả 4 trường hợp"}</Button>
    </Stack>
    {!open && <Box sx={{ mt: 1 }}>{caseBox(current)}</Box>}
    <Collapse in={open}><Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" }, columnGap: 3, rowGap: 1.5, mt: 1 }}>{cases.map(caseBox)}</Box><Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>Ngoài ra, ảnh có μ &gt; 170 được nhận xét là có xu hướng sáng; chương trình chỉ nhận xét và không tự làm tối ảnh.</Typography></Collapse>
  </Box>;
}

/** Overall Vietnamese assessment (output 6 of the report scope), authored by the server from the measured values. */
export function OverviewParagraphs({ items }: { items: Paragraph[] }) {
  return <Box sx={{ mt: 4 }}><Typography variant="overline" color="text.secondary">NHẬN XÉT TỔNG QUAN</Typography><Stack divider={<Divider flexItem />} sx={{ mt: 1 }}>{items.map((item) => <Box key={item.title} sx={{ py: 1.3, display: "grid", gridTemplateColumns: { xs: "1fr", sm: "180px 1fr" }, gap: { xs: .4, sm: 2 } }}><Typography sx={{ fontWeight: 700 }}>{item.title}</Typography><Typography color="text.secondary">{item.text}</Typography></Box>)}</Stack></Box>;
}

export function TransformExplanations({ guides }: { guides: TransformGuide[] }) {
  return <Box sx={{ mt: 3 }}><Typography variant="overline" color="text.secondary">CÁC BƯỚC ĐÃ ÁP DỤNG</Typography><Stack divider={<Divider flexItem />} sx={{ mt: 1 }}>{guides.map((guide) => <Box key={guide.name} sx={{ py: 1.3 }}><Typography sx={{ fontWeight: 700 }}>{guide.name}</Typography><Typography variant="body2" sx={{ mt: .25, fontFamily: "monospace", color: tone.primary }}>{guide.formula}</Typography><Typography variant="body2" color="text.secondary" sx={{ mt: .45 }}>{guide.effect}</Typography></Box>)}</Stack></Box>;
}
