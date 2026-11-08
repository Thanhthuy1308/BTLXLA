# Histogram-Based Image Brightness and Contrast Analysis

## Abstract

Digital images captured under insufficient or uneven illumination may suffer from poor brightness and low contrast, making visual details and object boundaries difficult to identify. This project proposes a histogram-based approach for analysing image brightness and contrast. For each input image, the system computes the grayscale histogram, mean gray level, and standard deviation to identify dark, overexposed, or low-contrast conditions. Gamma Correction and Contrast Stretching are then applied to improve image appearance according to the detected condition. The effectiveness of each enhancement method is evaluated by comparing image statistics, histograms, and Canny edge-detection results before and after processing. The expected outcome is a simple tool that recommends an appropriate enhancement method while showing whether the improved brightness and contrast also produce clearer and more meaningful edges.

**Keywords:** Image enhancement, histogram analysis, brightness, contrast, Gamma Correction, Contrast Stretching, Canny edge detection.

## Sample Visualization

![Two sample images with grayscale histograms](assets/sample_cover_histograms.png)

## Quick Start: Single-Image Demo

Install the project dependencies, then process any local image. The command uses the
validated baseline rules: dark if mean gray `< 85`, low contrast if standard deviation
`< 45`, gamma `0.60`, and percentile stretch `2–98%`.

```powershell
pip install -e .
python scripts/process_image.py --input "C:\path\to\image.jpg" --output data\processed\demo
```

The input is never modified. The selected output directory receives:

- `<image>_enhanced.<ext>` — the enhanced image;
- `<image>_comparison.png` — original/enhanced images, grayscale histograms, and Canny edges;
- `<image>_metrics.json` — detected conditions, selected operation, configuration, and before/after measurements.
