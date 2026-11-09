import { useCallback, useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Box, Button, ButtonBase, Divider, LinearProgress, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import DownloadMenu from "../components/DownloadMenu";
import HistoryTable from "../components/HistoryTable";
import { DropZone, PipelineChecklist, RunningState, SampleGrid, currentStep } from "../components/UploadPanels";
import type { RunStatus } from "../components/UploadPanels";
import VerdictCard from "../components/VerdictCard";
import { fileSize, fixed, validate } from "../lib/format";
import { useAnalysisHistory } from "../lib/history";
import type { HistoryEntry } from "../lib/history";
import { PIPELINE_STEPS, analyzeImage } from "../lib/pipeline";
import type { StepTimes } from "../lib/pipeline";
import { SAMPLES } from "../lib/samples";
import { reveal, tone } from "../lib/theme";
import type { AnalysisResult, ResultTab } from "../lib/types";
import EdgesTab from "./result/EdgesTab";
import OverviewTab from "./result/OverviewTab";
import TransformationsTab from "./result/TransformationsTab";

function ResultBody({ tab, result, history, onOpenHistory, onClearHistory }: {
  tab: ResultTab; result: AnalysisResult; history: HistoryEntry[]; onOpenHistory: (entry: HistoryEntry) => void; onClearHistory: () => void;
}) {
  if (tab === "Transformations") return <TransformationsTab result={result} />;
  if (tab === "Edges") return <EdgesTab result={result} />;
  if (tab === "History") return <HistoryTable entries={history} currentId={result.job_id} onOpen={onOpenHistory} onClear={onClearHistory} />;
  return <OverviewTab result={result} />;
}

export default function StudioPage() {
  const input = useRef<HTMLInputElement>(null);
  const resultAnchor = useRef<HTMLDivElement>(null);
  const runId = useRef(0);
  const [searchParams, setSearchParams] = useSearchParams();
  const history = useAnalysisHistory();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const [status, setStatus] = useState<RunStatus>("idle");
  const [times, setTimes] = useState<StepTimes>({});
  const [seconds, setSeconds] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<ResultTab>("Overview");
  const [dragging, setDragging] = useState(false);
  const running = status === "running";
  const hasImage = Boolean(file || result);

  /** Revoke the temporary browser thumbnail whenever the user changes the input image. */
  useEffect(() => {
    if (!file) { setPreview(""); setDimensions(null); return undefined; }
    const localUrl = URL.createObjectURL(file);
    setPreview(localUrl);
    const probe = new Image();
    probe.onload = () => setDimensions({ width: probe.naturalWidth, height: probe.naturalHeight });
    probe.src = localUrl;
    return () => URL.revokeObjectURL(localUrl);
  }, [file]);

  /** Stream one analysis; each server-reported step updates the checklist. */
  const run = useCallback(async (next: File) => {
    const id = ++runId.current;
    setStatus("running"); setError(""); setSeconds(0); setTimes({});
    const started = performance.now();
    const timer = window.setInterval(() => setSeconds((performance.now() - started) / 1000), 100);
    try {
      const { result: payload, elapsed } = await analyzeImage(next, (step, stepSeconds) => {
        if (id === runId.current) setTimes((current) => ({ ...current, [step]: stepSeconds }));
      });
      if (id !== runId.current) return;
      setResult(payload);
      setStatus("done");
      history.add({ result: payload, elapsed, at: Date.now() });
      window.requestAnimationFrame(() => resultAnchor.current?.focus({ preventScroll: true }));
    } catch (caught) {
      if (id !== runId.current) return;
      setResult(null);
      setError(caught instanceof Error ? caught.message : "Không thể hoàn tất phân tích.");
      setStatus("error");
    } finally {
      window.clearInterval(timer);
      if (id === runId.current) setSeconds((performance.now() - started) / 1000);
    }
  }, [history.add]);

  /** Validate, then analyse immediately: choosing an image is the only action needed. */
  const accept = useCallback((next: File | null | undefined) => {
    if (!next) return;
    const problem = validate(next);
    // A rejected file is reported next to the picker; the previous analysis stays valid.
    if (problem) { setError(problem); return; }
    setFile(next);
    setTab((current) => (current === "History" ? "Overview" : current));
    void run(next);
  }, [run]);

  const pickSample = useCallback(async (key: string) => {
    const sample = SAMPLES.find((item) => item.key === key);
    if (!sample) return;
    try {
      const blob = await (await fetch(`/samples/${sample.file}`)).blob();
      accept(new File([blob], sample.file, { type: "image/jpeg" }));
    } catch {
      setError("Không tải được ảnh mẫu.");
    }
  }, [accept]);

  /** Reopen an earlier analysis from this tab's history without re-uploading. */
  const openEntry = useCallback((entry: HistoryEntry) => {
    runId.current += 1;
    setFile(null); setResult(entry.result); setStatus("done"); setSeconds(entry.elapsed); setTimes({}); setError(""); setTab("Overview");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  /** `/studio?sample=…` (from the landing page) loads that sample once. */
  useEffect(() => {
    const key = searchParams.get("sample");
    if (!key) return;
    setSearchParams({}, { replace: true });
    void pickSample(key);
  }, [searchParams, setSearchParams, pickSample]);

  /** Ctrl+V with an image on the clipboard behaves like choosing that file. */
  useEffect(() => {
    const onPaste = (event: ClipboardEvent) => {
      const pasted = Array.from(event.clipboardData?.files ?? []).find((item) => item.type.startsWith("image/"));
      if (pasted) { event.preventDefault(); accept(pasted); }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [accept]);

  function pickFile(event: ChangeEvent<HTMLInputElement>) { accept(event.target.files?.[0]); event.target.value = ""; }
  function onDragOver(event: DragEvent) { event.preventDefault(); if (!dragging) setDragging(true); }
  function onDragLeave(event: DragEvent) { if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setDragging(false); }
  function onDrop(event: DragEvent) { event.preventDefault(); setDragging(false); accept(event.dataTransfer.files?.[0]); }
  const browse = () => input.current?.click();

  const canDownload = Boolean(result) && !running;
  const thumbnail = preview || result?.original_url || "";
  const displayName = file?.name ?? result?.name;
  const active = running ? currentStep(times) : null;
  const statusLine = running ? `${active ? PIPELINE_STEPS.find((step) => step.key === active)?.label : "Hoàn tất"}… ${fixed(seconds, 1)} giây` : status === "done" ? `Hoàn tất trong ${fixed(seconds, 1)} giây` : "";

  return <Box component="main" onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop} sx={{ minHeight: "calc(100vh - 72px)", bgcolor: "#fff", p: { xs: 2, md: 3 }, pb: { xs: hasImage ? 12 : 2, md: 3 } }}><Box sx={{ maxWidth: 1680, mx: "auto", display: "grid", gridTemplateColumns: { xs: "1fr", lg: "260px minmax(0,1fr)" }, gap: { xs: 3, lg: 5 } }}>
    <input ref={input} hidden type="file" accept="image/jpeg,image/png" onChange={pickFile} />
    <Box component="aside" sx={{ pr: { lg: 3 }, borderRight: { lg: `1px solid ${tone.outline}` }, alignSelf: "start", position: { lg: "sticky" }, top: 92 }}>
      <Typography variant="overline" color="text.secondary" sx={{ display: { xs: hasImage ? "none" : "block", lg: "block" } }}>Ảnh đã chọn</Typography>
      <Box sx={{ display: { xs: hasImage ? "grid" : "none", lg: "block" }, gridTemplateColumns: "96px 1fr", gap: 1.5, alignItems: "center" }}>
        <ButtonBase onClick={browse} focusRipple aria-label="Chọn ảnh khác" sx={{ mt: { xs: 0, lg: 1 }, width: "100%", aspectRatio: "4 / 3", overflow: "hidden", borderRadius: 1, bgcolor: tone.surfaceContainer, border: `1px dashed ${dragging ? tone.primary : "transparent"}` }}>
          {thumbnail ? <Box component="img" src={thumbnail} alt="Ảnh thu nhỏ đã chọn" sx={{ width: "100%", height: "100%", objectFit: "contain" }} /> : <Typography variant="body2" color="text.secondary">Chưa chọn ảnh</Typography>}
        </ButtonBase>
        <Box sx={{ minWidth: 0 }}>
          <Typography sx={{ mt: { xs: 0, lg: 1.2 }, fontWeight: 700, fontSize: 14, wordBreak: "break-all" }}>{displayName ?? "JPG hoặc PNG · tối đa 10 MB"}</Typography>
          {file && <Typography variant="caption" color="text.secondary">{dimensions ? `${dimensions.width} × ${dimensions.height} px · ` : ""}{fileSize(file.size)} · {file.type === "image/png" ? "PNG" : "JPG"}</Typography>}
          {!file && result && <Typography variant="caption" color="text.secondary">Mở lại từ lịch sử phân tích</Typography>}
          <Typography variant="caption" sx={{ display: { xs: "block", lg: "none" }, color: tone.primary, fontWeight: 650 }} aria-live="polite">{statusLine}</Typography>
        </Box>
      </Box>
      <Button fullWidth variant={hasImage ? "outlined" : "contained"} sx={{ mt: 1.5, display: { xs: hasImage ? "none" : "flex", lg: "flex" } }} onClick={browse} disabled={running}>{hasImage ? "Chọn ảnh khác" : "Chọn ảnh"}</Button>
      {error && <Typography role="alert" variant="body2" sx={{ mt: 1, color: tone.error }}>{error}</Typography>}
      <Box sx={{ display: { xs: "none", lg: "block" } }}>
        {hasImage && <><Divider sx={{ my: 2.5 }} /><Typography variant="overline" color="text.secondary">Ảnh mẫu</Typography><Box sx={{ mt: .5 }}><SampleGrid onPick={pickSample} disabled={running} compact /></Box></>}
        <Divider sx={{ my: 2.5 }} />
        <PipelineChecklist status={status} times={times} seconds={seconds} />
      </Box>
    </Box>
    <Box sx={{ minWidth: 0 }}>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ justifyContent: "space-between", alignItems: { md: "end" }, mb: 3 }}>
        <Box><Typography variant="overline" color="primary">Phân tích ảnh</Typography><Typography variant="h2">Độ sáng và độ tương phản</Typography><Typography color="text.secondary" sx={{ mt: .75 }}>Histogram, mức xám trung bình, độ lệch chuẩn, ảnh sau cải thiện và so sánh biên Canny.</Typography></Box>
        {canDownload && result && <Box sx={{ display: { xs: "none", md: "block" } }}><DownloadMenu items={result.downloads} /></Box>}
      </Stack>
      {!result && !running ? <DropZone dragging={dragging} onBrowse={browse}>
        <Typography variant="overline" color="text.secondary" sx={{ display: "block", mt: 3, mb: 1 }}>Hoặc thử với ảnh mẫu — mỗi ảnh ứng với một trường hợp phân loại</Typography>
        <SampleGrid onPick={pickSample} disabled={running} />
        {history.entries.length > 0 && <Box sx={{ mt: 4 }}><Typography variant="overline" color="text.secondary" sx={{ display: "block", mb: 1 }}>Phân tích gần đây</Typography><HistoryTable entries={history.entries} onOpen={openEntry} onClear={history.clear} /></Box>}
      </DropZone> : !result ? <RunningState times={times} seconds={seconds} /> : <Box ref={resultAnchor} tabIndex={-1} sx={{ position: "relative", outline: "none" }}>
        {running && <Box sx={{ position: "sticky", top: 72, zIndex: 2, mb: 1, bgcolor: "rgba(255,255,255,.9)", pb: .5 }}><LinearProgress variant="determinate" value={(Object.keys(times).length / PIPELINE_STEPS.length) * 100} sx={{ height: 3 }} /><Typography variant="body2" sx={{ mt: .5, color: tone.primary, fontWeight: 650 }}>Đang phân tích ảnh mới · {statusLine}</Typography></Box>}
        <Box sx={{ opacity: running ? .45 : 1, transition: "opacity .2s", pointerEvents: running ? "none" : "auto" }}>
          <VerdictCard result={result} />
          <Box sx={{ pb: 1.5, borderBottom: `1px solid ${tone.outline}` }}>
            <ToggleButtonGroup value={tab} exclusive onChange={(_, value: ResultTab | null) => value && setTab(value)} size="small" sx={{ gap: .5, flexWrap: "wrap", "& .MuiToggleButton-root": { textTransform: "none", border: 0, borderRadius: 2, px: 1.4, fontWeight: 650 } }}>
              <ToggleButton value="Overview">Tổng quan</ToggleButton>
              <ToggleButton value="Transformations">Các bước biến đổi</ToggleButton>
              <ToggleButton value="Edges">So sánh biên Canny</ToggleButton>
              <ToggleButton value="History">So sánh nhiều ảnh ({history.entries.length})</ToggleButton>
            </ToggleButtonGroup>
          </Box>
          <Box sx={{ py: { xs: 3, md: 4 } }}><AnimatePresence mode="wait"><motion.div key={`${result.job_id}-${tab}`} {...reveal} transition={{ duration: .2 }}>
            <ResultBody tab={tab} result={result} history={history.entries} onOpenHistory={openEntry} onClearHistory={history.clear} />
          </motion.div></AnimatePresence></Box>
        </Box>
      </Box>}
    </Box>
    {hasImage && <Box sx={{ display: { xs: "flex", md: "none" }, position: "fixed", left: 0, right: 0, bottom: 0, zIndex: 10, gap: 1, p: 1.5, bgcolor: "rgba(255,255,255,.97)", borderTop: `1px solid ${tone.outline}` }}>
      <Box sx={{ flex: 1, minWidth: 0 }}><Button fullWidth variant="outlined" onClick={browse} disabled={running} sx={{ whiteSpace: "nowrap", px: 1.5 }}>Chọn ảnh khác</Button></Box>
      {canDownload && result && <Box sx={{ flex: 1, minWidth: 0 }}><DownloadMenu items={result.downloads} fullWidth /></Box>}
    </Box>}
  </Box></Box>;
}
