import { API_BASE, REMOTE_API, apiUrl, withApiBase } from "./config";
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
/** Vietnamese message for a request that never reached, or lost, the server. */
function connectionError() {
  return new Error(REMOTE_API
    ? `Không kết nối được server phân tích (${API_BASE}). Server có thể đang khởi động, hãy thử lại sau khoảng một phút.`
    : "Không kết nối được server phân tích. Hãy kiểm tra server Flask đang chạy.");
}

export async function analyzeImage(file: File, onStep: (key: StepKey, seconds: number) => void): Promise<{ result: AnalysisResult; elapsed: number }> {
  const body = new FormData();
  body.append("image", file);
  let response: Response;
  try {
    response = await fetch(apiUrl("/api/analyze/stream"), { method: "POST", body });
  } catch {
    // fetch only rejects on network failure: the server is down, asleep, or unreachable.
    throw connectionError();
  }
  if (!response.ok || !response.body) {
    let message = "";
    try { message = ((await response.json()) as { error?: string }).error ?? ""; } catch { /* non-JSON error page */ }
    throw new Error(message || "Không thể hoàn tất phân tích.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    let chunk: ReadableStreamReadResult<Uint8Array>;
    try {
      chunk = await reader.read();
    } catch {
      // The connection dropped mid-stream (server restarted, free instance went to sleep…).
      throw connectionError();
    }
    if (chunk.done) break;
    buffer += decoder.decode(chunk.value, { stream: true });
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      newline = buffer.indexOf("\n");
      if (!line) continue;
      const event = JSON.parse(line) as StreamEvent;
      if (event.type === "step") onStep(event.step, event.seconds);
      else if (event.type === "result") return { result: withApiBase(event.result), elapsed: event.elapsed };
      else throw new Error(event.error);
    }
  }
  throw new Error("Kết nối bị ngắt trước khi có kết quả.");
}
