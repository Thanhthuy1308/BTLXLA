"""Regression tests for every documented brightness/contrast decision case."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


# The source directory is intentionally independent of the web server so the
# business-rule tests run quickly without creating browser result artefacts.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import (  # noqa: E402
    enhance,
    is_dark,
    is_low_contrast,
    measure,
    psnr_against_reference,
    ssim_against_reference,
)


def grayscale_scene(values: tuple[int, int], split: float = 0.5) -> np.ndarray:
    """Create a deterministic BGR test image containing two grayscale tones."""
    height, width = 80, 80
    image = np.full((height, width, 3), values[0], dtype=np.uint8)
    image[:, int(width * split):] = values[1]
    return image


class EnhancementDecisionTests(unittest.TestCase):
    """Verify classification and selected operation for each decision quadrant."""

    def assert_case(
        self,
        image: np.ndarray,
        expected_dark: bool,
        expected_low_contrast: bool,
        expected_operation: str,
    ) -> None:
        """Apply the public pipeline and compare every rule with its expected outcome."""
        metrics = measure(image)
        _enhanced, operation = enhance(image, metrics)
        self.assertEqual(is_dark(metrics), expected_dark)
        self.assertEqual(is_low_contrast(metrics), expected_low_contrast)
        self.assertEqual(operation, expected_operation)

    def test_dark_and_low_contrast_uses_gamma_and_stretch(self) -> None:
        """A dim narrow-range scene requires both recovery operations."""
        self.assert_case(grayscale_scene((8, 20)), True, True, "gamma+contrast_stretch")

    def test_dark_only_uses_gamma(self) -> None:
        """A dim but varied scene is brightened without an unnecessary stretch."""
        self.assert_case(grayscale_scene((0, 160)), True, False, "gamma")

    def test_low_contrast_only_uses_stretch(self) -> None:
        """A bright narrow-range scene receives only contrast stretching."""
        self.assert_case(grayscale_scene((140, 154)), False, True, "contrast_stretch")

    def test_within_thresholds_preserves_original(self) -> None:
        """A well-exposed, varied scene must remain an identity transformation."""
        self.assert_case(grayscale_scene((100, 210)), False, False, "identity")

    def test_canny_ignores_isolated_noise_after_gaussian_smoothing(self) -> None:
        """Salt noise on a flat field must not be reported as dense edges."""
        rng = np.random.default_rng(0)
        image = np.full((80, 80, 3), 120, dtype=np.uint8)
        mask = rng.random((80, 80)) < 0.02
        image[mask] = 255
        self.assertLess(measure(image).edge_ratio, 0.01)

    def test_reference_metrics_score_identical_images_perfectly(self) -> None:
        """The full-reference functions provide a stable perfect-match baseline."""
        image = grayscale_scene((40, 180))
        self.assertEqual(psnr_against_reference(image, image), float("inf"))
        self.assertAlmostEqual(ssim_against_reference(image, image), 1.0, places=12)

    def test_reference_metrics_reject_mismatched_dimensions(self) -> None:
        """Reference scores must not silently compare unaligned image geometry."""
        image = grayscale_scene((40, 180))
        resized = image[:64, :64]
        with self.assertRaises(ValueError):
            psnr_against_reference(image, resized)
        with self.assertRaises(ValueError):
            ssim_against_reference(image, resized)


if __name__ == "__main__":
    unittest.main()
