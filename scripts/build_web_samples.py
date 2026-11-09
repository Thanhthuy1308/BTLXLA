"""Prepare the static images used by the web interface.

The landing-page converter animation needs one dark image and its enhanced
counterpart produced by the real pipeline, and the studio offers one sample per
classification case so a demo never depends on finding a suitable photo.
Images are downscaled so the browser loads them quickly; the analysis is still
run by the server on whatever the user uploads.

Run from the repository root:

    python scripts/build_web_samples.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import enhance, is_bright, is_dark, is_low_contrast, measure, read_bgr  # noqa: E402

OUTPUT = ROOT / "frontend" / "public" / "samples"
MAX_SIDE = 1280
HERO_SIDE = 960

# One benchmark record per decision quadrant (see docs/rule-validation.md).
SAMPLES = (
    ("dark_low_contrast", "data/benchmark/primary/LOL_LOW_10.png", "Ảnh tối, tương phản thấp"),
    ("dark", "data/benchmark/primary/EXDARK_03.jpg", "Ảnh tối"),
    ("low_contrast", "data/benchmark/derived/LCV_06.png", "Ảnh tương phản thấp"),
    ("bright", "data/benchmark/primary/SICE_08.jpg", "Ảnh sáng, không cần xử lý"),
)
HERO_SOURCE = "data/benchmark/primary/LOL_LOW_10.png"


def downscale(image: np.ndarray, max_side: int) -> np.ndarray:
    """Shrink so the longest side is at most ``max_side``; never upscale."""
    height, width = image.shape[:2]
    scale = max_side / max(height, width)
    if scale >= 1:
        return image
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for key, source, label in SAMPLES:
        image = downscale(read_bgr(ROOT / source), MAX_SIDE)
        metrics = measure(image)
        _, operation = enhance(image, metrics)
        filename = f"{key}.jpg"
        cv2.imwrite(str(OUTPUT / filename), image, [cv2.IMWRITE_JPEG_QUALITY, 92])
        manifest.append({
            "key": key,
            "file": filename,
            "label": label,
            "source": Path(source).stem,
            "operation": operation,
            "dark": is_dark(metrics),
            "low_contrast": is_low_contrast(metrics),
            "bright": is_bright(metrics),
        })
        print(f"{filename}: mean={metrics.mean_gray:.1f} std={metrics.std_gray:.1f} -> {operation}")

    hero = downscale(read_bgr(ROOT / HERO_SOURCE), HERO_SIDE)
    hero_metrics = measure(hero)
    enhanced, _ = enhance(hero, hero_metrics)
    cv2.imwrite(str(OUTPUT / "hero_original.jpg"), hero, [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(str(OUTPUT / "hero_enhanced.jpg"), enhanced, [cv2.IMWRITE_JPEG_QUALITY, 90])
    (OUTPUT / "samples.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
