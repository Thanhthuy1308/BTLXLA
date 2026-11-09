# Benchmark Analysis Findings

## Scope

This report summarizes the 54-sample run recorded in `outputs/benchmark/metrics.csv`.
It describes metric changes produced by the fixed rule-based pipeline; it does not
treat a larger metric value alone as proof of subjective image quality.

## Dataset and decisions

- Input conditions: **mixed_illumination** (1), **normal** (1), **normal_control** (6), **overexposed** (7), **real_low_light** (12), **synthetic_low_contrast** (6), **underexposed** (21).
- Selected operations: **contrast_stretch** (6), **gamma** (7), **gamma+contrast_stretch** (25), **identity** (16).
- The detector flagged 32 images as dark and 31 as low contrast. These labels can overlap.

## Aggregate observations

- Mean gray level changed by **41.04** on average (median **27.41**); it increased for 35 samples, decreased for 3, and was unchanged for 16.
- Robust dynamic range changed by **106.19** on average (median **126.50**); it increased for 35 samples.
- Canny edge density changed by **0.0499** on average (median **0.0263**); it increased for 36 samples. This is a structural-response indicator, not a quality score: extra edges may reflect noise or over-enhancement.

## Recommended qualitative cases

The following samples are selected from measured extremes and one unchanged control.
Use their existing comparison figures where available, then inspect the original and
enhanced images before making any visual-quality claim.

| Reason | Image | Source | Condition | Operation | Δ mean | Δ range | Δ edge density |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| largest_brightness_gain | LOL_LOW_10 | LOL | underexposed | gamma+contrast_stretch | 132.14 | 223.00 | 0.1824 |
| largest_contrast_gain | SICE_07 | SICE | underexposed | gamma+contrast_stretch | 67.06 | 236.00 | 0.0331 |
| largest_edge_density_gain | LOL_LOW_12 | LOL | underexposed | gamma+contrast_stretch | 119.59 | 214.00 | 0.3576 |
| brightness_reduction_case | LCV_06 | derived | synthetic_low_contrast | contrast_stretch | -17.55 | 171.00 | 0.0644 |
| unchanged_control | SICE_08 | SICE | overexposed | identity | 0.00 | 0.00 | 0.0000 |


## Limitations

- The rules use fixed global thresholds (`mean < 85`, `std < 45`); they are transparent but not tuned per scene or camera.
- Canny edges use fixed thresholds. A rise in edge density can expose structure, but can also amplify texture or noise.
- The benchmark includes several sources and synthetic low-contrast variants, so aggregate statistics should be interpreted together with the source- and condition-level table rather than as a single image-quality score.
- The analysis reports change relative to the input. It does not calculate a full-reference quality metric for every source because a matched reference is not available for all samples.
