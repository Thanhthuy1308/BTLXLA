# Histogram-Based Image Brightness and Contrast Analysis

## Abstract

Digital images captured under insufficient or uneven illumination may suffer from poor brightness and low contrast, making visual details and object boundaries difficult to identify. This project proposes a histogram-based approach for analysing image brightness and contrast. For each input image, the system computes the 256-bin grayscale histogram, the mean gray level, and the standard deviation to identify dark or low-contrast conditions; bright images are reported but deliberately left unchanged. Gamma Correction and Contrast Stretching are then applied according to the detected condition. The effectiveness of each enhancement is evaluated by comparing image statistics, histograms, and Canny edge-detection results before and after processing. The outcome is a transparent tool that shows which rule fired, what each transformation did, and whether the improved brightness and contrast also produce clearer edges.

**Keywords:** Image enhancement, histogram analysis, brightness, contrast, Gamma Correction, Contrast Stretching, Canny edge detection.

## Sample Visualization

![Two sample images with grayscale histograms](assets/sample_cover_histograms.png)

## Quick start

Requirements: **Python 3.11+** and **Node.js 20.19+ or 22.12+** (Node is only needed to build the web interface).

```powershell
# 1. Python environment and dependencies
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

# 2. Build the web interface (frontend/dist is not committed)
cd frontend
npm ci
npm run build
cd ..

# 3. Start the server
python web/app.py
```

Open `http://127.0.0.1:5000`. On macOS/Linux, activate the environment with
`source .venv/bin/activate` instead.

Step 2 is required: Flask serves the built files from `frontend/dist`, so
skipping it leaves the web page blank. Rebuild after any change in `frontend/src`.

## Web interface

The interface is in Vietnamese, matching the course report. It runs the same
analysis code as the command-line scripts and the benchmark.

- **Giới thiệu (landing page):** an animated pixel-conversion demo of a real
  dark sample and its enhanced output; μ, σ and the histogram update with the scan.
- **Phân tích ảnh (studio):** drag-and-drop, file picker, or Ctrl+V paste of one
  JPG/JPEG/PNG up to 10 MB; analysis starts immediately. Four sample images, one
  per classification case, are available for demos.
- **Real progress:** the server streams each pipeline step as it finishes
  (decode → grayscale → statistics → enhancement → comparison) with its duration.
- **Result tabs:**
  - *Tổng quan* — conclusion card, before/after slider, threshold gauges for μ and σ,
    an interactive histogram (hover for exact pixel counts, linear/log scale), and a
    written assessment.
  - *Các bước biến đổi* — the numbered pipeline (original → grayscale → gamma →
    stretch) with μ, σ and a mini histogram per step, plus the formulas with the
    parameters actually used (e.g. `r_min`, `r_max`).
  - *So sánh biên Canny* — edge maps or edges overlaid on the image, with edge ratios.
  - *So sánh nhiều ảnh* — every image analysed in this browser tab in one table;
    click a row to reopen it, or export the table as CSV.
- **Downloads:** enhanced image, combined comparison figure, histogram figure,
  and the measurements as CSV and JSON.

Uploads and generated files are written to `web/runtime/` (ignored by Git).
This folder is not cleaned automatically; delete it when it grows.

### Frontend development

For live reloading while editing `frontend/src`, run Flask and the Vite dev
server side by side; Vite proxies `/api`, `/results` and `/samples` to Flask.

```powershell
python web/app.py          # terminal 1, port 5000
cd frontend; npm run dev   # terminal 2, open the URL Vite prints
```

## Decision rules

All values are on the 8-bit grayscale scale and are defined in `src/analysis.py`.

| Rule | Condition | Action |
| --- | --- | --- |
| Dark image | μ < 85 | Gamma correction, `s = 255·(r/255)^0.60` |
| Low contrast | σ < 45 (before or after gamma) | Contrast stretching between the 2nd and 98th percentiles, on the L channel of Lab so colours are preserved |
| Bright image | μ > 170 | Reported only; no transformation |
| Otherwise | — | Image left unchanged |

