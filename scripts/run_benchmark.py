"""Run the reproducible histogram-analysis benchmark and write report artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


# Resolve paths from the repository rather than the caller's current directory, so the
# command behaves consistently from PowerShell, an IDE, or a CI runner.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import enhance, flatten_metrics, is_dark, is_low_contrast, measure, read_bgr, save_comparison_figure  # noqa: E402
from datasets import read_manifest  # noqa: E402


def main() -> None:
    """Execute one identical analysis pass over every manifest sample.

    Outputs are separated into machine-readable metrics, a concise summary, and a
    limited number of report-ready figures. The original image files are never changed.
    """
    parser = argparse.ArgumentParser(description="Run the histogram benchmark.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data" / "manifests" / "benchmark.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "benchmark")
    parser.add_argument("--figures", type=int, default=12, help="Number of before/after figures to save; -1 saves all.")
    args = parser.parse_args()

    # Load the fixed experiment definition before creating any output artifacts.
    records = read_manifest(args.manifest)
    args.output.mkdir(parents=True, exist_ok=True)
    figure_dir = args.output / "figures"
    results: list[dict[str, object]] = []
    operation_counts: Counter[str] = Counter()

    for index, record in enumerate(records):
        # Measure the unmodified input, decide enhancement, then measure the result
        # with the same functions to keep before/after values comparable.
        original = read_bgr(ROOT / record.file_path)
        original_metrics = measure(original)
        enhanced, operation = enhance(original, original_metrics)
        enhanced_metrics = measure(enhanced)
        operation_counts[operation] += 1
        result: dict[str, object] = {
            "image_id": record.image_id,
            "source": record.source,
            "condition_label": record.condition_label,
            "parent_image_id": record.parent_image_id,
            "variant": record.variant,
            "illumination_condition": record.illumination_condition,
            "environment": record.environment,
            "dataset_split": record.dataset_split,
            "operation": operation,
            "is_dark": int(is_dark(original_metrics)),
            "is_low_contrast": int(is_low_contrast(original_metrics)),
            **flatten_metrics("before", original_metrics),
            **flatten_metrics("after", enhanced_metrics),
        }
        # Each row couples source provenance, the selected decision, and numeric
        # evidence, making a later report assertion traceable to one input image.
        results.append(result)
        # Figures are intentionally capped by default to keep report generation fast;
        # pass --figures -1 when a figure is needed for every benchmark record.
        if args.figures == -1 or index < args.figures:
            save_comparison_figure(record.image_id, original, enhanced, original_metrics, enhanced_metrics, operation, figure_dir / f"{record.image_id}.png")

    # Persist row-level evidence first; it is the source for later tables or plots.
    with (args.output / "metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    # Provide a compact run-level overview without replacing the detailed CSV.
    summary = {
        "sample_count": len(results),
        "operation_counts": dict(operation_counts),
        "dark_count": sum(row["is_dark"] for row in results),
        "low_contrast_count": sum(row["is_low_contrast"] for row in results),
        "figures_saved": len(list(figure_dir.glob("*.png"))) if figure_dir.exists() else 0,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
