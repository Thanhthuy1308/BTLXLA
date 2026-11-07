# Dataset Guide

This directory defines the compact, reproducible benchmark used by the
histogram-based brightness and contrast analysis pipeline. The project evaluates
deterministic image-processing operations; it does not train a model. Therefore,
the benchmark retains representative samples rather than full public datasets.

## Layout

```text
data/
├── benchmark/          # Local image files; intentionally excluded from Git
│   ├── primary/         # Natural benchmark images
│   ├── references/      # LOL normal-light references
│   └── derived/         # Controlled low-contrast variants
├── manifests/
│   └── benchmark.csv    # Versioned sample metadata and local paths
└── processed/           # Optional generated data; excluded from Git
```

`benchmark.csv` is the authoritative experiment definition. The image files are
local-only because they are large and may have source-specific terms.

## Benchmark Composition

The current benchmark contains 54 samples: 48 natural images and six controlled
low-contrast variants.

| Group | Count | Purpose |
|---|---:|---|
| LOL underexposed | 14 | Dark-image detection and gamma correction; each sample has a normal-light reference. |
| ExDark real low-light | 12 | Robustness under real low-light scenes; all ten official lighting conditions are represented. |
| SICE under-/over-exposed | 14 | Exposure-extreme cases for enhancement analysis. |
| LOL normal controls | 6 | Verified controls with `mean ≥ 100` and `std ≥ 50`. |
| Personal controls | 2 | Qualitative smoke tests. |
| Derived low-contrast | 6 | Controlled validation cases created from normal controls with contrast factor `0.40`. |

## Manifest Fields

| Field | Description |
|---|---|
| `image_id` | Stable identifier used in metrics and figures. |
| `file_path` | Path to the local benchmark image, relative to the repository root. |
| `source` | Dataset or origin: `LOL`, `ExDark`, `SICE`, `personal`, or `derived`. |
| `condition_label` | High-level image condition used for grouping results. |
| `reference_path` / `reference_type` | Optional comparison reference and its relationship to the sample. |
| `parent_image_id` / `variant` | Provenance for derived samples. |
| `illumination_condition` | Official ExDark lighting type, when applicable. |
| `environment` / `dataset_split` | Official ExDark indoor/outdoor label and split, when applicable. |
| `license_note` / `notes` | Usage reminder and selection context. |

## Running the Benchmark

From the repository root:

```powershell
python scripts/run_benchmark.py
```

The command reads `manifests/benchmark.csv`, computes histogram and grayscale
statistics, applies rule-based enhancement, compares Canny edges, and writes
results to `outputs/benchmark/`.

## Source Catalog and Selection Policy

| Source | Available characteristics | Benchmark role | Reference policy |
|---|---|---|---|
| [LOL](https://daooshee.github.io/BMVC2018website/) | 500 paired low-/normal-light examples | Underexposed cases and normal controls | The paired normal-light image is retained when available. |
| [ExDark](https://github.com/cs-chan/Exclusively-Dark-Image-Dataset) | 7,363 real low-light images, 10 lighting types, 12 object classes | Real-world low-light robustness and Canny-edge evaluation | No aligned normal-light reference; use no-reference metrics. |
| [SICE](https://github.com/csjcai/SICE) | 589 multi-exposure sequences | Under- and over-exposure cases | Treat selected images as unpaired unless a justified reference is recorded. |
| Personal images | Two user-provided images | Smoke tests and qualitative examples | No full-reference metric. |

The benchmark selection is intentionally compact and stratified rather than random:

- LOL supplies paired underexposed images and validated normal controls.
- ExDark supplies 12 images covering every official lighting type, with indoor/outdoor
  metadata retained in the manifest.
- SICE supplies seven locally darkest and seven brightest selected sequence exposures.
- Six derived variants provide known low-contrast cases for rule validation; they are
  reported separately from natural-image observations.

## Evaluation Policy

For every sample, the pipeline records histogram-derived statistics, robust dynamic
range, entropy, and Canny edge density before and after enhancement.

- Use PSNR or SSIM only for samples with an aligned, justified reference image.
- Do not report full-reference metrics for ExDark, SICE samples without an explicit
  reference, or personal images.
- Treat an increase in edge density as an observation, not automatically an improvement:
  strong enhancement can also amplify noise.

## Use and Redistribution Notice

This repository includes the selected benchmark images and generated evaluation
artefacts so the course-project experiment can be reproduced. Review the terms of each
source dataset before reuse beyond this project. ExDark metadata and annotations have
research-use terms, while underlying third-party photographs may carry separate rights.
