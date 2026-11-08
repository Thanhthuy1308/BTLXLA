"""Domain logic for histogram-based brightness and contrast analysis.

This module keeps the image-analysis rules independent from command-line execution.
The benchmark runner uses these functions to make every decision traceable in the
result CSV and in the before/after visualizations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


# Business rules used consistently for every benchmark sample. Values are expressed
# on the 8-bit grayscale scale [0, 255] and are reported in the comparison figure.
DARK_MEAN_THRESHOLD = 85.0
LOW_CONTRAST_STD_THRESHOLD = 45.0

# Enhancement parameters: gamma < 1 brightens shadows; percentile bounds reduce the
# influence of isolated outlier pixels when stretching contrast.
GAMMA_FOR_DARK_IMAGES = 0.60
PERCENTILE_LOW = 2.0
PERCENTILE_HIGH = 98.0

# Fixed Canny thresholds make edge-density changes comparable across all images.
CANNY_LOW_THRESHOLD = 100
CANNY_HIGH_THRESHOLD = 200


@dataclass(frozen=True)
class ImageMetrics:
    """Measurements used to classify and compare one image.

    All brightness and contrast values are calculated from grayscale pixels. Edge
    values are Canny-derived observations, not a stand-alone image-quality score.
    """

    mean_gray: float
    std_gray: float
    p02_gray: float
    p98_gray: float
    dynamic_range: float
    entropy: float
    edge_pixels: int
    edge_ratio: float


@dataclass(frozen=True)
class EnhancementConfig:
    """One complete, reproducible set of histogram-enhancement rules.

    Keeping the thresholds and transformation parameters together prevents a
    calibration experiment from silently mixing values from different runs.
    The default reproduces the configuration used by the baseline benchmark.
    """

    dark_mean_threshold: float = DARK_MEAN_THRESHOLD
    low_contrast_std_threshold: float = LOW_CONTRAST_STD_THRESHOLD
    gamma: float = GAMMA_FOR_DARK_IMAGES
    percentile_low: float = PERCENTILE_LOW
    percentile_high: float = PERCENTILE_HIGH


def read_bgr(path: str | Path) -> np.ndarray:
    """Load an image in OpenCV BGR order and fail early for invalid manifest paths."""
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {path}")
    return image


def to_gray(image_bgr: np.ndarray) -> np.ndarray:
    """Convert the analysis input to one luminance channel for histogram metrics."""
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def histogram(gray: np.ndarray) -> np.ndarray:
    """Return the 256-bin grayscale histogram used in figures and entropy."""
    return cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()


def entropy_from_histogram(values: np.ndarray) -> float:
    """Measure tonal information content in bits from a normalized histogram."""
    probabilities = values / values.sum()
    nonzero = probabilities[probabilities > 0]
    return float(-(nonzero * np.log2(nonzero)).sum())


def canny_edges(gray: np.ndarray) -> np.ndarray:
    """Detect edges with fixed thresholds so before/after ratios remain comparable."""
    return cv2.Canny(gray, CANNY_LOW_THRESHOLD, CANNY_HIGH_THRESHOLD)


def measure(image_bgr: np.ndarray) -> ImageMetrics:
    """Compute all metrics required by the experiment for one input image.

    The 2nd and 98th percentiles define a robust dynamic range. They are preferred
    over raw min/max values because a few clipped pixels should not dominate the
    contrast interpretation.
    """
    gray = to_gray(image_bgr)
    counts = histogram(gray)
    p02, p98 = np.percentile(gray, [PERCENTILE_LOW, PERCENTILE_HIGH])
    edges = canny_edges(gray)
    edge_pixels = int(np.count_nonzero(edges))
    # Edge density is retained alongside tonal metrics to show whether enhancement
    # reveals structure or merely increases high-frequency/noisy responses.
    return ImageMetrics(
        mean_gray=float(gray.mean()),
        std_gray=float(gray.std()),
        p02_gray=float(p02),
        p98_gray=float(p98),
        dynamic_range=float(p98 - p02),
        entropy=entropy_from_histogram(counts),
        edge_pixels=edge_pixels,
        edge_ratio=float(edge_pixels / gray.size),
    )


def is_dark(metrics: ImageMetrics, threshold: float = DARK_MEAN_THRESHOLD) -> bool:
    """Apply the documented brightness rule used to trigger gamma correction."""
    return metrics.mean_gray < threshold


def is_low_contrast(metrics: ImageMetrics, threshold: float = LOW_CONTRAST_STD_THRESHOLD) -> bool:
    """Apply the documented contrast rule used to trigger robust stretching."""
    return metrics.std_gray < threshold


def gamma_correct(image_bgr: np.ndarray, gamma: float = GAMMA_FOR_DARK_IMAGES) -> np.ndarray:
    """Brighten dark tones with ``y = 255 * (x / 255)^gamma``.

    A lookup table is used because the same 8-bit transformation is applied to every
    pixel and channel; this is both deterministic and efficient.
    """
    lookup = np.array([((value / 255.0) ** gamma) * 255 for value in range(256)], dtype=np.uint8)
    return cv2.LUT(image_bgr, lookup)


def contrast_stretch(image_bgr: np.ndarray, low: float = PERCENTILE_LOW, high: float = PERCENTILE_HIGH) -> np.ndarray:
    """Stretch each color channel between robust intensity percentiles.

    Channels with no measurable span are copied unchanged, preventing division by
    zero and avoiding artificial changes to a constant-color image.
    """
    result = np.empty_like(image_bgr)
    for channel in range(3):
        values = image_bgr[:, :, channel]
        minimum, maximum = np.percentile(values, [low, high])
        if maximum <= minimum:
            result[:, :, channel] = values
        else:
            scaled = (values.astype(np.float32) - minimum) * (255.0 / (maximum - minimum))
            result[:, :, channel] = np.clip(scaled, 0, 255).astype(np.uint8)
    return result


def enhance(
    image_bgr: np.ndarray,
    original: ImageMetrics,
    config: EnhancementConfig | None = None,
) -> tuple[np.ndarray, str]:
    """Apply transparent enhancement rules and return an audit-friendly operation label.

    Gamma is applied first when the original is dark. Contrast is then evaluated both
    before and after gamma because brightening alone does not necessarily restore tonal
    separation. The returned label is persisted in ``metrics.csv``.
    """
    # A missing configuration deliberately maps to the documented baseline so
    # existing callers keep exactly the same behaviour.
    rules = config or EnhancementConfig()
    result = image_bgr
    operations: list[str] = []
    # Step 1: recover visibility in shadow-dominated images.
    if is_dark(original, rules.dark_mean_threshold):
        result = gamma_correct(result, rules.gamma)
        operations.append("gamma")

    # Step 2: stretch tonal range only when original or gamma-adjusted contrast is low.
    after_gamma = measure(result)
    if is_low_contrast(original, rules.low_contrast_std_threshold) or is_low_contrast(after_gamma, rules.low_contrast_std_threshold):
        result = contrast_stretch(result, rules.percentile_low, rules.percentile_high)
        operations.append("contrast_stretch")

    return result, "+".join(operations) if operations else "identity"


def flatten_metrics(prefix: str, metrics: ImageMetrics) -> dict[str, float | int]:
    """Prefix metric keys so CSV columns clearly distinguish before from after values."""
    return {f"{prefix}_{key}": value for key, value in asdict(metrics).items()}


def save_comparison_figure(
    image_id: str,
    original_bgr: np.ndarray,
    enhanced_bgr: np.ndarray,
    original_metrics: ImageMetrics,
    enhanced_metrics: ImageMetrics,
    operation: str,
    output_path: str | Path,
) -> None:
    """Save one evidence figure for qualitative review of an enhancement decision.

    The layout intentionally places visual appearance, histogram shift, and Canny
    response together so a reviewer can detect improvements as well as over-enhancement.
    """
    original_gray, enhanced_gray = to_gray(original_bgr), to_gray(enhanced_bgr)
    figure, axes = plt.subplots(2, 3, figsize=(14, 8))
    figure.suptitle(f"{image_id} — {operation}", fontsize=14, fontweight="bold")

    # Top row: visual appearance and tonal distribution before/after processing.
    axes[0, 0].imshow(cv2.cvtColor(original_bgr, cv2.COLOR_BGR2RGB))
    axes[0, 0].set_title(f"Original\nmean={original_metrics.mean_gray:.1f}, std={original_metrics.std_gray:.1f}")
    axes[0, 1].imshow(cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title(f"Enhanced\nmean={enhanced_metrics.mean_gray:.1f}, std={enhanced_metrics.std_gray:.1f}")
    axes[0, 2].plot(histogram(original_gray), color="#4C78A8", label="original")
    axes[0, 2].plot(histogram(enhanced_gray), color="#F58518", label="enhanced")
    axes[0, 2].set_title("Grayscale histogram")
    axes[0, 2].set_xlim(0, 255)
    axes[0, 2].legend()

    # Bottom row: structural response and the exact rule/metric context.
    axes[1, 0].imshow(canny_edges(original_gray), cmap="gray")
    axes[1, 0].set_title(f"Original Canny\nedge ratio={original_metrics.edge_ratio:.3%}")
    axes[1, 1].imshow(canny_edges(enhanced_gray), cmap="gray")
    axes[1, 1].set_title(f"Enhanced Canny\nedge ratio={enhanced_metrics.edge_ratio:.3%}")
    axes[1, 2].axis("off")
    axes[1, 2].text(
        0.02, 0.95,
        "Decision rules\n"
        f"dark: mean < {DARK_MEAN_THRESHOLD:.0f}\n"
        f"low contrast: std < {LOW_CONTRAST_STD_THRESHOLD:.0f}\n\n"
        f"entropy: {original_metrics.entropy:.2f} → {enhanced_metrics.entropy:.2f}\n"
        f"range: {original_metrics.dynamic_range:.1f} → {enhanced_metrics.dynamic_range:.1f}",
        va="top", fontsize=11,
    )
    # Image and edge panes should not display coordinate axes in the final report.
    for axis in axes.ravel()[:2]:
        axis.axis("off")
    for axis in axes[1, :2]:
        axis.axis("off")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(figure)
