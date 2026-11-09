import { useState } from "react";
import { Box, Button, Menu, MenuItem, Typography } from "@mui/material";

import type { DownloadItem } from "../lib/types";

/** One "Tải xuống" button that lists every server-generated artefact for the current job. */
export default function DownloadMenu({ items, fullWidth = false }: { items: DownloadItem[]; fullWidth?: boolean }) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);
  return <>
    <Button variant="contained" fullWidth={fullWidth} onClick={(event) => setAnchor(event.currentTarget)} aria-haspopup="menu" aria-expanded={Boolean(anchor)} endIcon={<Box component="span" aria-hidden="true" sx={{ fontSize: 12 }}>▾</Box>} sx={{ whiteSpace: "nowrap", px: 1.5 }}>Tải xuống</Button>
    <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)} slotProps={{ paper: { sx: { mt: .75, minWidth: 260, border: "1px solid #e8eaed" } } }}>
      {items.map((item) => <MenuItem key={item.url} component="a" href={item.url} download onClick={() => setAnchor(null)} sx={{ display: "block", py: 1 }}>
        <Typography sx={{ fontWeight: 650, fontSize: 14 }}>{item.label}</Typography>
        <Typography variant="caption" color="text.secondary">{item.detail}</Typography>
      </MenuItem>)}
    </Menu>
  </>;
}
