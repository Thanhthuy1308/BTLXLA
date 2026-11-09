import { Link as RouterLink, useLocation } from "react-router-dom";
import { AppBar, Box, Button, Stack, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import { assetUrl } from "../lib/config";
import { tone } from "../lib/theme";

export default function Header() {
  const location = useLocation();
  const selectedTab = location.pathname.startsWith("/studio") ? 1 : 0;
  return <AppBar position="sticky" color="transparent" elevation={0} sx={{ bgcolor: "rgba(255,255,255,.96)", backdropFilter: "blur(16px)", borderBottom: `1px solid ${tone.outline}` }}>
    <Toolbar sx={{ minHeight: { xs: "60px !important", md: "72px !important" }, px: { xs: 1.5, md: 4 }, gap: { xs: 1, md: 3 } }}>
      <Stack direction="row" spacing={1.4} component={RouterLink} to="/" aria-label="Histogram Studio, về trang Giới thiệu" sx={{ alignItems: "center", minWidth: { md: 260 }, color: "inherit", textDecoration: "none" }}>
        <Box component="img" src={assetUrl("favicon.svg")} alt="" sx={{ width: 38, height: 38, display: "block", flexShrink: 0 }} />
        <Box sx={{ display: { xs: "none", sm: "block" } }}><Typography sx={{ fontWeight: 700, lineHeight: 1.15 }}>Histogram Studio</Typography><Typography variant="caption" color="text.secondary">Phân tích độ sáng và độ tương phản</Typography></Box>
      </Stack>
      <Tabs value={selectedTab} sx={{ minHeight: 48, "& .MuiTab-root": { minHeight: 48, minWidth: { xs: 0, md: 90 }, px: { xs: 1.25, md: 2 }, textTransform: "none", fontWeight: 650 } }}>
        <Tab component={RouterLink} to="/" label="Giới thiệu" /><Tab component={RouterLink} to="/studio" label="Phân tích ảnh" />
      </Tabs>
      <Box sx={{ flex: 1 }} />
      <Button component="a" href="https://github.com/Thanhthuy1308/BTLXLA" target="_blank" rel="noreferrer" variant="outlined" aria-label="GitHub"
        endIcon={<Box component="svg" aria-hidden="true" viewBox="0 0 24 24" sx={{ width: 16, height: 16, fill: "none", stroke: "currentColor", strokeWidth: 2, strokeLinecap: "round", strokeLinejoin: "round" }}><path d="M14 3h7v7" /><path d="M10 14 21 3" /><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" /></Box>}
        sx={{ color: tone.onSurface, borderColor: tone.onSurface, minWidth: { xs: 44, sm: 64 }, px: { xs: 1.25, sm: 2.75 }, "& .MuiButton-endIcon": { ml: { xs: 0, sm: 1 } }, "&:hover": { borderColor: tone.onSurface, bgcolor: "#f8f9fa" } }}>
        <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>GitHub</Box>
      </Button>
    </Toolbar>
  </AppBar>;
}
