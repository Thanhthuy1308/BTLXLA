"""Aggregate benchmark measurements into report-ready evidence for Issue #5.

The benchmark runner creates one row per image.  This script deliberately reads that
checked-in CSV rather than opening images again, so its tables and charts remain an
auditable interpretation of one reproducible run rather than a second experiment.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import matplotlib.pyplot as plt
import numpy as np


# Resolve default locations relative to the repository.  This makes the command work
# from an IDE, a shell opened in another folder, and a CI job in the same way.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import enhance, measure, read_bgr, save_comparison_figure  # noqa: E402
from datasets import read_manifest  # noqa: E402

METRICS = ("mean_gray", "std_gray", "dynamic_range", "entropy", "edge_ratio")
METRIC_LABELS = {
    "mean_gray": "Mean gray level",
    "std_gray": "Gray-level standard deviation",
    "dynamic_range": "Robust dynamic range (P98 − P02)",
    "entropy": "Histogram entropy (bits)",
    "edge_ratio": "Canny edge density",
}


def read_rows(path: Path) -> list[dict[str, object]]:
    """Load numeric metrics and derive before/after deltas for each image row."""
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"No benchmark rows found in {path}")

    for row in rows:
        for metric in METRICS:
            row[f"before_{metric}"] = float(row[f"before_{metric}"])
            row[f"after_{metric}"] = float(row[f"after_{metric}"])
            row[f"delta_{metric}"] = row[f"after_{metric}"] - row[f"before_{metric}"]
        row["is_dark"] = int(row["is_dark"])
        row["is_low_contrast"] = int(row["is_low_contrast"])
    return rows


def summarise(rows: list[dict[str, object]]) -> dict[str, object]:
    """Calculate descriptive statistics without inferring subjective image quality."""
    summary: dict[str, object] = {"count": len(rows)}
    for metric in METRICS:
        deltas = [float(row[f"delta_{metric}"]) for row in rows]
        summary[metric] = {
            "mean_delta": float(np.mean(deltas)),
            "median_delta": float(median(deltas)),
            "positive_count": sum(delta > 0 for delta in deltas),
            "negative_count": sum(delta < 0 for delta in deltas),
            "unchanged_count": sum(delta == 0 for delta in deltas),
        }
    return summary


def group_rows(rows: list[dict[str, object]], group_type: str) -> list[dict[str, object]]:
    """Return group-level evidence for source, condition, and selected operation."""
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[group_type])].append(row)

    result: list[dict[str, object]] = []
    for group_name in sorted(grouped):
        group = grouped[group_name]
        record: dict[str, object] = {
            "group_type": group_type,
            "group": group_name,
            "sample_count": len(group),
            "dark_count": sum(int(row["is_dark"]) for row in group),
            "low_contrast_count": sum(int(row["is_low_contrast"]) for row in group),
        }
        for metric in METRICS:
            before = [float(row[f"before_{metric}"]) for row in group]
            after = [float(row[f"after_{metric}"]) for row in group]
            delta = [float(row[f"delta_{metric}"]) for row in group]
            record[f"before_mean_{metric}"] = float(np.mean(before))
            record[f"after_mean_{metric}"] = float(np.mean(after))
            record[f"mean_delta_{metric}"] = float(np.mean(delta))
            record[f"median_delta_{metric}"] = float(median(delta))
        result.append(record)
    return result


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Write a non-empty list of dictionaries as a consistently ordered CSV file."""
    if not rows:
        raise ValueError(f"Cannot write an empty table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def choose_representatives(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Select distinct, data-driven cases for qualitative inspection in the report."""
    non_identity = [row for row in rows if row["operation"] != "identity"]
    controls = [row for row in rows if row["operation"] == "identity"]
    candidates = [
        ("largest_brightness_gain", max(non_identity, key=lambda row: float(row["delta_mean_gray"]))),
        ("largest_contrast_gain", max(non_identity, key=lambda row: float(row["delta_dynamic_range"]))),
        ("largest_edge_density_gain", max(non_identity, key=lambda row: float(row["delta_edge_ratio"]))),
        # This deliberate counterexample makes the report discuss a contrast-only
        # adjustment that improves separation while reducing average brightness.
        ("brightness_reduction_case", min(non_identity, key=lambda row: float(row["delta_mean_gray"]))),
        ("unchanged_control", controls[0]),
    ]
    selected: list[dict[str, object]] = []
    used_ids: set[str] = set()
    for purpose, row in candidates:
        image_id = str(row["image_id"])
        if image_id in used_ids:
            continue
        used_ids.add(image_id)
        selected.append(
            {
                "selection_reason": purpose,
                "image_id": image_id,
                "source": row["source"],
                "condition_label": row["condition_label"],
                "operation": row["operation"],
                **{f"delta_{metric}": row[f"delta_{metric}"] for metric in METRICS},
            }
        )
    return selected


def plot_operation_deltas(rows: list[dict[str, object]], output: Path) -> None:
    """Plot mean before/after deltas by rule-selected enhancement operation."""
    operations = sorted({str(row["operation"]) for row in rows})
    x = np.arange(len(operations))
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), constrained_layout=True)
    for axis, metric in zip(axes.ravel(), METRICS[:4], strict=True):
        values = [
            np.mean([float(row[f"delta_{metric}"]) for row in rows if row["operation"] == operation])
            for operation in operations
        ]
        axis.bar(x, values, color="#2A6F97")
        axis.axhline(0, color="#555555", linewidth=0.8)
        axis.set_title(METRIC_LABELS[metric])
        axis.set_xticks(x, operations, rotation=18, ha="right")
        axis.set_ylabel("Mean after − before")
    fig.suptitle("Metric changes by selected enhancement operation", fontsize=14, fontweight="bold")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_condition_deltas(rows: list[dict[str, object]], output: Path) -> None:
    """Compare brightness and contrast response across documented condition labels."""
    conditions = sorted({str(row["condition_label"]) for row in rows})
    x = np.arange(len(conditions))
    width = 0.38
    mean_change = [
        np.mean([float(row["delta_mean_gray"]) for row in rows if row["condition_label"] == condition])
        for condition in conditions
    ]
    range_change = [
        np.mean([float(row["delta_dynamic_range"]) for row in rows if row["condition_label"] == condition])
        for condition in conditions
    ]
    fig, axis = plt.subplots(figsize=(13, 6), constrained_layout=True)
    axis.bar(x - width / 2, mean_change, width, label="Mean gray level", color="#2A6F97")
    axis.bar(x + width / 2, range_change, width, label="Robust dynamic range", color="#F4A261")
    axis.axhline(0, color="#555555", linewidth=0.8)
    axis.set_xticks(x, conditions, rotation=20, ha="right")
    axis.set_ylabel("Mean after − before")
    axis.set_title("Brightness and contrast changes by input condition")
    axis.legend()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_edge_response(rows: list[dict[str, object]], output: Path) -> None:
    """Show whether Canny response changed alongside robust tonal range."""
    colors = {"identity": "#8D99AE", "gamma": "#2A6F97", "contrast_stretch": "#F4A261", "gamma+contrast_stretch": "#E76F51"}
    fig, axis = plt.subplots(figsize=(9, 7), constrained_layout=True)
    for operation in sorted({str(row["operation"]) for row in rows}):
        group = [row for row in rows if row["operation"] == operation]
        axis.scatter(
            [float(row["delta_dynamic_range"]) for row in group],
            [float(row["delta_edge_ratio"]) for row in group],
            label=operation,
            color=colors.get(operation, "#264653"),
            alpha=0.8,
        )
    axis.axhline(0, color="#555555", linewidth=0.8)
    axis.axvline(0, color="#555555", linewidth=0.8)
    axis.set_xlabel("Change in robust dynamic range")
    axis.set_ylabel("Change in Canny edge density")
    axis.set_title("Tonal-range versus edge-response change")
    axis.legend(title="Operation")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def save_representative_figures(representatives: list[dict[str, object]], output: Path) -> None:
    """Regenerate full before/after evidence for the data-selected qualitative cases.

    The regular benchmark intentionally caps figures at twelve for fast iterations.
    This focused set closes that gap for report cases selected outside that first block
    while reusing exactly the same measurement and enhancement functions as the run.
    """
    records = {record.image_id: record for record in read_manifest(ROOT / "data" / "manifests" / "benchmark.csv")}
    output.mkdir(parents=True, exist_ok=True)
    for selected in representatives:
        image_id = str(selected["image_id"])
        record = records[image_id]
        original = read_bgr(ROOT / record.file_path)
        original_metrics = measure(original)
        enhanced, operation = enhance(original, original_metrics)
        enhanced_metrics = measure(enhanced)
        # A mismatch would indicate the manifest or processing rules changed after
        # metrics.csv was made, invalidating the qualitative comparison.
        if operation != selected["operation"]:
            raise ValueError(f"Operation mismatch for {image_id}: {operation} != {selected['operation']}")
        save_comparison_figure(
            image_id,
            original,
            enhanced,
            original_metrics,
            enhanced_metrics,
            operation,
            output / f"{image_id}.png",
        )


