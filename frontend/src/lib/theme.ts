import { createTheme } from "@mui/material";

/** Keep the palette compact and flat: hierarchy comes from spacing and typography, not shadows. */
export const tone = {
  primary: "#0b57d0", onPrimary: "#ffffff", surface: "#ffffff",
  surfaceContainer: "#f1f3f4", onSurface: "#202124", onSurfaceVariant: "#45464f",
  outlineVariant: "#c5c6d0", outline: "#e8eaed", info: "#e8f0fe", error: "#b3261e",
  before: "#80868b",
};

/** Three corner radii only: pills for controls, 12px for cards, 8px for images. */
export const radius = { pill: "999px", card: "12px", media: "8px" };

/**
 * One fixed colour pair per classification, reused by chips, the conclusion card,
 * the comparison table and the threshold gauges so a category reads the same everywhere.
 */
export const conditionTone = {
  dark: { bg: "#e3e8f2", fg: "#1f3a68", zone: "#aab6cf" },
  lowContrast: { bg: "#fde8da", fg: "#8a3b12", zone: "#f4b38b" },
  bright: { bg: "#fdf2c9", fg: "#6e5200", zone: "#f3d36b" },
  ok: { bg: "#e2f3e7", fg: "#1e6b3a", zone: "#a6d8b3" },
  mid: { zone: "#d2e3fc" },
};

/** Shared entrance animation for result blocks. */
export const reveal = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 } };

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: tone.primary, contrastText: tone.onPrimary },
    background: { default: tone.surface, paper: tone.surface },
    text: { primary: tone.onSurface, secondary: tone.onSurfaceVariant },
    divider: tone.outlineVariant,
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: '"Google Sans", "Google Sans Text", Arial, sans-serif',
    h1: { fontSize: "clamp(2.6rem, 4.6vw, 4.4rem)", fontWeight: 500, lineHeight: 1.02, letterSpacing: "-.045em" },
    h2: { fontSize: "clamp(1.8rem, 2.6vw, 2.6rem)", fontWeight: 500, lineHeight: 1.08, letterSpacing: "-.035em" },
    h3: { fontSize: "1.25rem", fontWeight: 650, lineHeight: 1.28 },
    button: { fontWeight: 650, textTransform: "none", letterSpacing: 0 },
  },
  components: {
    MuiButton: { styleOverrides: { root: { minHeight: 44, borderRadius: 999, paddingInline: 22, boxShadow: "none", "&:hover": { boxShadow: "none" } } } },
    MuiAppBar: { styleOverrides: { root: { boxShadow: "none" } } },
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none", boxShadow: "none" } } },
  },
});