Canny edges are computed after a 5×5 Gaussian blur (σ = 1.4) with fixed
thresholds 50/150, identical for the images before and after processing, so the
edge ratios are comparable. The edge ratio is supporting evidence, not a quality
score: new continuous edges indicate recovered detail, while scattered responses
can be amplified noise.

The choice of thresholds is documented in `docs/rule-validation.md`.

## Command-line usage

```powershell
# One image: enhanced output, comparison figure and metrics JSON
python scripts/process_image.py --input path\to\image.jpg --output data\processed\demo

# Regenerate the web demo images in frontend/public/samples
python scripts/build_web_samples.py
```

## Tests

```powershell
python -m unittest discover -s tests
```

The tests cover the four classification cases, the reference metrics (PSNR/SSIM),
Canny noise robustness, and the web API: the JSON and streaming endpoints, every
download link, and Vietnamese error messages for invalid uploads.

## HTTP API

| Method and path | Purpose |
| --- | --- |
| `POST /api/analyze` | Multipart field `image`; returns the full result as JSON. |
| `POST /api/analyze/stream` | Same input; returns newline-delimited JSON: one `step` event per finished pipeline step, then a `result` (or `error`) event. |
| `GET /results/<job_id>/<file>` | Files produced by one analysis; add `?download=1` to download. |

## Project structure

```text
src/analysis.py        Measurement, classification, enhancement, figures
src/datasets.py        Benchmark manifest loading
web/app.py             Flask server and API (Vietnamese result text)
frontend/src/          React + TypeScript + MUI interface
  lib/                 Theme, API types, streaming client, history
  components/          Reusable UI pieces (slider, gauges, histogram, …)
  pages/               Landing page, studio, result tabs
frontend/public/samples/  Demo images built by scripts/build_web_samples.py
scripts/               Benchmark, calibration, analysis and demo tools
tests/                 Unit and API tests
docs/                  Benchmark and rule-validation notes
outputs/               Committed experiment results
```

## Experimental Evaluation

The reproducible benchmark contains 54 images: natural underexposed and
low-light scenes, normal/overexposed controls, personal smoke tests, and six
controlled low-contrast variants. Run the full experiment and aggregate its
evidence with:

```powershell
python scripts/run_benchmark.py --output outputs/benchmark
python scripts/analyze_benchmark.py --metrics outputs/benchmark/metrics.csv --output outputs/analysis
python scripts/evaluate_lol_references.py --output outputs/analysis/full_reference
```

The current run selected gamma plus contrast stretching for 25 samples, gamma
only for 7, contrast stretching only for 6, and preserved 16 with the identity
operation. The controlled checks behaved as expected: all 21 underexposed
samples triggered the dark rule; all six derived low-contrast images triggered
contrast stretching; and all six normal controls plus seven overexposed samples
were preserved unchanged.

Across all samples, mean grayscale increased by 41.04 on average, robust
dynamic range by 106.19, and Canny edge density by 0.0499. These changes are
evidence of tonal and structural response, not an absolute image-quality score:
the darkest examples may reveal both useful detail and amplified noise. See
`outputs/analysis/findings.md` for the generated discussion and selected
qualitative cases.

> **Note:** the committed benchmark outputs were produced before Canny gained its
> Gaussian pre-blur and the 50/150 thresholds (previously 100/200 on the raw
> image). The brightness, contrast, PSNR and SSIM figures are unaffected, but the
> edge-density values in `outputs/` and the 0.0499 figure above will change when
> the benchmark is re-run.

### Full-reference result on paired LOL images

Only the 14 LOL records that declare a spatially aligned normal-light partner
are eligible for full-reference measurement; the remaining benchmark images are
deliberately excluded because PSNR and SSIM require the same scene and pixel
geometry. Against this subset, the enhanced output raised mean PSNR from **8.04
to 16.76 dB** (+8.72 dB; 13/14 pairs improved) and mean grayscale SSIM from
**0.208 to 0.523** (+0.315; 14/14 pairs improved). `LOL_LOW_12` is the one
PSNR exception (-0.74 dB), despite a +0.216 SSIM gain, so the method should be
understood as a reproducible baseline rather than a guarantee of per-pixel
fidelity. The per-pair CSV, JSON summary, and plot are written to
`outputs/analysis/full_reference/`.