def write_findings(
    path: Path, rows: list[dict[str, object]], summary: dict[str, object], representatives: list[dict[str, object]]
) -> None:
    """Create a concise, evidence-bound discussion draft for the final report."""
    operations = Counter(str(row["operation"]) for row in rows)
    conditions = Counter(str(row["condition_label"]) for row in rows)
    mean_data = summary["mean_gray"]
    range_data = summary["dynamic_range"]
    edge_data = summary["edge_ratio"]
    representative_table = "".join(
        "| {selection_reason} | {image_id} | {source} | {condition_label} | {operation} | "
        "{mean:.2f} | {range:.2f} | {edge:.4f} |\n".format(
            selection_reason=row["selection_reason"],
            image_id=row["image_id"],
            source=row["source"],
            condition_label=row["condition_label"],
            operation=row["operation"],
            mean=float(row["delta_mean_gray"]),
            range=float(row["delta_dynamic_range"]),
            edge=float(row["delta_edge_ratio"]),
        )
        for row in representatives
    )
    text = f"""# Benchmark Analysis Findings

## Scope

This report summarizes the 54-sample run recorded in `outputs/benchmark/metrics.csv`.
It describes metric changes produced by the fixed rule-based pipeline; it does not
treat a larger metric value alone as proof of subjective image quality.

## Dataset and decisions

- Input conditions: {', '.join(f'**{name}** ({count})' for name, count in sorted(conditions.items()))}.
- Selected operations: {', '.join(f'**{name}** ({count})' for name, count in sorted(operations.items()))}.
- The detector flagged {sum(int(row['is_dark']) for row in rows)} images as dark and {sum(int(row['is_low_contrast']) for row in rows)} as low contrast. These labels can overlap.

## Aggregate observations

- Mean gray level changed by **{mean_data['mean_delta']:.2f}** on average (median **{mean_data['median_delta']:.2f}**); it increased for {mean_data['positive_count']} samples, decreased for {mean_data['negative_count']}, and was unchanged for {mean_data['unchanged_count']}.
- Robust dynamic range changed by **{range_data['mean_delta']:.2f}** on average (median **{range_data['median_delta']:.2f}**); it increased for {range_data['positive_count']} samples.
- Canny edge density changed by **{edge_data['mean_delta']:.4f}** on average (median **{edge_data['median_delta']:.4f}**); it increased for {edge_data['positive_count']} samples. This is a structural-response indicator, not a quality score: extra edges may reflect noise or over-enhancement.

## Recommended qualitative cases

The following samples are selected from measured extremes and one unchanged control.
Use their existing comparison figures where available, then inspect the original and
enhanced images before making any visual-quality claim.

| Reason | Image | Source | Condition | Operation | Δ mean | Δ range | Δ edge density |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
{representative_table}

## Limitations

- The rules use fixed global thresholds (`mean < 85`, `std < 45`); they are transparent but not tuned per scene or camera.
- Canny edges use fixed thresholds. A rise in edge density can expose structure, but can also amplify texture or noise.
- The benchmark includes several sources and synthetic low-contrast variants, so aggregate statistics should be interpreted together with the source- and condition-level table rather than as a single image-quality score.
- The analysis reports change relative to the input. It does not calculate a full-reference quality metric for every source because a matched reference is not available for all samples.
"""
    path.write_text(text, encoding="utf-8")


