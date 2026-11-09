/** Shapes returned by the Flask API (web/app.py). */

export type Metric = { before: number; after: number };
export type MetricGuide = { symbol: string; name: string; definition: string; threshold: number; rule: string; triggered: boolean; effect: string };
export type TransformGuide = { name: string; formula: string; effect: string };
export type Paragraph = { title: string; text: string };
export type DownloadItem = { label: string; detail: string; url: string };
export type PipelineStage = { key: string; label: string; note: string; url: string; mean: number; std: number; hist: number[]; final?: boolean };

export type AnalysisResult = {
  job_id: string;
  name: string;
  operation: string;
  operation_label: string;
  conditions: string[];
  metrics: { mean_gray: Metric; std_gray: Metric; dynamic_range: Metric; edge_ratio: Metric };
  interpretation: {
    metrics: { mean_gray: MetricGuide; std_gray: MetricGuide };
    overview: Paragraph[];
    histogram: { definition: string; reading: string };
    canny: { definition: string; reading: string };
    transformations: TransformGuide[];
    summary: string;
  };
  original_url: string;
  grayscale_url: string;
  gamma_url: string;
  enhanced_url: string;
  histogram_url: string;
  original_edges_url: string;
  enhanced_edges_url: string;
  original_overlay_url: string;
  enhanced_overlay_url: string;
  download_url: string;
  thresholds: { dark_mean: number; bright_mean: number; low_contrast_std: number };
  stages: PipelineStage[];
  downloads: DownloadItem[];
};

/** Result tabs in the studio. */
export type ResultTab = "Overview" | "Transformations" | "Edges" | "History";
