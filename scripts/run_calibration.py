"""Compare a compact grid of explainable histogram-enhancement configurations."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from statistics import fmean

import cv2

# Resolve imports and outputs from the repository so a calibration run remains
# reproducible regardless of the shell's current directory.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import EnhancementConfig, enhance, flatten_metrics, measure, read_bgr  # noqa: E402
from datasets import read_manifest  # noqa: E402


# This is deliberately a small sensitivity study, not an unrestricted parameter
# search. Every configuration changes one understandable aspect of the baseline so
# the final report can attribute an observed trade-off to a specific rule change.
CANDIDATES: dict[str, EnhancementConfig] = {
    "baseline": EnhancementConfig(),
    "gentle_detection": EnhancementConfig(dark_mean_threshold=75.0, low_contrast_std_threshold=40.0, gamma=0.70),
    "balanced_gamma": EnhancementConfig(low_contrast_std_threshold=40.0, gamma=0.65),
    "strong_recovery": EnhancementConfig(dark_mean_threshold=95.0, low_contrast_std_threshold=50.0, gamma=0.50),
    "narrow_percentile_stretch": EnhancementConfig(percentile_low=5.0, percentile_high=95.0),
}

# Labels are evaluated in two roles. Low-light records measure recovery; records
# that should normally remain unchanged guard against over-eager processing.
LOW_LIGHT_LABELS = {"underexposed", "real_low_light", "synthetic_low_contrast", "mixed_illumination"}
CONTROL_LABELS = {"normal", "normal_control", "overexposed"}


def delta(row: dict[str, object], metric: str) -> float:
    """Return one after-minus-before metric change from a result row."""
    return float(row[f"after_{metric}"]) - float(row[f"before_{metric}"])


def summarise(rows: list[dict[str, object]], config_name: str) -> dict[str, object]:
    """Aggregate benefits and control-image disturbance for one configuration.

    The score is only a ranking aid. It rewards tonal recovery in low-light groups
    and penalises unnecessary changes to controls; it never treats Canny density
    as a quality score.
    """
    low_light = [row for row in rows if row["condition_label"] in LOW_LIGHT_LABELS]
    controls = [row for row in rows if row["condition_label"] in CONTROL_LABELS]
    mean_gain = fmean(delta(row, "mean_gray") for row in low_light)
    range_gain = fmean(delta(row, "dynamic_range") for row in low_light)
    entropy_gain = fmean(delta(row, "entropy") for row in low_light)
    control_mean_shift = fmean(abs(delta(row, "mean_gray")) for row in controls)
    control_range_shift = fmean(abs(delta(row, "dynamic_range")) for row in controls)
    control_changed_fraction = sum(row["operation"] != "identity" for row in controls) / len(controls)
    edge_abs_change = fmean(abs(delta(row, "edge_ratio")) for row in low_light)

    # Normalise terms to their natural 8-bit ranges. The edge term is reported as
    # a stability diagnostic, not added as a benefit; dramatic edge response is a
    # reason for manual visual inspection rather than a claim of quality.
    ranking_score = (
        mean_gain / 255.0
        + range_gain / 255.0
        + entropy_gain / 8.0
        - control_mean_shift / 255.0
        - control_range_shift / 255.0
        - control_changed_fraction
    )
    return {
        "config_id": config_name,
        "sample_count": len(rows),
        "low_light_samples": len(low_light),
        "control_samples": len(controls),
        "low_light_mean_gain": mean_gain,
        "low_light_range_gain": range_gain,
        "low_light_entropy_gain": entropy_gain,
        "low_light_abs_edge_ratio_change": edge_abs_change,
        "control_abs_mean_shift": control_mean_shift,
        "control_abs_range_shift": control_range_shift,
        "control_changed_fraction": control_changed_fraction,
        "ranking_score": ranking_score,
    }


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write a deterministic CSV, including a header for a potentially empty set."""
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def calibration_image(image, max_side: int):
    """Downsample only for parameter comparison, never for the final benchmark.

    Calibration needs five passes over the same heterogeneous images. Bounding the
    longest side keeps the experiment practical while preserving the relative rule
    comparison; the chosen configuration is still verified by the full-size runner.
    """
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= max_side:
        return image
    scale = max_side / longest
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def main() -> None:
    """Run every candidate over one fixed manifest and persist comparison evidence."""
    parser = argparse.ArgumentParser(description="Calibrate transparent enhancement rules.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifests" / "benchmark.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "calibration")
    parser.add_argument("--max-side", type=int, default=960, help="Longest calibration-image side in pixels.")
    args = parser.parse_args()

    # Stage 1: load the immutable experiment definition and allocate a dedicated
    # result directory. Source images are never modified by this workflow.
    records = read_manifest(args.manifest)
    args.output.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, object]] = []
    rows_by_config: dict[str, list[dict[str, object]]] = defaultdict(list)

    # Stage 2: decode and measure each input once. Reusing this prepared set gives
    # all candidates identical input pixels and avoids repeated disk I/O.
    prepared = []
    for record in records:
        original = calibration_image(read_bgr(ROOT / record.file_path), args.max_side)
        prepared.append((record, original, measure(original)))

    # Stage 3: execute every candidate on every prepared image and preserve both
    # before/after metrics for later audit at image level.
    for config_id, config in CANDIDATES.items():
        for record, original, before in prepared:
            # Each candidate receives the identical resized-but-unmodified input.
            # This isolates rule changes from data-order and mutation effects.
            enhanced, operation = enhance(original, before, config)
            after = measure(enhanced)
            row: dict[str, object] = {
                "config_id": config_id,
                "image_id": record.image_id,
                "source": record.source,
                "condition_label": record.condition_label,
                "operation": operation,
                **asdict(config),
                **flatten_metrics("before", before),
                **flatten_metrics("after", after),
            }
            all_rows.append(row)
            rows_by_config[config_id].append(row)

    # Stage 4: reduce row-level evidence to comparable configuration summaries.
    # The leading candidate is intentionally provisional until visual review.
    summaries = [summarise(rows_by_config[config_id], config_id) for config_id in CANDIDATES]
    summaries.sort(key=lambda row: float(row["ranking_score"]), reverse=True)
    leading_candidate = summaries[0]
    selection = {
        "leading_candidate": leading_candidate["config_id"],
        "calibration_max_side": args.max_side,
        "selection_rule": "Highest balanced ranking score; verify representative images before treating it as the final configuration.",
        "candidate_parameters": {name: asdict(config) for name, config in CANDIDATES.items()},
        "summary": summaries,
    }

    # Stage 5: write a detailed table, a concise ranking, and full parameter
    # provenance so the same result can be regenerated without hidden state.
    write_csv(args.output / "results.csv", all_rows)
    write_csv(args.output / "summary.csv", summaries)
    (args.output / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
