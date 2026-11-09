import { useCallback, useEffect, useState } from "react";
import type { AnalysisResult } from "./types";

export type HistoryEntry = { result: AnalysisResult; elapsed: number; at: number };

const STORAGE_KEY = "histogram-studio-history";
const LIMIT = 20;

function load(): HistoryEntry[] {
  try { return JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "[]") as HistoryEntry[]; } catch { return []; }
}

/**
 * Analyses made in this browser tab, newest first.
 *
 * sessionStorage is a per-viewer convenience: it survives reloads of the tab
 * but is cleared when the tab closes, so it never points at server results
 * from a much older session. Storage failures simply disable persistence.
 */
export function useAnalysisHistory() {
  const [entries, setEntries] = useState<HistoryEntry[]>(load);
  useEffect(() => {
    try { window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(entries)); } catch { /* storage unavailable */ }
  }, [entries]);
  const add = useCallback((entry: HistoryEntry) => {
    setEntries((current) => [entry, ...current.filter((item) => item.result.job_id !== entry.result.job_id)].slice(0, LIMIT));
  }, []);
  const clear = useCallback(() => setEntries([]), []);
  return { entries, add, clear };
}

/** CSV (with BOM so Excel keeps Vietnamese text) of every analysis in the history. */
export function historyCsv(entries: HistoryEntry[]) {
  const header = ["anh", "phan_loai", "phep_xu_ly", "mean_truoc", "mean_sau", "std_truoc", "std_sau", "dai_dong_truoc", "dai_dong_sau", "ti_le_bien_truoc_pct", "ti_le_bien_sau_pct", "thoi_gian_xu_ly_s"];
  const quote = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`;
  const rows = entries.map(({ result: r, elapsed }) => [
    r.name, r.conditions.join(" · "), r.operation_label,
    r.metrics.mean_gray.before, r.metrics.mean_gray.after, r.metrics.std_gray.before, r.metrics.std_gray.after,
    r.metrics.dynamic_range.before, r.metrics.dynamic_range.after, r.metrics.edge_ratio.before, r.metrics.edge_ratio.after, elapsed,
  ].map(quote).join(","));
  return "﻿" + [header.join(","), ...rows].join("\r\n");
}
