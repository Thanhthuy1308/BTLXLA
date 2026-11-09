import type { AnalysisResult } from "./types";

/** Pipeline steps in execution order; keys match PIPELINE_STEPS in web/app.py. */
export const PIPELINE_STEPS = [
  { key: "decode", label: "Đọc ảnh đầu vào" },
  { key: "grayscale", label: "Chuyển sang ảnh xám" },
  { key: "measure", label: "Tính Histogram và thống kê" },
  { key: "enhance", label: "Áp dụng phương pháp cải thiện" },
  { key: "compare", label: "So sánh kết quả và biên Canny" },
] as const;

export type StepKey = typeof PIPELINE_STEPS[number]["key"];
/** Seconds each finished step took, as measured by the server. */
export type StepTimes = Partial<Record<StepKey, number>>;

type StreamEvent =
  | { type: "step"; step: StepKey; seconds: number; elapsed: number }
  | { type: "result"; elapsed: number; result: AnalysisResult }
  | { type: "error"; error: string };

/**
 * Upload one image to the streaming endpoint and report each finished step.
 *
 * The server answers with newline-delimited JSON; every "step" line is real
 * progress from the Python pipeline, so the checklist never runs ahead of it.
 */
export async function analyzeImage(file: File, onStep: (key: StepKey, seconds: number) => void): Promise<{ result: AnalysisResult; elapsed: number }> {
  const body = new FormData();
  body.append("image", file);
  const response = await fetch("/api/analyze/stream", { method: "POST", body });
  if (!response.ok || !response.body) {
    let message = "";
    try { message = ((await response.json()) as { error?: string }).error ?? ""; } catch { /* non-JSON error page */ }
    throw new Error(message || "Không thể hoàn tất phân tích.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      newline = buffer.indexOf("\n");
      if (!line) continue;
      const event = JSON.parse(line) as StreamEvent;
      if (event.type === "step") onStep(event.step, event.seconds);
      else if (event.type === "result") return { result: event.result, elapsed: event.elapsed };
      else throw new Error(event.error);
    }
  }
  throw new Error("Kết nối bị ngắt trước khi có kết quả.");
}
