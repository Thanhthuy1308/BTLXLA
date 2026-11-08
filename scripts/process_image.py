"""Process one external image with the validated histogram-enhancement pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import cv2


# Resolve repository modules from this script's location so the command works from
# PowerShell, an IDE, or another working directory without installation steps.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import (  # noqa: E402
    EnhancementConfig,
    enhance,
    is_dark,
    is_low_contrast,
    measure,
    read_bgr,
    save_comparison_figure,
)


def output_paths(input_path: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    """Return deterministic, non-destructive artifact paths for one source image.

    The suffixes identify generated content and avoid overwriting the original even
    when the caller places outputs beside it.
    """
    stem = input_path.stem
    extension = input_path.suffix or ".png"
    return (
        output_dir / f"{stem}_enhanced{extension}",
        output_dir / f"{stem}_comparison.png",
        output_dir / f"{stem}_metrics.json",
    )


def parse_args() -> argparse.Namespace:
    """Define the small public CLI surface for the single-image demonstration."""
    parser = argparse.ArgumentParser(
        description="Enhance one image using validated histogram-based rules.",
    )
    parser.add_argument("--input", required=True, type=Path, help="Path to a readable image file.")
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "processed" / "demo",
        help="Directory for the enhanced image, comparison figure, and metrics JSON.",
    )
    return parser.parse_args()


def main() -> None:
    """Measure, enhance, and document one image using the baseline configuration."""
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_dir = args.output.expanduser().resolve()

    # Validate the source before creating outputs, so a typo cannot leave behind a
    # misleading partial result directory.
    if not input_path.is_file():
        raise SystemExit(f"Input image does not exist or is not a file: {input_path}")

    try:
        original = read_bgr(input_path)
    except ValueError as error:
        raise SystemExit(str(error)) from error

    # Reuse the selected baseline rules rather than duplicating thresholds in the
    # CLI. This keeps demo behavior consistent with benchmark and validation work.
    config = EnhancementConfig()
    before = measure(original)
    enhanced, operation = enhance(original, before, config)
    after = measure(enhanced)

    output_dir.mkdir(parents=True, exist_ok=True)
    enhanced_path, comparison_path, metrics_path = output_paths(input_path, output_dir)
    if enhanced_path.resolve() == input_path:
        raise SystemExit("Refusing to overwrite the input image.")
    if not cv2.imwrite(str(enhanced_path), enhanced):
        raise SystemExit(f"Unable to write enhanced image: {enhanced_path}")

    # The comparison figure places appearance, tonal distribution, and edge response
    # together so users can see both improvement and possible over-enhancement.
    save_comparison_figure(
        input_path.stem,
        original,
        enhanced,
        before,
        after,
        operation,
        comparison_path,
    )

    # Persist raw measurements separately from the figure for reproducible reports
    # and for easy consumption by future batch or UI work.
    result = {
        "input": str(input_path),
        "enhanced_image": str(enhanced_path),
        "comparison_figure": str(comparison_path),
        "configuration": asdict(config),
        "detected_conditions": {
            "dark": is_dark(before, config.dark_mean_threshold),
            "low_contrast": is_low_contrast(before, config.low_contrast_std_threshold),
        },
        "operation": operation,
        "before": asdict(before),
        "after": asdict(after),
    }
    metrics_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # Keep terminal output compact and structured for a quick presentation demo.
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
