import type { ReactNode } from "react";
import { Box, ButtonBase, LinearProgress, Stack, Typography } from "@mui/material";
import { fixed } from "../lib/format";
import { PIPELINE_STEPS } from "../lib/pipeline";
import type { StepKey, StepTimes } from "../lib/pipeline";
import { SAMPLES } from "../lib/samples";
import { tone } from "../lib/theme";

export type RunStatus = "idle" | "running" | "done" | "error";

/** Clickable sample tiles: one image per classification case. */
export function SampleGrid({ onPick, disabled, compact = false }: { onPick: (key: string) => void; disabled: boolean; compact?: boolean }) {
  return <Box sx={{ display: "grid", gridTemplateColumns: compact ? "1fr 1fr" : { xs: "1fr 1fr", md: "repeat(4, 1fr)" }, gap: compact ? 1 : 1.5 }}>
    {SAMPLES.map((sample) => <ButtonBase key={sample.key} disabled={disabled} onClick={() => onPick(sample.key)} focusRipple sx={{ display: "block", textAlign: "left", borderRadius: 1, p: .5, "&:hover": { bgcolor: tone.surfaceContainer } }}>
      <Box component="img" src={`/samples/${sample.file}`} alt="" sx={{ width: "100%", aspectRatio: "4 / 3", objectFit: "cover", display: "block", borderRadius: .75, bgcolor: tone.surfaceContainer }} />
      <Typography sx={{ mt: .5, fontSize: compact ? 12 : 13, fontWeight: 650, lineHeight: 1.25 }}>{sample.label}</Typography>
    </ButtonBase>)}
  </Box>;
}

/** Large drop target shown before any image is chosen. */
export function DropZone({ dragging, onBrowse, children }: { dragging: boolean; onBrowse: () => void; children?: ReactNode }) {
  return <Box>
    <ButtonBase onClick={onBrowse} focusRipple sx={{ width: "100%", minHeight: 280, display: "grid", placeItems: "center", textAlign: "center", borderRadius: 2, border: `2px dashed ${dragging ? tone.primary : tone.outlineVariant}`, bgcolor: dragging ? tone.info : "#fafbfc", transition: "background-color .15s, border-color .15s", px: 3 }}>
      <Box>
        <Box aria-hidden="true" sx={{ mx: "auto", width: 52, height: 52, borderRadius: "50%", display: "grid", placeItems: "center", bgcolor: tone.info, color: tone.primary, fontSize: 28, fontWeight: 500 }}>↑</Box>
        <Typography variant="h3" component="p" sx={{ mt: 2 }}>{dragging ? "Thả ảnh vào đây" : "Kéo-thả ảnh vào đây hoặc bấm để chọn"}</Typography>
        <Typography color="text.secondary" sx={{ mt: .75 }}>JPG hoặc PNG, tối đa 10 MB. Có thể dán ảnh bằng Ctrl+V. Phân tích chạy ngay khi chọn ảnh.</Typography>
      </Box>
    </ButtonBase>
    {children}
  </Box>;
}

/** The step the server is working on: the first one not yet reported as finished. */
export function currentStep(times: StepTimes): StepKey | null {
  return PIPELINE_STEPS.find((step) => times[step.key] === undefined)?.key ?? null;
}

/**
 * Real per-step progress: a step is ticked only when the server reports it
 * finished, with the time it took. No timer-driven guessing.
 */
export function PipelineChecklist({ status, times, seconds }: { status: RunStatus; times: StepTimes; seconds: number }) {
  const active = status === "running" ? currentStep(times) : null;
  const doneCount = PIPELINE_STEPS.filter((step) => times[step.key] !== undefined).length;
  return <Box>
    <Typography variant="overline" color="text.secondary">Các bước xử lý</Typography>
    {status === "running" && <LinearProgress variant="determinate" value={(doneCount / PIPELINE_STEPS.length) * 100} sx={{ mt: .5, mb: 1, height: 3 }} />}
    <Stack spacing={1} sx={{ mt: .5 }}>{PIPELINE_STEPS.map((step) => {
      const time = times[step.key];
      const done = time !== undefined;
      const isActive = step.key === active;
      return <Stack key={step.key} direction="row" spacing={1.25} sx={{ alignItems: "center" }}>
        <Box aria-hidden="true" sx={{ width: 20, height: 20, flexShrink: 0, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: 12, fontWeight: 700, color: "white", bgcolor: done ? tone.primary : "transparent", border: done ? "none" : `1.5px solid ${isActive ? tone.primary : tone.outlineVariant}`,
          ...(isActive && { "&::after": { content: '""', width: 8, height: 8, borderRadius: "50%", bgcolor: tone.primary, animation: "pulse 1s ease-in-out infinite" } }) }}>{done ? "✓" : ""}</Box>
        <Typography sx={{ flex: 1, fontSize: 13, color: done || isActive ? tone.onSurface : "text.secondary", fontWeight: isActive ? 700 : 400 }}>{step.label}</Typography>
        {done && <Typography variant="caption" color="text.secondary" sx={{ fontVariantNumeric: "tabular-nums" }}>{fixed(time, 2)} s</Typography>}
      </Stack>;
    })}</Stack>
    <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.25 }} aria-live="polite">
      {status === "running" ? `Đang xử lý… ${fixed(seconds, 1)} giây` : status === "done" ? `Hoàn tất trong ${fixed(seconds, 1)} giây` : status === "error" ? "Phân tích không thành công" : "Chưa chạy phân tích"}
    </Typography>
  </Box>;
}

/** First run has no previous result to keep on screen: show the real current step. */
export function RunningState({ times, seconds }: { times: StepTimes; seconds: number }) {
  const active = currentStep(times);
  const index = active ? PIPELINE_STEPS.findIndex((step) => step.key === active) : PIPELINE_STEPS.length - 1;
  const doneCount = PIPELINE_STEPS.filter((step) => times[step.key] !== undefined).length;
  return <Box sx={{ minHeight: 360, display: "grid", placeItems: "center", textAlign: "center" }}><Box sx={{ width: 360, maxWidth: "100%" }}>
    <LinearProgress variant={doneCount ? "determinate" : "indeterminate"} value={(doneCount / PIPELINE_STEPS.length) * 100} sx={{ height: 4 }} />
    <Typography variant="h3" component="p" sx={{ mt: 3 }}>{PIPELINE_STEPS[index].label}…</Typography>
    <Typography color="text.secondary" sx={{ mt: .8 }} aria-live="polite">Bước {index + 1}/{PIPELINE_STEPS.length} · {fixed(seconds, 1)} giây</Typography>
  </Box></Box>;
}
