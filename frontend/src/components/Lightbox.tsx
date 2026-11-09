import { useEffect, useState } from "react";
import { Box, Button, Dialog, IconButton, Stack, Typography } from "@mui/material";

export type LightboxItem = { src: string; title: string; detail?: string };

/** Shared state for opening the image viewer at a given item. */
export function useLightbox() {
  const [state, setState] = useState<{ items: LightboxItem[]; index: number } | null>(null);
  return {
    open: (items: LightboxItem[], index = 0) => setState({ items, index }),
    element: <Lightbox items={state?.items ?? []} index={state ? state.index : null} onClose={() => setState(null)} />,
  };
}

/**
 * Full-screen viewer for evidence images. "Kích thước thật" shows pixels 1:1 so
 * amplified noise or clipping is visible; ←/→ step through the related images
 * (e.g. every pipeline stage) without closing the dialog.
 */
export default function Lightbox({ items, index, onClose }: { items: LightboxItem[]; index: number | null; onClose: () => void }) {
  const [current, setCurrent] = useState(0);
  const [actualSize, setActualSize] = useState(false);
  useEffect(() => { if (index !== null) { setCurrent(index); setActualSize(false); } }, [index]);

  const open = index !== null && items.length > 0;
  const item = items[Math.min(current, items.length - 1)];
  const step = (delta: number) => setCurrent((value) => (value + delta + items.length) % items.length);

  return <Dialog open={open} onClose={onClose} fullWidth maxWidth="xl" aria-label={item?.title}
    onKeyDown={(event) => { if (event.key === "ArrowRight") step(1); if (event.key === "ArrowLeft") step(-1); }}
    slotProps={{ paper: { sx: { bgcolor: "#111317", color: "#e8eaed", m: { xs: 1, md: 3 }, width: "100%", maxHeight: "calc(100% - 32px)" } } }}>
    {item && <Box sx={{ display: "flex", flexDirection: "column", minHeight: 0, height: "100%" }}>
      <Stack direction="row" sx={{ alignItems: "center", gap: 1.5, px: 2, py: 1.25, borderBottom: "1px solid rgba(255,255,255,.12)" }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography sx={{ fontWeight: 700 }} noWrap>{item.title}</Typography>
          {item.detail && <Typography variant="caption" sx={{ color: "#9aa0a6" }} noWrap component="p">{item.detail}</Typography>}
        </Box>
        {items.length > 1 && <Typography variant="caption" sx={{ color: "#9aa0a6" }}>{current + 1}/{items.length}</Typography>}
        <Button size="small" variant="outlined" onClick={() => setActualSize((value) => !value)} sx={{ minHeight: 34, color: "#e8eaed", borderColor: "rgba(255,255,255,.3)" }}>{actualSize ? "Vừa khung" : "Kích thước thật"}</Button>
        <IconButton onClick={onClose} aria-label="Đóng" sx={{ color: "#e8eaed" }}>✕</IconButton>
      </Stack>
      <Box sx={{ position: "relative", flex: 1, minHeight: 0, overflow: actualSize ? "auto" : "hidden", display: actualSize ? "block" : "grid", placeItems: "center", p: actualSize ? 0 : 2 }}>
        <Box component="img" src={item.src} alt={item.title} sx={actualSize ? { display: "block", maxWidth: "none" } : { display: "block", width: "100%", height: "calc(100vh - 150px)", objectFit: "contain" }} />
        {items.length > 1 && <>
          <IconButton onClick={() => step(-1)} aria-label="Ảnh trước" sx={{ position: "fixed", left: { xs: 12, md: 36 }, top: "50%", bgcolor: "rgba(0,0,0,.55)", color: "#fff", "&:hover": { bgcolor: "rgba(0,0,0,.75)" } }}>‹</IconButton>
          <IconButton onClick={() => step(1)} aria-label="Ảnh tiếp theo" sx={{ position: "fixed", right: { xs: 12, md: 36 }, top: "50%", bgcolor: "rgba(0,0,0,.55)", color: "#fff", "&:hover": { bgcolor: "rgba(0,0,0,.75)" } }}>›</IconButton>
        </>}
      </Box>
    </Box>}
  </Dialog>;
}