def main() -> None:
    """Generate tables, figures, and a report draft from a completed benchmark run."""
    parser = argparse.ArgumentParser(description="Analyse histogram benchmark results.")
    parser.add_argument("--metrics", type=Path, default=ROOT / "outputs" / "benchmark" / "metrics.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "analysis")
    args = parser.parse_args()

    rows = read_rows(args.metrics)
    summary = summarise(rows)
    group_summary = [
        record
        for group_type in ("source", "condition_label", "operation")
        for record in group_rows(rows, group_type)
    ]
    representatives = choose_representatives(rows)

    args.output.mkdir(parents=True, exist_ok=True)
    write_csv(args.output / "group_summary.csv", group_summary)
    write_csv(args.output / "representative_cases.csv", representatives)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_findings(args.output / "findings.md", rows, summary, representatives)
    figure_dir = args.output / "figures"
    plot_operation_deltas(rows, figure_dir / "operation_metric_changes.png")
    plot_condition_deltas(rows, figure_dir / "condition_metric_changes.png")
    plot_edge_response(rows, figure_dir / "edge_response_vs_dynamic_range.png")
    save_representative_figures(representatives, figure_dir / "representatives")
    print(json.dumps({"samples": len(rows), "groups": len(group_summary), "representatives": len(representatives)}, indent=2))


if __name__ == "__main__":
    main()
