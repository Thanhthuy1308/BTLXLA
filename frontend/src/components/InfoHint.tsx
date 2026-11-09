import { Box, Tooltip } from "@mui/material";
import { tone } from "../lib/theme";

/** Small "i" trigger that reveals a definition on hover or keyboard focus. */
export default function InfoHint({ text }: { text: string }) {
  return <Tooltip title={text} arrow placement="top">
    <Box component="span" tabIndex={0} aria-label={text} sx={{ display: "inline-grid", placeItems: "center", width: 18, height: 18, ml: .75, borderRadius: "50%", border: `1px solid ${tone.outlineVariant}`, fontSize: 11, fontWeight: 700, color: "text.secondary", cursor: "help", verticalAlign: "1px" }}>i</Box>
  </Tooltip>;
}
