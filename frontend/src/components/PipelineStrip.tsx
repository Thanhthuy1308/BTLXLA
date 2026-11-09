import { motion } from "framer-motion";
import { Box, ButtonBase, Stack, Typography } from "@mui/material";
import MiniHistogram from "./MiniHistogram";
import { fixed } from "../lib/format";
import { reveal, tone } from "../lib/theme";
import type { PipelineStage } from "../lib/types";

/** Numbered pipeline: each produced image with its μ, σ and histogram, in processing order. */
export default function PipelineStrip({ stages, onOpen }: { stages: PipelineStage[]; onOpen: (index: number) => void }) {
  return <Box sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, alignItems: "stretch", gap: { xs: 1, md: 0 } }}>
    {stages.map((stage, index) => <Box key={stage.key} sx={{ display: "flex", flexDirection: { xs: "column", md: "row" }, alignItems: "center", flex: 1, minWidth: 0 }}>
      {index > 0 && <Box aria-hidden="true" sx={{ px: { md: .75 }, py: { xs: .25, md: 0 }, color: tone.outlineVariant, fontSize: 22, fontWeight: 700, transform: { xs: "rotate(90deg)", md: "none" } }}>→</Box>}
      <motion.div {...reveal} transition={{ duration: .25, delay: index * .06 }} style={{ flex: 1, minWidth: 0, width: "100%", alignSelf: "stretch" }}>
        <Box sx={{ height: "100%", p: 1.25, borderRadius: 1.5, border: `1px solid ${stage.final ? tone.primary : tone.outline}`, bgcolor: stage.final ? "#f8faff" : "#fff" }}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
            <Box sx={{ width: 22, height: 22, flexShrink: 0, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: 12, fontWeight: 700, color: "#fff", bgcolor: stage.final ? tone.primary : tone.onSurfaceVariant }}>{index + 1}</Box>
            <Typography sx={{ fontWeight: 700, fontSize: 14 }} noWrap>{stage.label}{stage.final ? " · kết quả" : ""}</Typography>
          </Stack>
          <ButtonBase onClick={() => onOpen(index)} focusRipple aria-label={`Phóng to: ${stage.label}`} sx={{ display: "block", width: "100%", borderRadius: 1, cursor: "zoom-in" }}>
            <Box component="img" src={stage.url} alt={stage.label} sx={{ width: "100%", aspectRatio: "4 / 3", objectFit: "contain", display: "block", borderRadius: 1, bgcolor: tone.surfaceContainer }} />
          </ButtonBase>
          <Typography sx={{ mt: 1, fontSize: 13, fontVariantNumeric: "tabular-nums" }}>μ = <b>{fixed(stage.mean)}</b> · σ = <b>{fixed(stage.std)}</b></Typography>
          <Box sx={{ mt: .75 }}><MiniHistogram hist={stage.hist} mean={stage.mean} /></Box>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: .75, lineHeight: 1.35 }}>{stage.note}</Typography>
        </Box>
      </motion.div>
    </Box>)}
  </Box>;
}
