"""Create qualitative evidence for the three principal calibration candidates."""

from __future__ import annotations

import csv
import sys
from dataclasses import asdict
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import EnhancementConfig, canny_edges, enhance, histogram, measure, read_bgr, to_gray  # noqa: E402
from datasets import read_manifest  # noqa: E402


# Keep the visual review focused on the baseline, the metric-leading alternative,
# and the strongest alternative that risks changing control images.
CONFIGS = {
    "baseline": EnhancementConfig(),
    "narrow_percentile_stretch": EnhancementConfig(percentile_low=5.0, percentile_high=95.0),
    "strong_recovery": EnhancementConfig(dark_mean_threshold=95.0, low_contrast_std_threshold=50.0, gamma=0.50),
}
# These groups make representative-case selection systematic rather than based on
# convenient-looking images chosen after seeing their enhanced versions.
LOW_LIGHT = {"underexposed", "real_low_light", "synthetic_low_contrast", "mixed_illumination"}
CONTROL = {"normal", "normal_control", "overexposed"}


def resize_for_review(image: np.ndarray, max_side: int = 960) -> np.ndarray:
    """Match the bounded-resolution calibration protocol for visual comparison."""
    height, width = image.shape[:2]
    if max(height, width) <= max_side:
        return image
    scale = max_side / max(height, width)
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def clip_ratios(image: np.ndarray) -> tuple[float, float]:
    """Measure near-black and near-white grayscale clipping after enhancement."""
    gray = to_gray(image)
    return float(np.mean(gray <= 1)), float(np.mean(gray >= 254))


def delta(row: dict[str, object], name: str) -> float:
    """Read an enhancement delta from the review record."""
    return float(row[f"after_{name}"]) - float(row[f"before_{name}"])


def choose_cases(rows: list[dict[str, object]]) -> list[tuple[str, dict[str, object]]]:
    """Select five non-duplicated cases that test benefits, clipping, and controls."""
    # Index all candidate outcomes by image so each selection criterion compares
    # transformations of the exact same source record.
    by_config = {name: {row["image_id"]: row for row in rows if row["config_id"] == name} for name in CONFIGS}
    narrow = by_config["narrow_percentile_stretch"]
    baseline = by_config["baseline"]
    strong = by_config["strong_recovery"]
    low_ids = [image_id for image_id, row in narrow.items() if row["condition_label"] in LOW_LIGHT]
    control_ids = [image_id for image_id, row in baseline.items() if row["condition_label"] in CONTROL]
    # Cover both positive recovery and failure modes: clipping, excessive edges,
    # unwanted control modification, and a control that should stay untouched.
    choices = [
        ("largest brightness recovery", max(low_ids, key=lambda item: delta(narrow[item], "mean_gray"))),
        ("highest white clipping after narrow stretch", max(low_ids, key=lambda item: float(narrow[item]["white_clip_ratio"]))),
        ("largest edge-response increase", max(low_ids, key=lambda item: delta(narrow[item], "edge_ratio"))),
        ("control altered by strong recovery", max(control_ids, key=lambda item: abs(delta(strong[item], "mean_gray")))),
        ("unchanged control", min(control_ids, key=lambda item: abs(delta(baseline[item], "mean_gray")))),
    ]
    selected: list[tuple[str, dict[str, object]]] = []
    seen: set[str] = set()
    for reason, image_id in choices:
        if image_id not in seen:
            selected.append((reason, baseline[image_id]))
            seen.add(image_id)
    return selected


def save_figure(record, transformed: dict[str, tuple[np.ndarray, object, str]], reason: str, output: Path) -> None:
    """Put appearance, histograms, and Canny responses in one reviewable figure."""
    original = resize_for_review(read_bgr(ROOT / record.file_path))
    original_metrics = measure(original)
    columns = ["original", *CONFIGS]
    figure, axes = plt.subplots(3, len(columns), figsize=(18, 10))
    figure.suptitle(f"{record.image_id}: {reason}", fontsize=14, fontweight="bold")
    images = {"original": (original, original_metrics, "input"), **transformed}
    for index, name in enumerate(columns):
        image, metrics, operation = images[name]
        gray = to_gray(image)
        black, white = clip_ratios(image)
        axes[0, index].imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        axes[0, index].set_title(f"{name}\n{operation}\nmean={metrics.mean_gray:.1f}, clip W={white:.1%}")
        axes[1, index].plot(histogram(gray), color="#4C78A8")
        axes[1, index].set_title("Grayscale histogram")
        axes[1, index].set_xlim(0, 255)
        axes[2, index].imshow(canny_edges(gray), cmap="gray")
        axes[2, index].set_title(f"Canny edge ratio={metrics.edge_ratio:.3%}\nclip B={black:.1%}")
        axes[0, index].axis("off")
        axes[2, index].axis("off")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    """Reapply candidates, save row-level diagnostics, and render selected cases."""
    # Stage 1: prepare the same bounded-resolution input representation used by
    # calibration, ensuring numerical and visual comparisons agree.
    records = read_manifest(ROOT / "data" / "manifests" / "benchmark.csv")
    output = ROOT / "outputs" / "calibration" / "review"
    output.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    prepared: dict[str, tuple[object, np.ndarray, object]] = {}
    for record in records:
        original = resize_for_review(read_bgr(ROOT / record.file_path))
        prepared[record.image_id] = (record, original, measure(original))

    # Stage 2: capture visual-review-specific diagnostics, including clipping
    # ratios that are not included in the core benchmark metric schema.
    for config_id, config in CONFIGS.items():
        for record, original, before in prepared.values():
            enhanced, operation = enhance(original, before, config)
            after = measure(enhanced)
            black, white = clip_ratios(enhanced)
            rows.append({
                "config_id": config_id,
                "image_id": record.image_id,
                "condition_label": record.condition_label,
                "operation": operation,
                **asdict(config),
                "before_mean_gray": before.mean_gray,
                "after_mean_gray": after.mean_gray,
                "before_dynamic_range": before.dynamic_range,
                "after_dynamic_range": after.dynamic_range,
                "before_entropy": before.entropy,
                "after_entropy": after.entropy,
                "before_edge_ratio": before.edge_ratio,
                "after_edge_ratio": after.edge_ratio,
                "black_clip_ratio": black,
                "white_clip_ratio": white,
            })

    # Stage 3: persist raw review metrics before rendering figures, allowing the
    # final conclusion to be independently checked without visual judgement.
    with (output / "review_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Stage 4: render one complete original/histogram/Canny comparison per chosen
    # case. The baseline row supplies the shared source record for all candidates.
    for reason, baseline_row in choose_cases(rows):
        record, original, before = prepared[baseline_row["image_id"]]
        transformed = {}
        for config_id, config in CONFIGS.items():
            enhanced, operation = enhance(original, before, config)
            transformed[config_id] = (enhanced, measure(enhanced), operation)
        save_figure(record, transformed, reason, output / "figures" / f"{record.image_id}.png")

    print(f"Saved {len(rows)} review rows and {len(list((output / 'figures').glob('*.png')))} figures to {output}")


if __name__ == "__main__":
    main()
