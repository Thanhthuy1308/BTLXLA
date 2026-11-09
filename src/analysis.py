"""Domain logic for histogram-based brightness and contrast analysis.

This module keeps the image-analysis rules independent from command-line execution.
The benchmark runner uses these functions to make every decision traceable in the
result CSV and in the before/after visualizations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import matplotlib
# Figures are written to PNG files by the CLI and Flask interface. The non-GUI
# backend keeps those server-side requests deterministic on Windows and avoids
# attempting to open a desktop plotting window from a request thread.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# Business rules used consistently for every benchmark sample. Values are expressed
# on the 8-bit grayscale scale [0, 255] and are reported in the comparison figure.
DARK_MEAN_THRESHOLD = 85.0
LOW_CONTRAST_STD_THRESHOLD = 45.0
# Descriptive-only rule: a bright image is reported to the user but never
# darkened automatically, because the project scope enhances only dark and
# low-contrast inputs. 170 mirrors the dark threshold around the mid-gray 127.5.
BRIGHT_MEAN_THRESHOLD = 170.0
# Pixels at or below/above these levels are counted as clipped shadows/highlights.
CLIP_LOW_LEVEL = 5
CLIP_HIGH_LEVEL = 250

# Enhancement parameters: gamma < 1 brightens shadows; percentile bounds reduce the
# influence of isolated outlier pixels when stretching contrast.
GAMMA_FOR_DARK_IMAGES = 0.60
PERCENTILE_LOW = 2.0
PERCENTILE_HIGH = 98.0

# Fixed Canny thresholds make edge-density changes comparable across all images.
# A Gaussian pre-blur implements step 1 of the classical Canny algorithm, which
# cv2.Canny itself does not perform. Without it, the sensor noise lifted by gamma
# and stretching is detected as dense false edges (e.g. LOL_LOW_10: 18.2% "edges"
# raw vs 4.7% coherent structure after blur). 50/150 keeps the 1:3 ratio
# recommended by Canny and was chosen on the representative benchmark samples.
CANNY_BLUR_KERNEL = (5, 5)
CANNY_BLUR_SIGMA = 1.4
CANNY_LOW_THRESHOLD = 50
CANNY_HIGH_THRESHOLD = 150


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
    """Load an image in OpenCV BGR order and fail early for invalid manifest paths.

    The byte-buffer fallback supports valid Windows paths containing non-ASCII
    characters, which OpenCV's path-based decoder may reject on some builds.
    """
    path_text = str(path)
    try:
        path_text.encode("ascii")
        image = cv2.imread(path_text, cv2.IMREAD_COLOR)
    except UnicodeEncodeError:
        image = None
    if image is None:
        # Read bytes through Python's Unicode-aware filesystem layer, then let
        # OpenCV decode the image content rather than the filesystem path.
        try:
            encoded = np.fromfile(path_text, dtype=np.uint8)
            image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        except OSError:
            image = None
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
    """Smooth with a Gaussian, then detect edges with fixed, comparable thresholds."""
    smoothed = cv2.GaussianBlur(gray, CANNY_BLUR_KERNEL, CANNY_BLUR_SIGMA)
    return cv2.Canny(smoothed, CANNY_LOW_THRESHOLD, CANNY_HIGH_THRESHOLD)


def psnr_against_reference(candidate_bgr: np.ndarray, reference_bgr: np.ndarray) -> float:
    """Return grayscale PSNR in dB for one spatially aligned reference pair.

    PSNR is only valid when the candidate and reference depict the same pixels.
    This project therefore uses it exclusively for the paired LOL subset rather
    than unpaired ExDark, SICE, or personal samples.
    """
    candidate_gray, reference_gray = to_gray(candidate_bgr), to_gray(reference_bgr)
    if candidate_gray.shape != reference_gray.shape:
        raise ValueError("PSNR requires candidate and reference images with identical dimensions.")
    # OpenCV guards zero MSE with an epsilon and returns an arbitrary large,
    # finite value. By definition, an exact match has an infinite PSNR score.
    if np.array_equal(candidate_gray, reference_gray):
        return float("inf")
    return float(cv2.PSNR(reference_gray, candidate_gray))


def ssim_against_reference(candidate_bgr: np.ndarray, reference_bgr: np.ndarray) -> float:
    """Return a deterministic grayscale SSIM score for an aligned reference pair.

    The implementation follows the standard local-mean/local-variance SSIM
    formulation with an 11×11 Gaussian window.  It avoids adding a separate
    dependency while making the score definition explicit in the source.
    """
    candidate = to_gray(candidate_bgr).astype(np.float64)
    reference = to_gray(reference_bgr).astype(np.float64)
    if candidate.shape != reference.shape:
        raise ValueError("SSIM requires candidate and reference images with identical dimensions.")

    # SSIM constants assume the documented 8-bit intensity range [0, 255].
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2
    mu_candidate = cv2.GaussianBlur(candidate, (11, 11), 1.5)
    mu_reference = cv2.GaussianBlur(reference, (11, 11), 1.5)
    sigma_candidate = cv2.GaussianBlur(candidate * candidate, (11, 11), 1.5) - mu_candidate * mu_candidate
    sigma_reference = cv2.GaussianBlur(reference * reference, (11, 11), 1.5) - mu_reference * mu_reference
    covariance = cv2.GaussianBlur(candidate * reference, (11, 11), 1.5) - mu_candidate * mu_reference
    numerator = (2 * mu_candidate * mu_reference + c1) * (2 * covariance + c2)
    denominator = (mu_candidate**2 + mu_reference**2 + c1) * (sigma_candidate + sigma_reference + c2)
    return float(np.mean(numerator / denominator))


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


def is_bright(metrics: ImageMetrics, threshold: float = BRIGHT_MEAN_THRESHOLD) -> bool:
    """Report a bright tendency; this rule describes the image and triggers no transform."""
    return metrics.mean_gray > threshold


def clipping_ratios(image_bgr: np.ndarray) -> tuple[float, float]:
    """Return the share of near-black and near-white grayscale pixels.

    A large spike at either end of the histogram means detail has been lost
    (crushed shadows or blown highlights), which the global Mean and Standard
    Deviation alone cannot reveal.
    """
    gray = to_gray(image_bgr)
    return (
        float(np.count_nonzero(gray <= CLIP_LOW_LEVEL) / gray.size),
        float(np.count_nonzero(gray >= CLIP_HIGH_LEVEL) / gray.size),
    )


def stretch_bounds(image_bgr: np.ndarray, low: float = PERCENTILE_LOW, high: float = PERCENTILE_HIGH) -> tuple[float, float]:
    """Return the (r_min, r_max) lightness percentiles used by ``contrast_stretch``."""
    lightness = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)[:, :, 0]
    minimum, maximum = np.percentile(lightness, [low, high])
    return float(minimum), float(maximum)


def gamma_correct(image_bgr: np.ndarray, gamma: float = GAMMA_FOR_DARK_IMAGES) -> np.ndarray:
    """Brighten dark tones with ``y = 255 * (x / 255)^gamma``.

    A lookup table is used because the same 8-bit transformation is applied to every
    pixel and channel; this is both deterministic and efficient.
    """
    lookup = np.array([((value / 255.0) ** gamma) * 255 for value in range(256)], dtype=np.uint8)
    return cv2.LUT(image_bgr, lookup)


def contrast_stretch(image_bgr: np.ndarray, low: float = PERCENTILE_LOW, high: float = PERCENTILE_HIGH) -> np.ndarray:
    """Stretch only perceptual lightness between robust intensity percentiles.

    Stretching B, G, and R channels independently changes their ratios and may
    introduce false purple/green colour casts in very dark scenes.  Lab separates
    lightness (L) from chromatic components (a and b), so adjusting L preserves
    the original hue while still expanding the image's visible tonal range.
    """
    lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)
    lightness = lab[:, :, 0]
    minimum, maximum = stretch_bounds(image_bgr, low, high)
    if maximum <= minimum:
        return image_bgr.copy()

    # Percentile clipping limits the effect of isolated highlight/shadow outliers.
    scaled = (lightness.astype(np.float32) - minimum) * (255.0 / (maximum - minimum))
    lab[:, :, 0] = np.clip(scaled, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


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
    axes[0, 0].set_title(f"Ảnh gốc\nμ={original_metrics.mean_gray:.1f}, σ={original_metrics.std_gray:.1f}")
    axes[0, 1].imshow(cv2.cvtColor(enhanced_bgr, cv2.COLOR_BGR2RGB))
    axes[0, 1].set_title(f"Ảnh sau xử lý\nμ={enhanced_metrics.mean_gray:.1f}, σ={enhanced_metrics.std_gray:.1f}")
    axes[0, 2].plot(histogram(original_gray), color="#4C78A8", label="ảnh gốc")
    axes[0, 2].plot(histogram(enhanced_gray), color="#F58518", label="sau xử lý")
    axes[0, 2].set_title("Histogram mức xám")
    axes[0, 2].set_xlim(0, 255)
    axes[0, 2].legend()

    # Bottom row: structural response and the exact rule/metric context.
    axes[1, 0].imshow(canny_edges(original_gray), cmap="gray")
    axes[1, 0].set_title(f"Canny ảnh gốc\ntỉ lệ biên={original_metrics.edge_ratio:.3%}")
    axes[1, 1].imshow(canny_edges(enhanced_gray), cmap="gray")
    axes[1, 1].set_title(f"Canny ảnh sau xử lý\ntỉ lệ biên={enhanced_metrics.edge_ratio:.3%}")
    axes[1, 2].axis("off")
    axes[1, 2].text(
        0.02, 0.95,
        "Quy tắc phân loại\n"
        f"ảnh tối: μ < {DARK_MEAN_THRESHOLD:.0f}\n"
        f"tương phản thấp: σ < {LOW_CONTRAST_STD_THRESHOLD:.0f}\n\n"
        f"entropy: {original_metrics.entropy:.2f} → {enhanced_metrics.entropy:.2f}\n"
        f"dải động: {original_metrics.dynamic_range:.1f} → {enhanced_metrics.dynamic_range:.1f}",
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


def save_histogram_comparison(
    original_bgr: np.ndarray,
    enhanced_bgr: np.ndarray,
    output_path: str | Path,
) -> None:
    """Write the exact 256-bin before/after distributions as a standalone figure.

    The web client displays this server-generated figure rather than recreating
    bins in JavaScript.  Consequently, the visual evidence and the calculated
    Mean/Standard Deviation always come from the same pixels and pipeline run.
    """
    figure, axes = plt.subplots(1, 2, figsize=(12, 3.8))

    for axis, image, title, color in (
        (axes[0], original_bgr, "Histogram ảnh gốc", "#0b57d0"),
        (axes[1], enhanced_bgr, "Histogram ảnh sau xử lý", "#185abc"),
    ):
        gray = to_gray(image)
        counts = histogram(gray)
        mean_value = float(gray.mean())
        axis.bar(np.arange(256), counts, width=1.0, color=color, edgecolor=color)
        # Each panel keeps its own y-axis: a sharply peaked dark histogram would
        # otherwise flatten the wider enhanced distribution into an unreadable strip.
        # The y-limit ignores the two extreme bins so a clipped spike at 0 or 255
        # cannot hide the rest of the distribution; the spike is labelled instead.
        inner_peak = counts[1:255].max() if counts[1:255].max() > 0 else counts.max()
        axis.set_ylim(0, inner_peak * 1.15)
        for level in (0, 255):
            if counts[level] > inner_peak * 1.15:
                axis.annotate(
                    f"mức {level}: {int(counts[level]):,} px".replace(",", "."),
                    xy=(level, inner_peak * 1.12), ha="left" if level == 0 else "right",
                    va="top", fontsize=9, color="#b3261e",
                )
        axis.axvline(mean_value, color="#b3261e", linestyle="--", linewidth=1.4, label=f"μ = {mean_value:.1f}")
        axis.legend(loc="upper left", frameon=False, fontsize=9)
        axis.set_title(title, loc="left", fontsize=11, fontweight="bold")
        axis.set_xlim(0, 255)
        axis.set_xlabel("Mức xám (0–255)")
        axis.grid(axis="y", alpha=0.18)

    axes[0].set_ylabel("Số pixel")
    figure.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(figure)
