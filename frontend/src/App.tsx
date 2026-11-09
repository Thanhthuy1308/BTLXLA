import { Route, Routes, useLocation } from "react-router-dom";
import { AnimatePresence, MotionConfig, motion } from "framer-motion";
import { CssBaseline, ThemeProvider } from "@mui/material";
import Header from "./components/Header";
import { theme } from "./lib/theme";
import OverviewPage from "./pages/OverviewPage";
import StudioPage from "./pages/StudioPage";

function AnimatedRoutes() {
  const location = useLocation();
  return <AnimatePresence mode="wait">
    <motion.div key={location.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .2, ease: "easeOut" }}>
      <Routes location={location}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="*" element={<OverviewPage />} />
      </Routes>
    </motion.div>
  </AnimatePresence>;
}

export default function App() {
  return <ThemeProvider theme={theme}><MotionConfig reducedMotion="user"><CssBaseline /><Header /><AnimatedRoutes /></MotionConfig></ThemeProvider>;
}
