import { useState } from "react";
import { Box, Stack, Typography } from "@mui/material";
import { useLightbox } from "../../components/Lightbox";
import OutputImage from "../../components/OutputImage";
import PillTabs from "../../components/PillTabs";
import { fixed } from "../../lib/format";
import { radius, tone } from "../../lib/theme";
import type { AnalysisResult } from "../../lib/types";

type EdgeView = "edges" | "overlay";

export default function EdgesTab({ result }: { result: AnalysisResult }) {
  const viewer = useLightbox();
  const [view, setView] = useState<EdgeView>("overlay");
  const edges = result.metrics.edge_ratio;
  const overlay = view === "overlay";
  const items = [
    { src: overlay ? result.original_overlay_url : result.original_edges_url, title: `Canny ảnh gốc — tỉ lệ biên ${fixed(edges.before)}%` },
    { src: overlay ? result.enhanced_overlay_url : result.enhanced_edges_url, title: `Canny ảnh sau xử lý — tỉ lệ biên ${fixed(edges.after)}%` },
  ];
  return <Box>
    <Stack direction={{ xs: "column", sm: "row" }} sx={{ justifyContent: "space-between", alignItems: { sm: "center" }, gap: 1.5, mb: 2 }}>
      <Typography sx={{ fontWeight: 700 }}>Tỉ lệ pixel biên: {fixed(edges.before)}% → {fixed(edges.after)}%</Typography>
      <PillTabs variant="segmented" label="Cách hiển thị ảnh biên" value={view} onChange={setView} options={[
        { value: "overlay", label: "Phủ biên lên ảnh" },
        { value: "edges", label: "Chỉ ảnh biên" },
      ]} />
    </Stack>
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
      <OutputImage label={items[0].title} detail={edges.before < .01 && edges.after >= .01 ? "Không phát hiện biên: chênh lệch mức xám của ảnh gốc quá nhỏ" : "Trước khi cải thiện"} src={items[0].src} onOpen={() => viewer.open(items, 0)} />
      <OutputImage label={items[1].title} detail="Sau khi cải thiện" src={items[1].src} delay={.05} onOpen={() => viewer.open(items, 1)} />
    </Box>
    <Box sx={{ mt: 3, p: 2.25, borderRadius: radius.card, bgcolor: tone.info }}>
      <Typography sx={{ fontWeight: 700 }}>Cách đọc kết quả so sánh</Typography>
      <Typography color="text.secondary" sx={{ mt: .5 }}>{result.interpretation.canny.definition} {result.interpretation.canny.reading}</Typography>
    </Box>
    {viewer.element}
  </Box>;
}
