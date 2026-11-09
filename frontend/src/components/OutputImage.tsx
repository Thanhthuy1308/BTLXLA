import { motion } from "framer-motion";
import { Box, ButtonBase, Typography } from "@mui/material";
import { reveal, tone } from "../lib/theme";

/** Show the whole image (contain, never crop): these tiles are evidence, so no border pixels may be hidden. Click opens the viewer. */
export default function OutputImage({ label, detail, src, delay = 0, onOpen }: { label: string; detail: string; src: string; delay?: number; onOpen?: () => void }) {
  return <motion.div {...reveal} transition={{ duration: .3, delay }}>
    <ButtonBase onClick={onOpen} disabled={!onOpen} focusRipple aria-label={`Phóng to: ${label}`} sx={{ display: "block", width: "100%", borderRadius: 1, cursor: onOpen ? "zoom-in" : "default" }}>
      <Box component="img" src={src} alt={label} sx={{ width: "100%", aspectRatio: "4 / 3", display: "block", objectFit: "contain", borderRadius: 1, bgcolor: tone.surfaceContainer }} />
    </ButtonBase>
    <Typography sx={{ mt: 1, fontSize: 15, fontWeight: 700 }}>{label}</Typography>
    <Typography variant="caption" color="text.secondary">{detail}</Typography>
  </motion.div>;
}
