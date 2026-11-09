"""Evaluate enhancement against aligned LOL normal-light reference pairs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt
import numpy as np


# Keep the evaluation script independent of the web server and runnable from any
# working directory, exactly like the benchmark runner.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import enhance, measure, psnr_against_reference, read_bgr, ssim_against_reference  # noqa: E402
from datasets import read_manifest  # noqa: E402


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write non-empty results in a stable, spreadsheet-friendly format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def save_metric_plot(rows: list[dict[str, object]], output_path: Path) -> None:
    """Plot each pair's PSNR and SSIM before/after without mixing score scales."""
    ids = [str(row["image_id"]).replace("LOL_LOW_", "L") for row in rows]
    x = np.arange(len(rows))
    figure, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, constrained_layout=True)
    for axis, metric, label in (
        (axes[0], "psnr_db", "PSNR (dB)"),
        (axes[1], "ssim", "SSIM"),
    ):
        before = [float(row[f"before_{metric}"]) for row in rows]
        after = [float(row[f"after_{metric}"]) for row in rows]
        axis.plot(x, before, marker="o", label="Low-light input", color="#5f6368")
        axis.plot(x, after, marker="o", label="Enhanced output", color="#0b57d0")
        axis.set_ylabel(label)
        axis.grid(axis="y", alpha=0.2)
        axis.legend(loc="best")
    axes[1].set_xticks(x, ids)
    axes[1].set_xlabel("Aligned LOL pair")
    figure.suptitle("Full-reference comparison against LOL normal-light pairs", fontweight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main() -> None:
    """Measure whether enhanced LOL images move toward their paired references."""
    parser = argparse.ArgumentParser(description="Evaluate aligned LOL reference pairs.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifests" / "benchmark.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "analysis" / "full_reference")
    args = parser.parse_args()

    # Only records declaring an explicit paired normal-light reference may enter
    # this evaluation. This avoids treating an unrelated image as ground truth.
    records = [
        record for record in read_manifest(args.manifest)
        if record.source == "LOL" and record.reference_type == "paired_normal_light" and record.reference_path
    ]
    if not records:
        raise ValueError("No paired LOL normal-light references were found in the manifest.")

    rows: list[dict[str, object]] = []
    for record in records:
        original = read_bgr(ROOT / record.file_path)
        reference = read_bgr(ROOT / str(record.reference_path))
        original_metrics = measure(original)
        enhanced, operation = enhance(original, original_metrics)
        rows.append(
            {
                "image_id": record.image_id,
                "operation": operation,
                "before_psnr_db": psnr_against_reference(original, reference),
                "after_psnr_db": psnr_against_reference(enhanced, reference),
                "before_ssim": ssim_against_reference(original, reference),
                "after_ssim": ssim_against_reference(enhanced, reference),
            }
        )

    for row in rows:
        row["delta_psnr_db"] = float(row["after_psnr_db"]) - float(row["before_psnr_db"])
        row["delta_ssim"] = float(row["after_ssim"]) - float(row["before_ssim"])

    def aggregate(metric: str) -> dict[str, float | int]:
        deltas = [float(row[f"delta_{metric}"]) for row in rows]
        return {
            "mean_before": float(np.mean([float(row[f"before_{metric}"]) for row in rows])),
            "mean_after": float(np.mean([float(row[f"after_{metric}"]) for row in rows])),
            "mean_delta": float(np.mean(deltas)),
            "median_delta": float(median(deltas)),
            "improved_count": sum(delta > 0 for delta in deltas),
            "worsened_count": sum(delta < 0 for delta in deltas),
            "unchanged_count": sum(delta == 0 for delta in deltas),
        }

    summary = {"pair_count": len(rows), "psnr_db": aggregate("psnr_db"), "ssim": aggregate("ssim")}
    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "lol_reference_metrics.csv", rows)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    save_metric_plot(rows, args.output / "metric_changes.png")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
